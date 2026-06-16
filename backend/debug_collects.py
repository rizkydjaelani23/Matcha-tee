import os, sys, httpx
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

STORE = os.environ["SHOPIFY_STORE"]
TOKEN = os.environ["SHOPIFY_TOKEN"]
HR = {"X-Shopify-Access-Token": TOKEN}
H  = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}
API = f"https://{STORE}/admin/api/2025-01"

# Test with a known product
PID = 7698365382769  # Addison Rae

# 1. Check collects for this product
r = httpx.get(f"{API}/products/{PID}/collects.json", headers=HR, timeout=20)
print(f"collects status: {r.status_code}")
print(f"collects body: {r.text[:500]}")

# 2. Check collects globally for collection 305611079793 (Homepage)
r2 = httpx.get(f"{API}/collects.json?collection_id=305611079793&limit=5", headers=HR, timeout=20)
print(f"\nGlobal collects for Homepage: {r2.status_code}")
print(r2.text[:500])

# 3. Try adding this product to Homepage
r3 = httpx.post(f"{API}/collects.json",
                headers=H,
                json={"collect": {"product_id": PID, "collection_id": 305611079793}},
                timeout=20)
print(f"\nPOST collect: {r3.status_code}")
print(r3.text[:400])

# 4. Check collects again
r4 = httpx.get(f"{API}/products/{PID}/collects.json", headers=HR, timeout=20)
print(f"\ncollects after add: {r4.status_code}")
print(r4.text[:500])

# 5. Check via collection's product list
r5 = httpx.get(f"{API}/collections/305611079793/products.json?limit=5&fields=id,title", headers=HR, timeout=20)
print(f"\nHomepage collection products: {r5.status_code}")
print(r5.text[:500])
