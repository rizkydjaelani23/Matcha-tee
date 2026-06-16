"""Read the cart summary block to find where the checkout button is."""
import os, sys, httpx
from dotenv import load_dotenv
sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
STORE = os.environ["SHOPIFY_STORE"]
RH    = {"X-Shopify-Access-Token": os.environ["SHOPIFY_TOKEN"]}
API   = f"https://{STORE}/admin/api/2025-01"
THEME = 143507587185

for key in ("blocks/_cart-summary.liquid", "snippets/cart-summary.liquid", "sections/main-cart.liquid"):
    r = httpx.get(f"{API}/themes/{THEME}/assets.json", headers=RH,
                  params={"asset[key]": key}, timeout=15)
    content = r.json().get("asset", {}).get("value", "")
    if not content:
        continue
    lines = content.split("\n")
    print(f"\n=== {key} ({len(lines)} lines) ===")
    # Find checkout button area
    for i, line in enumerate(lines, 1):
        lower = line.lower()
        if any(kw in lower for kw in ("checkout", "payment", "paypal", "submit", "button", "dynamic")):
            print(f"  {i:4d}: {line.rstrip()}")
