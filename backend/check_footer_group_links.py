"""Check what group_links contains in the footer-group.json."""
import os, sys, json, httpx
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

STORE    = os.environ["SHOPIFY_STORE"]
TOKEN    = os.environ["SHOPIFY_TOKEN"]
RH       = {"X-Shopify-Access-Token": TOKEN}
API      = f"https://{STORE}/admin/api/2025-01"
THEME_ID = 143507587185

r = httpx.get(f"{API}/themes/{THEME_ID}/assets.json", headers=RH,
              params={"asset[key]": "sections/footer-group.json"}, timeout=15)
fgj = json.loads(r.json()["asset"]["value"])

footer_sec = fgj["sections"]["footer_m9NzUG"]
print("footer_m9NzUG block_order:", footer_sec.get("block_order"))

# Print full JSON of each block
for bkey, block in footer_sec.get("blocks", {}).items():
    print(f"\n--- block: {bkey} ---")
    print(json.dumps(block, indent=2)[:1000])
