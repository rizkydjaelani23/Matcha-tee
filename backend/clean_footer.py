"""Remove the old group_links block from footer (it has incomplete links) — keep the proper footer menu block."""
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
KEY      = "sections/footer-group.json"

r = httpx.get(f"{API}/themes/{THEME_ID}/assets.json", headers=RH,
              params={"asset[key]": KEY}, timeout=15)
fgj = json.loads(r.json()["asset"]["value"])

footer_sec = fgj["sections"]["footer_m9NzUG"]

# Remove old group_links block and any duplicate Help block
remove_blocks = ["group_links"]
for bid in remove_blocks:
    if bid in footer_sec["blocks"]:
        del footer_sec["blocks"][bid]
        print(f"Removed block: {bid}")

# Remove from block_order
footer_sec["block_order"] = [b for b in footer_sec.get("block_order", [])
                              if b not in remove_blocks]
print(f"New block_order: {footer_sec['block_order']}")

# Push
r2 = httpx.put(
    f"{API}/themes/{THEME_ID}/assets.json",
    headers=H,
    json={"asset": {"key": KEY, "value": json.dumps(fgj, ensure_ascii=False)}},
    timeout=30,
)
print(f"PUT {KEY}: {r2.status_code}")
if r2.status_code in (200, 201):
    print("Footer cleaned. Old group_links removed. footer_menu_nav (FAQ, Shipping, etc.) is now the only nav in footer.")
