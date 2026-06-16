import os, json, httpx, sys
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

STORE = os.environ["SHOPIFY_STORE"]
TOKEN = os.environ["SHOPIFY_TOKEN"]
H = {"X-Shopify-Access-Token": TOKEN}
API = f"https://{STORE}/admin/api/2025-01"

# Get custom collections
r = httpx.get(f"{API}/custom_collections.json?limit=250", headers=H, timeout=20)
colls = r.json().get("custom_collections", [])
print("Custom collections:")
for c in colls:
    print(f"  {c['id']}: {c['title']}")

# Get smart collections
r2 = httpx.get(f"{API}/smart_collections.json?limit=250", headers=H, timeout=20)
smart = r2.json().get("smart_collections", [])
print("\nSmart collections:")
for c in smart:
    print(f"  {c['id']}: {c['title']}")

# Check a sample product's variants for current price
r3 = httpx.get(f"{API}/products.json?limit=1&fields=id,title,variants", headers=H, timeout=20)
prods = r3.json().get("products", [])
if prods:
    p = prods[0]
    print(f"\nSample product: {p['title']}")
    for v in p["variants"][:3]:
        print(f"  variant: {v['title']} | price={v['price']} | compare_at_price={v.get('compare_at_price')}")

# Check which collections a product is in
if prods:
    pid = prods[0]["id"]
    r4 = httpx.get(f"{API}/products/{pid}/collects.json", headers=H, timeout=20)
    collects = r4.json().get("collects", [])
    print(f"\nCollections for product {pid}:")
    for c in collects:
        print(f"  collection_id={c['collection_id']}")
