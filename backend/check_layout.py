"""Check layout/theme.liquid and find section group JSON files."""
import os, sys, json, httpx
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

STORE    = os.environ["SHOPIFY_STORE"]
TOKEN    = os.environ["SHOPIFY_TOKEN"]
RH       = {"X-Shopify-Access-Token": TOKEN}
API      = f"https://{STORE}/admin/api/2025-01"
THEME_ID = 143507587185

# List all assets and find section groups
r = httpx.get(f"{API}/themes/{THEME_ID}/assets.json", headers=RH, timeout=30)
assets = [a["key"] for a in r.json().get("assets", [])]

# Find JSON files (section group files)
json_assets = [k for k in assets if k.endswith(".json")]
print("JSON files in theme:")
for k in sorted(json_assets):
    print(f"  {k}")

# Fetch layout/theme.liquid
r2 = httpx.get(f"{API}/themes/{THEME_ID}/assets.json", headers=RH,
               params={"asset[key]": "layout/theme.liquid"}, timeout=15)
theme_liq = r2.json().get("asset", {}).get("value", "")
print("\nlayout/theme.liquid — section_group and sections references:")
for i, line in enumerate(theme_liq.split("\n"), 1):
    if "section" in line.lower() or "group" in line.lower() or "footer" in line.lower() or "header" in line.lower():
        print(f"  {i}: {line.rstrip()}")

# Fetch sections/header-group.json or layout/header-group.json if exists
for key in ["sections/header-group.json", "layout/header-group.json",
            "sections/footer-group.json", "layout/footer-group.json"]:
    if key in assets:
        r3 = httpx.get(f"{API}/themes/{THEME_ID}/assets.json", headers=RH,
                       params={"asset[key]": key}, timeout=15)
        val = r3.json().get("asset", {}).get("value", "")
        print(f"\n=== {key} ===")
        print(val[:3000])
