"""
Fetch sections/footer-group.json, add a menu block pointing to 'footer',
and push it back to the theme.
"""
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

KEY = "sections/footer-group.json"

# Fetch current footer-group.json
r = httpx.get(f"{API}/themes/{THEME_ID}/assets.json", headers=RH,
              params={"asset[key]": KEY}, timeout=15)
raw = r.json()["asset"]["value"]
fgj = json.loads(raw)

print("Current footer sections:", list(fgj["sections"].keys()))

# Find the footer section key (type == "footer")
footer_section_key = None
for k, sec in fgj["sections"].items():
    if sec.get("type") == "footer":
        footer_section_key = k
        break

if not footer_section_key:
    print("ERROR: No footer type section found")
    sys.exit(1)

footer_sec = fgj["sections"][footer_section_key]
print(f"Footer section key: {footer_section_key}")
print(f"Current block_order: {footer_sec.get('block_order', [])}")
print(f"Current blocks: {list(footer_sec.get('blocks', {}).keys())}")

# Add a menu block pointing to 'footer'
menu_block_id = "footer_menu_nav"
footer_sec["blocks"][menu_block_id] = {
    "type": "menu",
    "settings": {
        "menu": "footer",
        "heading": "Help & Info",
        "menu_style": "text",
        "accordion": False,
        "accordion_expand_first": True,
        "dividers": False,
        "inherit_color_scheme": True,
        "color_scheme": "",
        "width": "fit",
        "custom_width": 25,
        "width_mobile": "fill",
        "custom_width_mobile": 100,
        "height": "fit",
        "custom_height": 100,
        "padding-block-start": 0,
        "padding-block-end": 0,
        "padding-inline-start": 0,
        "padding-inline-end": 0
    },
    "blocks": {}
}

# Insert menu block at the beginning of block_order
block_order = footer_sec.get("block_order", [])
if menu_block_id not in block_order:
    footer_sec["block_order"] = [menu_block_id] + block_order

print(f"New block_order: {footer_sec['block_order']}")

# Push updated footer-group.json
new_raw = json.dumps(fgj, ensure_ascii=False)
r2 = httpx.put(
    f"{API}/themes/{THEME_ID}/assets.json",
    headers=H,
    json={"asset": {"key": KEY, "value": new_raw}},
    timeout=30,
)
print(f"\nPUT {KEY}: {r2.status_code}")
if r2.status_code not in (200, 201):
    print(r2.text[:500])
else:
    print("Footer menu block added successfully.")
    print("Footer navigation (FAQ, Shipping, Returns, T&C, Privacy, Contact, Affiliates, Wholesale) is now live.")
