import httpx, os, sys, json
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
STORE=os.environ["SHOPIFY_STORE"]; TOKEN=os.environ["SHOPIFY_TOKEN"]
H={"X-Shopify-Access-Token":TOKEN}
API=f"https://{STORE}/admin/api/2025-01"
THEME=143507587185

# 1. Locale files in theme
r=httpx.get(f"{API}/themes/{THEME}/assets.json",headers=H,timeout=30)
assets=r.json().get("assets",[])
locales=[a["key"] for a in assets if "locales/" in a["key"]]
print("Locale files in theme:")
for l in sorted(locales): print(" ", l)

# 2. Markets
print()
r2=httpx.get(f"{API}/markets.json",headers=H,timeout=20)
markets=r2.json().get("markets",[])
for m in markets:
    print(f"Market: {m['name']} | enabled={m['enabled']}")

# 3. Check if de.json exists and has content
print()
r3=httpx.get(f"{API}/themes/{THEME}/assets.json?asset[key]=locales/de.json",headers=H,timeout=20)
if r3.status_code==200:
    val=r3.json()["asset"]["value"]
    print(f"locales/de.json exists, size={len(val)} chars")
    sample=json.loads(val)
    # show a few keys
    keys=list(sample.keys())[:5]
    print("Top-level keys:", keys)
else:
    print("locales/de.json NOT found (status", r3.status_code, ")")

# 4. Check de.schema.json
r4=httpx.get(f"{API}/themes/{THEME}/assets.json?asset[key]=locales/de.schema.json",headers=H,timeout=20)
print("locales/de.schema.json:", r4.status_code)
