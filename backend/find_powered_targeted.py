"""Check specific files + locale for 'powered by shopify'."""
import os, sys, httpx, json
from dotenv import load_dotenv
sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
STORE = os.environ["SHOPIFY_STORE"]
RH    = {"X-Shopify-Access-Token": os.environ["SHOPIFY_TOKEN"]}
API   = f"https://{STORE}/admin/api/2025-01"
THEME = 143507587185

targets = [
    "sections/footer.liquid",
    "sections/footer-utilities.liquid",
    "blocks/footer-copyright.liquid",
    "blocks/footer-policy-list.liquid",
    "snippets/footer.liquid",
    "locales/en.default.json",
]

for key in targets:
    r = httpx.get(f"{API}/themes/{THEME}/assets.json", headers=RH,
                  params={"asset[key]": key}, timeout=15)
    content = r.json().get("asset", {}).get("value", "")
    if not content:
        print(f"{key}: (not found)")
        continue
    found = False
    for i, line in enumerate(content.split("\n"), 1):
        low = line.lower()
        if "powered" in low or "powered_by" in low:
            print(f"{key}:{i}: {line.strip()[:140]}")
            found = True
    if not found:
        print(f"{key}: no 'powered' match")
