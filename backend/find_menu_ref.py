"""Find where the Horizon theme's header-menu block references the menu handle."""
import os, sys, httpx
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

STORE    = os.environ["SHOPIFY_STORE"]
TOKEN    = os.environ["SHOPIFY_TOKEN"]
RH       = {"X-Shopify-Access-Token": TOKEN}
API      = f"https://{STORE}/admin/api/2025-01"
THEME_ID = 143507587185

# List all assets
r = httpx.get(f"{API}/themes/{THEME_ID}/assets.json", headers=RH, timeout=30)
assets = [a["key"] for a in r.json().get("assets", [])]

# Find block files that might be _header-menu
print("Blocks and snippets containing 'header' or 'menu':")
for key in assets:
    if ("header" in key.lower() or "menu" in key.lower()) and key.endswith(".liquid"):
        print(f"  {key}")

# Fetch the _header-menu block
for key in assets:
    if "header-menu" in key and key.endswith(".liquid"):
        print(f"\n=== {key} ===")
        r2 = httpx.get(f"{API}/themes/{THEME_ID}/assets.json", headers=RH,
                       params={"asset[key]": key}, timeout=15)
        content = r2.json().get("asset", {}).get("value", "")
        # Show lines with menu references
        for i, line in enumerate(content.split("\n"), 1):
            if "menu" in line.lower() or "linklists" in line.lower() or "navigation" in line.lower():
                print(f"  {i}: {line.rstrip()}")
