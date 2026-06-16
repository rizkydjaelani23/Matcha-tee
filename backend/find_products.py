import json, os, httpx
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
STORE = os.environ["SHOPIFY_STORE"]
TOKEN = os.environ["SHOPIFY_TOKEN"]
HR = {"X-Shopify-Access-Token": TOKEN}
API = f"https://{STORE}/admin/api/2025-01"

# Search for "addison" by title
r = httpx.get(f"{API}/products.json?title=Addison&limit=5&fields=id,title,status", headers=HR, timeout=20)
print("Status:", r.status_code)
prods = r.json().get("products", [])
print(f"Found {len(prods)} products matching 'Addison':")
for p in prods:
    print(f"  id={p['id']}  status={p['status']}  title={p['title'][:60]}")

# Also check how many total active products we have
r2 = httpx.get(f"{API}/products/count.json?status=active", headers=HR, timeout=20)
print(f"\nTotal active products: {r2.json().get('count')}")

r3 = httpx.get(f"{API}/products/count.json", headers=HR, timeout=20)
print(f"Total all products: {r3.json().get('count')}")
