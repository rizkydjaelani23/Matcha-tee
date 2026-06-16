"""Dump all blocks in settings_data.json that reference a menu or navigation."""
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
              params={"asset[key]": "config/settings_data.json"}, timeout=15)
settings = json.loads(r.json()["asset"]["value"])

current = settings.get("current", {})

# Check all sections and their blocks
sections = current.get("sections", {})
print("=== Sections and blocks with menu/nav references ===")
for skey, sec in sections.items():
    blocks = sec.get("blocks", {})
    for bkey, block in blocks.items():
        bs = block.get("settings", {})
        if any("menu" in k.lower() or "nav" in k.lower() for k in bs):
            print(f"\n  section={skey} block={bkey} type={block.get('type')}")
            for k, v in bs.items():
                print(f"    {k} = {repr(v)}")

# Also dump ALL block settings to find header-menu block
print("\n=== All blocks (header-menu type) ===")
for skey, sec in sections.items():
    blocks = sec.get("blocks", {})
    for bkey, block in blocks.items():
        btype = block.get("type", "")
        if "header" in btype.lower() or "menu" in btype.lower() or bkey == "header-menu":
            print(f"\n  section={skey} block={bkey} type={btype}")
            print(f"    settings={block.get('settings', {})}")

# Find the block with id matching 'header-menu'
print("\n=== Looking for header-menu block id ===")
for skey, sec in sections.items():
    blocks = sec.get("blocks", {})
    for bkey, block in blocks.items():
        if bkey == "header-menu":
            print(f"  FOUND: section={skey} type={block.get('type')}")
            print(f"  settings={json.dumps(block.get('settings', {}), indent=4)}")
