"""Check how the Horizon footer references its menu."""
import os, sys, httpx
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

STORE    = os.environ["SHOPIFY_STORE"]
TOKEN    = os.environ["SHOPIFY_TOKEN"]
RH       = {"X-Shopify-Access-Token": TOKEN}
API      = f"https://{STORE}/admin/api/2025-01"
THEME_ID = 143507587185

# List all section assets
r = httpx.get(f"{API}/themes/{THEME_ID}/assets.json", headers=RH, timeout=30)
assets = [a["key"] for a in r.json().get("assets", [])]

# Find footer-related assets
footer_assets = [k for k in assets if "footer" in k.lower() and k.endswith(".liquid")]
print("Footer-related liquid files:", footer_assets)

# Check each for menu references
for key in footer_assets:
    r2 = httpx.get(f"{API}/themes/{THEME_ID}/assets.json", headers=RH,
                   params={"asset[key]": key}, timeout=15)
    content = r2.json().get("asset", {}).get("value", "")
    menu_lines = [(i+1, l.rstrip()) for i, l in enumerate(content.split("\n"))
                  if "menu" in l.lower() or "footer" in l.lower() or "linklist" in l.lower()
                  or '"default"' in l]
    if menu_lines:
        print(f"\n=== {key} ===")
        for lineno, line in menu_lines[:30]:
            print(f"  {lineno}: {line}")
