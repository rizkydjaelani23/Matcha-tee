"""Check the footer menu block's default menu handle."""
import os, sys, json, httpx
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

STORE    = os.environ["SHOPIFY_STORE"]
TOKEN    = os.environ["SHOPIFY_TOKEN"]
RH       = {"X-Shopify-Access-Token": TOKEN}
H        = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}
API      = f"https://{STORE}/admin/api/2025-01"
THEME_ID = 143507587185

# Check blocks/menu.liquid for default menu handle
r = httpx.get(f"{API}/themes/{THEME_ID}/assets.json", headers=RH,
              params={"asset[key]": "blocks/menu.liquid"}, timeout=15)
content = r.json().get("asset", {}).get("value", "")

print("=== blocks/menu.liquid menu references ===")
for i, line in enumerate(content.split("\n"), 1):
    if "menu" in line.lower() or "default" in line.lower() or "linklist" in line.lower() or "footer" in line.lower():
        print(f"  {i}: {line.rstrip()}")

# Also dump the current settings_data.json sections that are of type 'footer' or 'footer.liquid'
r2 = httpx.get(f"{API}/themes/{THEME_ID}/assets.json", headers=RH,
               params={"asset[key]": "config/settings_data.json"}, timeout=15)
settings = json.loads(r2.json()["asset"]["value"])
sections = settings.get("current", {}).get("sections", {})

print("\n=== footer-related sections and their blocks ===")
for key, sec in sections.items():
    stype = sec.get("type", "")
    if "footer" in stype.lower() or "footer" in key.lower():
        print(f"\n  section: {key}  type={stype}")
        print(f"  settings: {sec.get('settings', {})}")
        for bkey, block in sec.get("blocks", {}).items():
            print(f"  block: {bkey}  type={block.get('type')}  settings={block.get('settings', {})}")
        print(f"  block_order: {sec.get('block_order', [])}")
