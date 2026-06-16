"""
Check blueprint details, print providers, and variants for choosing the right blueprint.
Also samples Shopify products to understand current variant structure.
"""
import os, sys, httpx, json
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
STORE = os.environ["SHOPIFY_STORE"]
SHOPIFY_TOKEN = os.environ["SHOPIFY_TOKEN"]
PRINTIFY_TOKEN = os.environ["PRINTIFY_TOKEN"]
SH = {"X-Shopify-Access-Token": SHOPIFY_TOKEN}
PH = {"Authorization": f"Bearer {PRINTIFY_TOKEN}"}
PAPI = "https://api.printify.com/v1"
SHOP_ID = 27883571

# ── Blueprints to check (Bella+Canvas 3001, Gildan 64000, Gildan 5000) ──────
BLUEPRINT_IDS = [5, 6, 12]

for bid in BLUEPRINT_IDS:
    r = httpx.get(f"{PAPI}/catalog/blueprints/{bid}.json", headers=PH, timeout=20)
    b = r.json()
    print(f"\n=== Blueprint {bid}: {b.get('title','?')} ===")
    print(f"  Description: {b.get('description','')[:100]}")

    # Print providers for this blueprint
    r2 = httpx.get(f"{PAPI}/catalog/blueprints/{bid}/print_providers.json", headers=PH, timeout=20)
    providers = r2.json()
    print(f"  Print providers ({len(providers)}):")
    for p in providers[:8]:
        print(f"    id={p['id']:4}  {p['title']}")

# ── Sample Shopify products ───────────────────────────────────────────────────
print("\n\n=== Sample Shopify Products ===")
r = httpx.get(
    f"https://{STORE}/admin/api/2025-01/products.json?limit=3&fields=id,title,variants,images",
    headers=SH, timeout=20
)
for p in r.json()["products"]:
    print(f"\nProduct: {p['title'][:60]}")
    print(f"  Variants ({len(p['variants'])}):")
    for v in p["variants"][:6]:
        print(f"    sku={v.get('sku','')}  opts: {v.get('option1','')} / {v.get('option2','')}  price={v.get('price')}")
    if p.get("images"):
        img = p["images"][0]
        print(f"  Main image: {img.get('src','')[:80]}")

# ── Check existing Printify products ─────────────────────────────────────────
print("\n\n=== Existing Printify Products ===")
r = httpx.get(f"{PAPI}/shops/{SHOP_ID}/products.json?limit=10", headers=PH, timeout=20)
data = r.json()
prods = data.get("data", [])
print(f"Total Printify products: {data.get('total', 0)}")
for p in prods[:5]:
    print(f"  id={p['id']}  title={p.get('title','')[:50]}  blueprint={p.get('blueprint_id')}")
