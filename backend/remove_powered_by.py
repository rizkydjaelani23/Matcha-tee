"""Set show_powered_by=false on all footer-copyright blocks in footer-group.json."""
import os, sys, json, httpx
from dotenv import load_dotenv
sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
STORE = os.environ["SHOPIFY_STORE"]
TOKEN = os.environ["SHOPIFY_TOKEN"]
H     = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}
RH    = {"X-Shopify-Access-Token": TOKEN}
API   = f"https://{STORE}/admin/api/2025-01"
THEME = 143507587185
KEY   = "sections/footer-group.json"

r = httpx.get(f"{API}/themes/{THEME}/assets.json", headers=RH,
              params={"asset[key]": KEY}, timeout=15)
fgj = json.loads(r.json()["asset"]["value"])

changed = 0

def walk_blocks(blocks):
    global changed
    for bkey, block in blocks.items():
        if block.get("type") == "footer-copyright":
            s = block.setdefault("settings", {})
            if s.get("show_powered_by") is not False:
                s["show_powered_by"] = False
                changed += 1
                print(f"  Set show_powered_by=false on block '{bkey}'")
        # recurse nested blocks
        if isinstance(block.get("blocks"), dict):
            walk_blocks(block["blocks"])

for skey, sec in fgj.get("sections", {}).items():
    if isinstance(sec.get("blocks"), dict):
        walk_blocks(sec["blocks"])

if changed == 0:
    print("No footer-copyright block found in footer-group.json — it may use schema default.")
    print("Searching all blocks for type footer-copyright...")
    for skey, sec in fgj.get("sections", {}).items():
        print(f"  section {skey} type={sec.get('type')} blocks={list(sec.get('blocks',{}).keys())}")
else:
    raw = json.dumps(fgj, ensure_ascii=False)
    r2 = httpx.put(f"{API}/themes/{THEME}/assets.json", headers=H,
                   json={"asset": {"key": KEY, "value": raw}}, timeout=30)
    print(f"PUT {KEY}: {r2.status_code}")
    if r2.status_code in (200, 201):
        print("'Powered by Shopify' removed from footer.")
