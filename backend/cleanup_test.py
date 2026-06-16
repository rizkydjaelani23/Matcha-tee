"""Delete the test Addison Rae duplicate that was created during debugging."""
import os, httpx, sys
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

# Delete the Shopify duplicate
shopify_id = "7697268637809"
r = httpx.delete(f"{SAPI}/products/{shopify_id}.json", headers=SHR, timeout=20)
print(f"Delete Shopify product {shopify_id}: {r.status_code}")

# Delete the Printify product
printify_id = "6a2f6bc7a4bf9acfe9043bcf"
r2 = httpx.delete(f"{PAPI}/shops/{SHOP_ID}/products/{printify_id}.json", headers=PH, timeout=20)
print(f"Delete Printify product {printify_id}: {r2.status_code}")
if r2.status_code not in (200, 204):
    print(f"  Response: {r2.text[:200]}")

print("\nTest products cleaned up. Ready for full sync.")
