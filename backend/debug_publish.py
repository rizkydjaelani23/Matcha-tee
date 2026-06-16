import os, httpx, json, sys, time
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
STORE = os.environ["SHOPIFY_STORE"]
SHOPIFY_TOKEN = os.environ["SHOPIFY_TOKEN"]
PRINTIFY_TOKEN = os.environ["PRINTIFY_TOKEN"]
SHR = {"X-Shopify-Access-Token": SHOPIFY_TOKEN}
SH = {"X-Shopify-Access-Token": SHOPIFY_TOKEN, "Content-Type": "application/json"}
PH = {"Authorization": f"Bearer {PRINTIFY_TOKEN}", "Content-Type": "application/json"}
PAPI = "https://api.printify.com/v1"
SAPI = f"https://{STORE}/admin/api/2025-01"
SHOP_ID = 27883571
PID = "6a2f6bc7a4bf9acfe9043bcf"

# Check full product details
r = httpx.get(f"{PAPI}/shops/{SHOP_ID}/products/{PID}.json", headers=PH, timeout=20)
p = r.json()

print("=== Product variants (first 5) ===")
for v in p.get("variants", [])[:5]:
    print(f"  {json.dumps(v)[:150]}")

print(f"\n=== Images ({len(p.get('images',[]))}) ===")
for img in p.get("images", [])[:3]:
    print(f"  {json.dumps(img)[:150]}")

print(f"\n=== Print areas ===")
for pa in p.get("print_areas", []):
    vids = pa.get("variant_ids", [])
    placeholders = pa.get("placeholders", [])
    print(f"  variant_ids count: {len(vids)}  (first 3: {vids[:3]})")
    for ph in placeholders:
        print(f"  position={ph.get('position')}  images={ph.get('images')}")

# Check shop details
print("\n=== Printify Shop Details ===")
r2 = httpx.get(f"{PAPI}/shops.json", headers=PH, timeout=20)
for s in r2.json():
    print(f"  {json.dumps(s)}")

# Check all products list to understand external IDs on existing products
print("\n=== Existing Printify products with external IDs ===")
r3 = httpx.get(f"{PAPI}/shops/{SHOP_ID}/products.json?limit=20", headers=PH, timeout=20)
data = r3.json()
for prod in data.get("data", []):
    print(f"  id={prod['id']}  external={prod.get('external')}  title={prod.get('title','')[:40]}")

# Also check Shopify fulfillment services again
print("\n=== Shopify Fulfillment Services ===")
r4 = httpx.get(f"{SAPI}/fulfillment_services.json", headers=SHR, timeout=20)
svcs = r4.json().get("fulfillment_services", [])
print(f"  Count: {len(svcs)}")
for s in svcs:
    print(f"  id={s['id']}  name={s['name']}  handle={s['handle']}")
