"""Find where the buy button / payment section lives in the Horizon product template."""
import os, sys, json, httpx
from dotenv import load_dotenv
sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
STORE = os.environ["SHOPIFY_STORE"]
RH    = {"X-Shopify-Access-Token": os.environ["SHOPIFY_TOKEN"]}
API   = f"https://{STORE}/admin/api/2025-01"
THEME = 143507587185

# Read templates/product.json to see section/block layout
r = httpx.get(f"{API}/themes/{THEME}/assets.json", headers=RH,
              params={"asset[key]": "templates/product.json"}, timeout=15)
pj = r.json()["asset"]["value"]
print("=== templates/product.json ===")
print(pj[:4000])

# List product-related liquid files
r2 = httpx.get(f"{API}/themes/{THEME}/assets.json", headers=RH, timeout=30)
assets = [a["key"] for a in r2.json().get("assets", [])]
prod_assets = [k for k in assets if "product" in k.lower() and k.endswith(".liquid")]
print("\n=== Product liquid files ===")
for k in sorted(prod_assets):
    print(f"  {k}")
