import os, httpx, json, sys, time
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
STORE = os.environ["SHOPIFY_STORE"]
SHOPIFY_TOKEN = os.environ["SHOPIFY_TOKEN"]
PRINTIFY_TOKEN = os.environ["PRINTIFY_TOKEN"]
SHR = {"X-Shopify-Access-Token": SHOPIFY_TOKEN}
PH = {"Authorization": f"Bearer {PRINTIFY_TOKEN}", "Content-Type": "application/json"}
PAPI = "https://api.printify.com/v1"
SAPI = f"https://{STORE}/admin/api/2025-01"
SHOP_ID = 27883571
PID = "6a2f6bc7a4bf9acfe9043bcf"

# Check print_areas on the Printify product
r = httpx.get(f"{PAPI}/shops/{SHOP_ID}/products/{PID}.json", headers=PH, timeout=20)
p = r.json()
print("Print areas:")
for pa in p.get("print_areas", []):
    print(f"  {json.dumps(pa)[:300]}")

print("\nSales channel props:", p.get("sales_channel_properties"))

# Check if any new product appeared on Shopify in the last 30 min
print("\n\nShopify - recent products:")
r2 = httpx.get(
    f"{SAPI}/products.json?limit=5&order=created_at+desc&fields=id,title,created_at,handle",
    headers=SHR, timeout=20
)
for pr in r2.json().get("products", []):
    print(f"  id={pr['id']}  {pr['title'][:60]}  created={pr['created_at']}")

# Check Shopify for "Addison Rae" specifically
print("\nSearching Shopify for 'addison':")
r3 = httpx.get(
    f"{SAPI}/products.json?title=addison&fields=id,title,created_at,variants",
    headers=SHR, timeout=20
)
for pr in r3.json().get("products", []):
    print(f"  id={pr['id']}  {pr['title']}  created={pr['created_at']}")
    for v in pr.get("variants", [])[:2]:
        print(f"    variant fulfillment_service={v.get('fulfillment_service')}")
