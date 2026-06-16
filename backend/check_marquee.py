import httpx, os, json, sys
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
TOKEN = os.environ["SHOPIFY_TOKEN"]
STORE = os.environ["SHOPIFY_STORE"]
THEME = 143507587185
H = {"X-Shopify-Access-Token": TOKEN}

def get_asset(key):
    r = httpx.get(f"https://{STORE}/admin/api/2025-01/themes/{THEME}/assets.json",
        headers=H, params={"asset[key]": key}, timeout=20)
    return r.json()["asset"]["value"]

# Check the homepage JSON for marquee content
raw = get_asset("templates/index.json")
parsed = json.loads(raw)
marquee = parsed["sections"].get("marquee_strip", {})
print("Marquee section:")
print(json.dumps(marquee, indent=2))
