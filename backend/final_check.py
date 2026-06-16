"""Final state check — menus and footer configuration."""
import os, sys, json, httpx
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

STORE    = os.environ["SHOPIFY_STORE"]
TOKEN    = os.environ["SHOPIFY_TOKEN"]
H        = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}
RH       = {"X-Shopify-Access-Token": TOKEN}
GQL      = f"https://{STORE}/admin/api/2025-01/graphql.json"
API      = f"https://{STORE}/admin/api/2025-01"
THEME_ID = 143507587185

# ── 1. Menus ──────────────────────────────────────────────────────────────────
q = """{ menus(first:10){ edges{ node{
  id handle title
  items { title url items { title url } }
} } } }"""
r = httpx.post(GQL, headers=H, json={"query": q}, timeout=15)
print("=== MENUS ===")
for edge in r.json()["data"]["menus"]["edges"]:
    m = edge["node"]
    print(f"\n  [{m['handle']}] {m['title']}")
    for item in m.get("items", []):
        children = item.get("items", [])
        child_str = f"  ↳ {', '.join(c['title'] for c in children)}" if children else ""
        print(f"    - {item['title']}{child_str}")

# ── 2. Footer block order ─────────────────────────────────────────────────────
r2 = httpx.get(f"{API}/themes/{THEME_ID}/assets.json", headers=RH,
               params={"asset[key]": "sections/footer-group.json"}, timeout=15)
fgj = json.loads(r2.json()["asset"]["value"])
footer_sec = fgj["sections"]["footer_m9NzUG"]
print("\n=== FOOTER BLOCK ORDER ===")
for bkey in footer_sec.get("block_order", []):
    block = footer_sec["blocks"].get(bkey, {})
    btype = block.get("type", "?")
    bmenu = block.get("settings", {}).get("menu", "")
    extra = f"  menu→{bmenu}" if bmenu else ""
    print(f"  {bkey}  ({btype}){extra}")

# ── 3. Header menu setting ─────────────────────────────────────────────────────
r3 = httpx.get(f"{API}/themes/{THEME_ID}/assets.json", headers=RH,
               params={"asset[key]": "sections/header-group.json"}, timeout=15)
hgj = json.loads(r3.json()["asset"]["value"])
header_sec = hgj["sections"]["header_section"]
header_menu_block = header_sec["blocks"].get("header-menu", {})
print("\n=== HEADER MENU SETTING ===")
print(f"  menu handle: {header_menu_block.get('settings', {}).get('menu', '(not set)')}")

# ── 4. Collections ────────────────────────────────────────────────────────────
r4 = httpx.get(f"{API}/custom_collections.json", headers=RH, timeout=15)
print("\n=== COLLECTIONS ===")
for c in r4.json().get("custom_collections", []):
    print(f"  [{c['id']}] {c['title']} — {c['handle']}")
