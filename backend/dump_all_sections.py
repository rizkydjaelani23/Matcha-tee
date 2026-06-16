"""Dump all sections in settings_data.json to understand theme layout."""
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

r = httpx.get(f"{API}/themes/{THEME_ID}/assets.json", headers=RH,
              params={"asset[key]": "config/settings_data.json"}, timeout=15)
settings = json.loads(r.json()["asset"]["value"])
current = settings.get("current", {})
sections = current.get("sections", {})

print(f"Total sections in settings_data.json: {len(sections)}")
for key, sec in sections.items():
    stype = sec.get("type", "?")
    n_blocks = len(sec.get("blocks", {}))
    print(f"  [{key}]  type={stype}  blocks={n_blocks}")
    if n_blocks > 0:
        for bkey, block in sec.get("blocks", {}).items():
            bs = block.get("settings", {})
            menu_val = bs.get("menu", "(not set)")
            print(f"    block {bkey}  type={block.get('type')}  menu={menu_val}")
