"""Push a single local file back to the theme."""
import os, sys, httpx
from dotenv import load_dotenv
sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
STORE = os.environ["SHOPIFY_STORE"]
H = {"X-Shopify-Access-Token": os.environ["SHOPIFY_TOKEN"],
     "Content-Type": "application/json"}
API = f"https://{STORE}/admin/api/2025-01"
THEME_ID = 143507587185
BASE = os.path.dirname(__file__)

# key -> local filename
assets = {
    "templates/product.json": "templates_product.json",
}

for key, fname in assets.items():
    with open(os.path.join(BASE, fname), encoding="utf-8") as f:
        value = f.read()
    r = httpx.put(f"{API}/themes/{THEME_ID}/assets.json", headers=H, timeout=60,
                  json={"asset": {"key": key, "value": value}})
    print(f"PUT {key}: {r.status_code}", "" if r.status_code == 200 else r.text[:400])
