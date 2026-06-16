"""
Phase 1: Set SEO title + meta description on all products via GraphQL.
Generates unique, keyword-rich metadata for the UK vintage graphic-tee niche.
"""
import os, sys, json, time, re
import httpx
from dotenv import load_dotenv
sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
STORE = os.environ["SHOPIFY_STORE"]
TOKEN = os.environ["SHOPIFY_TOKEN"]
RH    = {"X-Shopify-Access-Token": TOKEN}
H     = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}
API   = f"https://{STORE}/admin/api/2025-01"
GQL   = f"https://{STORE}/admin/api/2025-01/graphql.json"

BRAND = "The Matcha Tee"

# ── helpers ───────────────────────────────────────────────────────────────────
ACRONYMS = {"ii", "iii", "iv", "tv", "uk", "us", "ai", "dj", "mtv", "nba", "nfl", "wwe"}

def title_case(s):
    words = re.split(r"(\s+)", s.strip())
    out = []
    for w in words:
        if w.isspace() or not w:
            out.append(w)
            continue
        low = w.lower().strip(".,|-")
        if low in ACRONYMS:
            out.append(w.upper())
        elif "'" in w:  # keep apostrophes natural
            out.append(w[0].upper() + w[1:].lower())
        else:
            out.append(w[0].upper() + w[1:].lower())
    return "".join(out)

def clean_title(raw):
    # Remove duplicate suffixes like " - Xxx Tee", redundant brand refs
    t = raw.strip()
    # collapse weird " | duplicate name" patterns: keep part before " | " if it repeats
    if " | " in t:
        left = t.split(" | ")[0].strip()
        if len(left) >= 8:
            t = left
    if " - " in t:
        left = t.split(" - ")[0].strip()
        if len(left) >= 8:
            t = left
    return title_case(t)

def type_label(ptype, raw_title):
    p = (ptype or "").lower()
    tl = raw_title.lower()
    if "sweat" in p or "sweat" in tl:
        return "Vintage Sweatshirt"
    if "hoodie" in p or "hoodie" in tl:
        return "Vintage Hoodie"
    if "kid" in p or "kid" in tl:
        return "Kids Graphic Tee"
    return "Vintage Graphic Tee"

def type_noun(label):
    return {
        "Vintage Sweatshirt": "sweatshirt",
        "Vintage Hoodie": "hoodie",
        "Kids Graphic Tee": "kids' graphic tee",
        "Vintage Graphic Tee": "graphic tee",
    }[label]

DESC_TEMPLATES = [
    "Shop the {name} at {brand}. Premium {noun} in soft cotton with a unisex fit. Fast UK delivery & easy 30-day returns.",
    "Get the {name} — a vintage-style {noun} in heavyweight cotton. Unisex fit & quick UK shipping from {brand}.",
    "{name}: a retro {noun} with a bold print and lived-in feel. Soft cotton, unisex sizing, fast UK delivery. {brand}.",
    "Wear the {name} from {brand}. Nostalgic print on a buttery-soft {noun} with a true unisex fit. UK delivery & returns.",
]

def make_title_tag(name, label):
    base = f"{name} | {label} | {BRAND}"
    if len(base) <= 60:
        return base
    base2 = f"{name} | {BRAND}"
    if len(base2) <= 60:
        return base2
    # truncate name
    room = 60 - len(f" | {BRAND}")
    return f"{name[:room].rstrip()} | {BRAND}"

def make_desc(name, label, idx):
    noun = type_noun(label)
    tpl = DESC_TEMPLATES[idx % len(DESC_TEMPLATES)]
    d = tpl.format(name=name, noun=noun, brand=BRAND)
    if len(d) > 160:
        # cut at last whole word before 157, no mid-word truncation
        cut = d[:157]
        if " " in cut:
            cut = cut[:cut.rfind(" ")]
        d = cut.rstrip(" .,&-") + "."
    return d

# ── fetch all products (REST, paginated) ──────────────────────────────────────
def fetch_all():
    out = []
    url = f"{API}/products.json?limit=250&fields=id,title,product_type,handle"
    while url:
        r = httpx.get(url, headers=RH, timeout=30)
        out.extend(r.json().get("products", []))
        link = r.headers.get("Link", "")
        nxt = None
        for part in link.split(","):
            if 'rel="next"' in part:
                nxt = part[part.find("<")+1:part.find(">")]
        url = nxt
    return out

products = fetch_all()
print(f"Fetched {len(products)} products\n")

MUT = """mutation upd($id: ID!, $seo: SEOInput!) {
  productUpdate(input: {id: $id, seo: $seo}) {
    product { id seo { title description } }
    userErrors { field message }
  }
}"""

ok = fail = 0
for i, p in enumerate(products):
    name  = clean_title(p["title"])
    label = type_label(p.get("product_type"), p["title"])
    ttag  = make_title_tag(name, label)
    desc  = make_desc(name, label, i)
    gid   = f"gid://shopify/Product/{p['id']}"

    r = httpx.post(GQL, headers=H, json={
        "query": MUT,
        "variables": {"id": gid, "seo": {"title": ttag, "description": desc}},
    }, timeout=30)
    body = r.json()
    errs = body.get("data", {}).get("productUpdate", {}).get("userErrors", [])
    if r.status_code == 200 and not errs and body.get("data", {}).get("productUpdate", {}).get("product"):
        ok += 1
        if i < 5 or i % 20 == 0:
            print(f"  [{i+1:02d}] {ttag}")
            print(f"        {desc}")
    else:
        fail += 1
        print(f"  [{i+1:02d}] FAIL {p['title'][:40]}: {errs or body.get('errors')}")
    time.sleep(0.4)

print(f"\nDone. SEO set on {ok} products. Failed: {fail}")
