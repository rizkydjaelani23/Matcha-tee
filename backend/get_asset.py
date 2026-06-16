import os, sys, httpx
from dotenv import load_dotenv
sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
STORE = os.environ["SHOPIFY_STORE"]
H = {"X-Shopify-Access-Token": os.environ["SHOPIFY_TOKEN"]}
API = f"https://{STORE}/admin/api/2025-01"
THEME_ID = 143507587185

keys = ["templates/product.json", "sections/product-information.liquid",
        "sections/main-collection.liquid"]
for key in keys:
    r = httpx.get(f"{API}/themes/{THEME_ID}/assets.json", headers=H,
                  params={"asset[key]": key}, timeout=30)
    val = r.json()["asset"].get("value", "")
    fn = key.replace("/", "_")
    with open(os.path.join(os.path.dirname(__file__), fn), "w", encoding="utf-8") as f:
        f.write(val)
    print(f"{key}: {len(val)} bytes -> {fn}")
