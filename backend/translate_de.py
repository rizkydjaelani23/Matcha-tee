"""
Translate all store content to German using MyMemory free API (no signup, 5000 words/day).
Pushes translations to Shopify via GraphQL translationsRegister mutation.
Covers: products (title + body), collections (title + description), pages (title + body).

Run:  python translate_de.py --dry     # count words, no changes
      python translate_de.py            # translate everything
      python translate_de.py --products # products only
      python translate_de.py --pages    # pages + collections only
"""
import os, sys, time, argparse, httpx, json, hashlib
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
STORE = os.environ["SHOPIFY_STORE"]
TOKEN = os.environ["SHOPIFY_TOKEN"]
H  = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}
RH = {"X-Shopify-Access-Token": TOKEN}
API = f"https://{STORE}/admin/api/2025-01"
GQL = f"{API}/graphql.json"
LOCALE = "de"

# ── Free translation via MyMemory (5000 words/day, no key needed) ─────────────
def translate(text):
    if not text or not text.strip():
        return text
    # MyMemory limit per request: 500 chars. Chunk if needed.
    chunks = [text[i:i+499] for i in range(0, len(text), 499)]
    parts = []
    for chunk in chunks:
        try:
            r = httpx.get(
                "https://api.mymemory.translated.net/get",
                params={"q": chunk, "langpair": "en|de"},
                timeout=15,
            )
            d = r.json()
            # responseStatus 200 = success, 429 = quota exceeded
            if d.get("responseStatus") == 200:
                parts.append(d["responseData"]["translatedText"])
            elif d.get("responseStatus") == 429:
                print("  QUOTA EXCEEDED — stop and resume tomorrow")
                sys.exit(1)
            else:
                parts.append(chunk)   # fallback: keep English
        except Exception as e:
            print(f"  translate error: {e}")
            parts.append(chunk)
        time.sleep(0.25)   # gentle rate limiting
    return "".join(parts)

# ── GraphQL helpers ───────────────────────────────────────────────────────────
def gql(q, v=None):
    for _ in range(4):
        r = httpx.post(GQL, headers=H, json={"query": q, "variables": v or {}}, timeout=60)
        d = r.json()
        if d.get("errors") and any("throttle" in str(e).lower() for e in d["errors"]):
            time.sleep(3); continue
        return d
    return d

def get_translatable(gid):
    """Get translatable fields + their digest for a resource."""
    q = """query($id:ID!){
      translatableResource(resourceId:$id){
        resourceId
        translatableContent{ key value digest locale }
      }
    }"""
    d = gql(q, {"id": gid})
    return (d.get("data",{}).get("translatableResource",{}) or {}).get("translatableContent",[])

def push_translation(gid, key, value, digest):
    """Register a single translated field."""
    q = """mutation($id:ID!,$t:[TranslationInput!]!){
      translationsRegister(resourceId:$id, translations:$t){
        userErrors{field message}
      }
    }"""
    d = gql(q, {
        "id": gid,
        "t": [{"key": key, "value": value, "locale": LOCALE,
               "translatableContentDigest": digest}]
    })
    errs = (d.get("data",{}).get("translationsRegister",{}) or {}).get("userErrors",[])
    return errs

TRANSLATABLE_FIELDS = {
    # resource type -> [fields to translate]
    "product":    ["title", "body_html"],
    "collection": ["title", "description"],
    "page":       ["title", "body_html"],
}

def process_resource(gid, rtype, label):
    fields_needed = TRANSLATABLE_FIELDS.get(rtype, ["title"])
    content = get_translatable(gid)
    # filter to only the fields we want, in English
    targets = [c for c in content
               if c["key"] in fields_needed
               and c.get("locale") in ("en", None, "")
               and c.get("value","").strip()]
    if not targets:
        return 0, 0

    ok = fail = 0
    for c in targets:
        translated = translate(c["value"])
        errs = push_translation(gid, c["key"], translated, c["digest"])
        if errs:
            fail += 1
            print(f"    ERR {label} [{c['key']}]: {errs}")
        else:
            ok += 1
    return ok, fail

# ── Fetch all resources ───────────────────────────────────────────────────────
def fetch_products():
    prods = []
    url = f"{API}/products.json?limit=250&fields=id,title"
    while url:
        r = httpx.get(url, headers=RH, timeout=30)
        prods.extend(r.json()["products"])
        link = r.headers.get("Link",""); url = None
        for p in link.split(","):
            if 'rel="next"' in p: url = p.strip().split(";")[0].strip("<> ")
    return prods

def fetch_collections():
    cols = []
    for endpoint in ["custom_collections","smart_collections"]:
        url = f"{API}/{endpoint}.json?limit=250&fields=id,title"
        while url:
            r = httpx.get(url, headers=RH, timeout=30)
            cols.extend(r.json().get(endpoint.replace("_collections","")+"_collections",[]))
            link = r.headers.get("Link",""); url = None
            for p in link.split(","):
                if 'rel="next"' in p: url = p.strip().split(";")[0].strip("<> ")
    return cols

def fetch_pages():
    pages = []
    url = f"{API}/pages.json?limit=250&fields=id,title"
    while url:
        r = httpx.get(url, headers=RH, timeout=30)
        pages.extend(r.json()["pages"])
        link = r.headers.get("Link",""); url = None
        for p in link.split(","):
            if 'rel="next"' in p: url = p.strip().split(";")[0].strip("<> ")
    return pages

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--products", action="store_true")
    ap.add_argument("--pages", action="store_true")
    args = ap.parse_args()

    do_products = args.products or (not args.products and not args.pages)
    do_pages    = args.pages    or (not args.products and not args.pages)

    total_ok = total_fail = 0

    if do_products:
        prods = fetch_products()
        print(f"\nProducts: {len(prods)}")
        if args.dry:
            print("  DRY: would translate title + body_html for each")
        else:
            for i, p in enumerate(prods, 1):
                gid = f"gid://shopify/Product/{p['id']}"
                ok, fail = process_resource(gid, "product", p["title"][:30])
                total_ok += ok; total_fail += fail
                if i % 10 == 0 or i == len(prods):
                    print(f"  {i}/{len(prods)} products (ok={total_ok} fail={total_fail})")
                time.sleep(0.3)

    if do_pages:
        cols = fetch_collections()
        print(f"\nCollections: {len(cols)}")
        if not args.dry:
            for i, c in enumerate(cols, 1):
                gid = f"gid://shopify/Collection/{c['id']}"
                ok, fail = process_resource(gid, "collection", c["title"][:30])
                total_ok += ok; total_fail += fail
                if i % 5 == 0 or i == len(cols):
                    print(f"  {i}/{len(cols)} collections (ok={total_ok} fail={total_fail})")
                time.sleep(0.3)

        pages = fetch_pages()
        print(f"\nPages: {len(pages)}")
        if not args.dry:
            for i, pg in enumerate(pages, 1):
                gid = f"gid://shopify/Page/{pg['id']}"
                ok, fail = process_resource(gid, "page", pg["title"][:30])
                total_ok += ok; total_fail += fail
                time.sleep(0.3)
            print(f"  {len(pages)}/{len(pages)} pages done")

    if not args.dry:
        print(f"\nDone. translations registered={total_ok} errors={total_fail}")
        print("Visit /de/products/<handle> to verify German content.")
    else:
        print("\nDRY RUN complete — no changes made.")

if __name__ == "__main__":
    main()
