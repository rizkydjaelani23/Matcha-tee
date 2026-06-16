import os, sys, json, httpx
from dotenv import load_dotenv
sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
STORE = os.environ["SHOPIFY_STORE"]
RH    = {"X-Shopify-Access-Token": os.environ["SHOPIFY_TOKEN"]}
API   = f"https://{STORE}/admin/api/2025-01"
THEME = 143507587185

# Confirm block_order in product.json
r = httpx.get(f"{API}/themes/{THEME}/assets.json", headers=RH,
              params={"asset[key]": "templates/product.json"}, timeout=15)
pj = json.loads(r.json()["asset"]["value"])
order = pj["sections"]["main"]["blocks"]["product-details"]["block_order"]
print("product-details block_order:")
for i, b in enumerate(order, 1):
    print(f"  {i}. {b}")

# Confirm block file exists
r2 = httpx.get(f"{API}/themes/{THEME}/assets.json", headers=RH,
               params={"asset[key]": "blocks/tmt-payment-notice.liquid"}, timeout=15)
exists = "value" in r2.json().get("asset", {})
print(f"\nblocks/tmt-payment-notice.liquid: {'EXISTS' if exists else 'MISSING'}")
