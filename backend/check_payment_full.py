"""Check full payment setup — gateways, checkout settings, cart template."""
import os, sys, json, httpx
from dotenv import load_dotenv
sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
STORE = os.environ["SHOPIFY_STORE"]
TOKEN = os.environ["SHOPIFY_TOKEN"]
H     = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}
RH    = {"X-Shopify-Access-Token": TOKEN}
API   = f"https://{STORE}/admin/api/2025-01"
GQL   = f"https://{STORE}/admin/api/2025-01/graphql.json"
THEME = 143507587185

# 1. All payment gateways
r = httpx.get(f"{API}/payment_gateways.json", headers=RH, timeout=15)
print("=== PAYMENT GATEWAYS ===")
gws = r.json().get("payment_gateways", [])
for g in gws:
    print(f"  {g.get('name')}  enabled={g.get('enabled')}  type={g.get('type','')}  id={g.get('id')}")
if not gws:
    print("  (none via REST — checking shop info)")

# 2. Shop info to see plan / country
r2 = httpx.get(f"{API}/shop.json", headers=RH, timeout=15)
shop = r2.json().get("shop", {})
print(f"\n=== SHOP ===")
print(f"  plan: {shop.get('plan_name')}  country: {shop.get('country_name')}  currency: {shop.get('currency')}")
print(f"  checkout_api_supported: {shop.get('checkout_api_supported')}")
print(f"  has_storefront: {shop.get('has_storefront')}")

# 3. Check checkout section in cart template
r3 = httpx.get(f"{API}/themes/{THEME}/assets.json", headers=RH,
               params={"asset[key]": "templates/cart.json"}, timeout=15)
cart_json = r3.json().get("asset", {})
if cart_json:
    print(f"\n=== templates/cart.json ===")
    cj = json.loads(cart_json["value"])
    for skey, sec in cj.get("sections", {}).items():
        print(f"  section {skey}  type={sec.get('type')}  blocks={list(sec.get('blocks',{}).keys())[:8]}")
        bo = sec.get("block_order", [])
        if bo:
            print(f"    block_order: {bo}")

# 4. List cart-related liquid files
r4 = httpx.get(f"{API}/themes/{THEME}/assets.json", headers=RH, timeout=30)
assets = [a["key"] for a in r4.json().get("assets", [])]
cart_liq = [k for k in assets if "cart" in k.lower() and k.endswith(".liquid")]
print(f"\n=== CART LIQUID FILES ===")
for k in sorted(cart_liq):
    print(f"  {k}")
