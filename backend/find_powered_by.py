"""Find where 'Powered by Shopify' is rendered in the theme."""
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

needles = ["powered_by", "powered by", "shopify_link", "powered-by"]
hits = []
for key in assets:
    if not (key.endswith(".liquid") or key.endswith(".json")):
        continue
    try:
        rr = httpx.get(f"{API}/themes/{THEME}/assets.json", headers=RH,
                       params={"asset[key]": key}, timeout=15)
        content = rr.json().get("asset", {}).get("value", "")
    except Exception:
        continue
    low = content.lower()
    for n in needles:
        if n in low:
            # print matching lines
            for i, line in enumerate(content.split("\n"), 1):
                if n in line.lower():
                    print(f"{key}:{i}: {line.strip()[:120]}")
            hits.append(key)
            break

print("\nFiles with matches:", set(hits))
