"""
1. Reprice: tees £27 / hoodies+sweatshirts £37 / kids £22
2. compare_at_price = price × 1.30
3. Fix title typos (e.g. Sweathirt -> Sweatshirt)
4. Update handle to match fixed title + create 301 redirect so no links break
"""
import os, sys, json, re, time
import httpx
from dotenv import load_dotenv
sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
STORE = os.environ["SHOPIFY_STORE"]
TOKEN = os.environ["SHOPIFY_TOKEN"]
RH = {"X-Shopify-Access-Token": TOKEN}
H  = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}
API = f"https://{STORE}/admin/api/2025-01"

# ── typo patterns to fix in product titles ───────────────────────────────────
TYPOS = [
    (re.compile(r'Sweathirts?', re.IGNORECASE),
     lambda m: 'Sweatshirts' if m.group().lower().endswith('s') else 'Sweatshirt'),
    (re.compile(r'\bHoodied\b', re.IGNORECASE), lambda m: 'Hoodie'),
    (re.compile(r'\bTshirt\b', re.IGNORECASE),  lambda m: 'T-Shirt'),
    (re.compile(r'\bT Shirt\b', re.IGNORECASE), lambda m: 'T-Shirt'),
]

def fix_typos(title):
    for pattern, replacement in TYPOS:
        title = pattern.sub(replacement, title)
    return title

def slugify(text):
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s-]+', '-', text)
    return text.strip('-')

# ── category → price / compare_at ────────────────────────────────────────────
def categorize(title, ptype):
    t = title.lower()
    p = (ptype or "").lower()
    if any(k in t or k in p for k in ["kid", "youth", "child", "toddler", "baby"]):
        return "kids", "22.00", "28.60"
    if any(k in t or k in p for k in ["hoodie", "hoody", "sweatshirt", "sweat shirt",
                                        "crewneck", "crew neck", "pullover"]):
        return "hoodie", "37.00", "48.10"
    return "tee", "27.00", "35.10"

# ── fetch all products ────────────────────────────────────────────────────────
products = []
url = f"{API}/products.json?limit=250"
while url:
    r = httpx.get(url, headers=RH, timeout=30)
    data = r.json()
    products.extend(data["products"])
    link = r.headers.get("Link", "")
    url = None
    for part in link.split(","):
        if 'rel="next"' in part:
            url = part.strip().split(";")[0].strip("<> ")
print(f"Fetched {len(products)} products\n")

counts = {"tee": 0, "hoodie": 0, "kids": 0}
price_updated = 0
typos_fixed = []
redirect_ok = 0
failed = []

for p in products:
    orig_title = p["title"]
    ptype      = p.get("product_type", "")
    old_handle = p["handle"]

    # Fix typos in title
    new_title = fix_typos(orig_title)
    title_changed = new_title != orig_title

    cat, price, compare = categorize(new_title, ptype)
    counts[cat] += 1

    # Build variant list with new prices
    variants_payload = [
        {"id": v["id"], "price": price, "compare_at_price": compare}
        for v in p["variants"]
    ]

    update = {"id": p["id"], "variants": variants_payload}

    if title_changed:
        new_handle = slugify(new_title)
        update["title"]  = new_title
        update["handle"] = new_handle
    else:
        new_handle = old_handle

    # PUT product update
    r = httpx.put(f"{API}/products/{p['id']}.json",
                  headers=H, json={"product": update}, timeout=30)
    if r.status_code not in (200, 201):
        failed.append(f"{orig_title}: HTTP {r.status_code}")
        time.sleep(0.5)
        continue

    price_updated += 1

    label = f"[{cat.upper():<6}] {orig_title}"
    if title_changed:
        typos_fixed.append((orig_title, new_title))
        label += f"\n          typo fixed -> '{new_title}'"

    if title_changed and old_handle != new_handle:
        rr = httpx.post(f"{API}/redirects.json", headers=H,
                        json={"redirect": {
                            "path": f"/products/{old_handle}",
                            "target": f"/products/{new_handle}"
                        }}, timeout=20)
        # 422 = redirect already exists — still fine
        if rr.status_code in (200, 201, 422):
            redirect_ok += 1
            label += f"\n          redirect /products/{old_handle} -> /products/{new_handle}"
        else:
            label += f"\n          REDIRECT FAIL {rr.status_code}"

    print(label)
    time.sleep(0.35)

# ── summary ───────────────────────────────────────────────────────────────────
print(f"""
══ DONE ══════════════════════════════════════════════
Products repriced  : {price_updated}
  Tees @ £27       : {counts['tee']}
  Hoodies @ £37    : {counts['hoodie']}
  Kids  @ £22       : {counts['kids']}

Typos fixed        : {len(typos_fixed)}""")
for orig, new in typos_fixed:
    print(f"  '{orig}' -> '{new}'")
print(f"301 redirects made : {redirect_ok}")
if failed:
    print(f"FAILED ({len(failed)}):")
    for f in failed:
        print(f"  {f}")
print("══════════════════════════════════════════════════")
