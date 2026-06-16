"""Fetch a single theme asset and print it."""
import os, sys, httpx
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
STORE = os.environ["SHOPIFY_STORE"]
TOKEN = os.environ["SHOPIFY_TOKEN"]
HR = {"X-Shopify-Access-Token": TOKEN}
API = f"https://{STORE}/admin/api/2025-01"
THEME_ID = 143507587185

key = sys.argv[1] if len(sys.argv) > 1 else "sections/product-information.liquid"
r = httpx.get(f"{API}/themes/{THEME_ID}/assets.json", headers=HR, params={"asset[key]": key}, timeout=30)
asset = r.json().get("asset", {})
print(asset.get("value", ""))
