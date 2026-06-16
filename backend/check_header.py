"""Check how the Horizon theme header references the navigation menu."""
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


def get_asset(key):
    r = httpx.get(f"{API}/themes/{THEME_ID}/assets.json", headers=RH,
                  params={"asset[key]": key}, timeout=15)
    return r.json().get("asset", {}).get("value", "")


# Check header section schema for menu settings
header_liq = get_asset("sections/header.liquid")
if header_liq:
    # Find lines referencing menu
    lines = header_liq.split("\n")
    for i, line in enumerate(lines):
        if "menu" in line.lower() or "navigation" in line.lower():
            print(f"  header.liquid:{i+1}  {line.rstrip()}")
else:
    print("No sections/header.liquid found")
    # Try sections/announcement-bar.liquid or layout/theme.liquid
    theme_liq = get_asset("layout/theme.liquid")
    if theme_liq:
        for i, line in enumerate(theme_liq.split("\n")):
            if "main-menu" in line or "navigation" in line.lower():
                print(f"  layout/theme.liquid:{i+1}  {line.rstrip()}")

# Also dump the full settings for header/footer sections
r2 = httpx.get(f"{API}/themes/{THEME_ID}/assets.json", headers=RH,
               params={"asset[key]": "config/settings_data.json"}, timeout=15)
settings = json.loads(r2.json()["asset"]["value"])
sections = settings.get("current", {}).get("sections", {})
print("\n=== All section types with settings ===")
for key, sec in sections.items():
    s = sec.get("settings", {})
    if s:
        print(f"  [{key}] type={sec.get('type')}  settings_keys={list(s.keys())[:8]}")
