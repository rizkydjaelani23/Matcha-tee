"""Read blocks/text.liquid to understand HTML support."""
import os, sys, httpx
from dotenv import load_dotenv
sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
STORE = os.environ["SHOPIFY_STORE"]
RH    = {"X-Shopify-Access-Token": os.environ["SHOPIFY_TOKEN"]}
API   = f"https://{STORE}/admin/api/2025-01"
THEME = 143507587185

r = httpx.get(f"{API}/themes/{THEME}/assets.json", headers=RH,
              params={"asset[key]": "blocks/text.liquid"}, timeout=15)
content = r.json()["asset"]["value"]
# Show rendering section (first ~60 lines)
lines = content.split("\n")
for i, line in enumerate(lines[:70], 1):
    print(f"{i:3d}: {line.rstrip()}")
