import os, sys, httpx
from dotenv import load_dotenv
sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
STORE = os.environ["SHOPIFY_STORE"]
RH    = {"X-Shopify-Access-Token": os.environ["SHOPIFY_TOKEN"]}
API   = f"https://{STORE}/admin/api/2025-01"
THEME = 143507587185

r = httpx.get(f"{API}/themes/{THEME}/assets.json", headers=RH, timeout=30)
assets = [a["key"] for a in r.json().get("assets", [])]
icon_files = [k for k in assets if "icon" in k.lower()]
print("Icon-related files:")
for k in sorted(icon_files)[:20]:
    print(f"  {k}")
# Check if snippets/icon.liquid exists
if "snippets/icon.liquid" in assets:
    print("\nsnippets/icon.liquid EXISTS — checking for 'lock'...")
    r2 = httpx.get(f"{API}/themes/{THEME}/assets.json", headers=RH,
                   params={"asset[key]": "snippets/icon.liquid"}, timeout=15)
    content = r2.json().get("asset", {}).get("value", "")
    if "lock" in content.lower():
        print("  lock icon: FOUND")
    else:
        print("  lock icon: NOT found")
        # Show available icons
        import re
        icons = re.findall(r"'([^']+)'\s*(?:==|when)", content)
        print(f"  Available icons (sample): {icons[:15]}")
else:
    print("\nsnippets/icon.liquid NOT found — using plain SVG instead")
