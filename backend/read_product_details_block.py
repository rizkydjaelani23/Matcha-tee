"""Read blocks/_product-details.liquid to find buy-buttons render point."""
import os, sys, httpx
from dotenv import load_dotenv
sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
STORE = os.environ["SHOPIFY_STORE"]
RH    = {"X-Shopify-Access-Token": os.environ["SHOPIFY_TOKEN"]}
API   = f"https://{STORE}/admin/api/2025-01"
THEME = 143507587185

r = httpx.get(f"{API}/themes/{THEME}/assets.json", headers=RH,
              params={"asset[key]": "blocks/_product-details.liquid"}, timeout=15)
content = r.json()["asset"]["value"]
lines = content.split("\n")
# Show lines referencing buy, payment, content_for, children, block_order
for i, line in enumerate(lines, 1):
    lower = line.lower()
    if any(kw in lower for kw in ("buy", "payment", "content_for", "children", "for block", "render")):
        print(f"{i:4d}: {line.rstrip()}")
print(f"\nTotal lines: {len(lines)}")
