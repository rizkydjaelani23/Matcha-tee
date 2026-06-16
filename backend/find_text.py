"""Search all theme assets for a given text string."""
import httpx, os, sys
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

TOKEN = os.environ["SHOPIFY_TOKEN"]
STORE = os.environ["SHOPIFY_STORE"]
THEME = 143507587185
H = {"X-Shopify-Access-Token": TOKEN}

search = sys.argv[1] if len(sys.argv) > 1 else "Tracked"

# Get all assets
r = httpx.get(f"https://{STORE}/admin/api/2025-01/themes/{THEME}/assets.json", headers=H, timeout=20)
assets = r.json().get("assets", [])

print(f"Searching for: '{search}' across {len(assets)} assets...\n")
found = []
for a in assets:
    key = a["key"]
    if not key.endswith((".liquid", ".json", ".css", ".js")):
        continue
    r2 = httpx.get(f"https://{STORE}/admin/api/2025-01/themes/{THEME}/assets.json",
        headers=H, params={"asset[key]": key}, timeout=20)
    val = r2.json().get("asset", {}).get("value", "")
    if search.lower() in val.lower():
        # Find the line
        for i, line in enumerate(val.splitlines(), 1):
            if search.lower() in line.lower():
                print(f"  [{key}:{i}]  {line.strip()[:120]}")
                found.append(key)
                break

if not found:
    print("Not found in any asset.")
