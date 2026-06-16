"""Read cart-summary.liquid lines 230-310 around checkout button."""
import os, sys, httpx
from dotenv import load_dotenv
sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
STORE = os.environ["SHOPIFY_STORE"]
RH    = {"X-Shopify-Access-Token": os.environ["SHOPIFY_TOKEN"]}
API   = f"https://{STORE}/admin/api/2025-01"
THEME = 143507587185

r = httpx.get(f"{API}/themes/{THEME}/assets.json", headers=RH,
              params={"asset[key]": "snippets/cart-summary.liquid"}, timeout=15)
content = r.json()["asset"]["value"]
lines = content.split("\n")
# Show lines 230-310
for i, line in enumerate(lines[225:320], 226):
    print(f"{i:4d}: {line.rstrip()}")
