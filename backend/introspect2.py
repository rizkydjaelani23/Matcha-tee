import os, httpx
from dotenv import load_dotenv
load_dotenv()
STORE = os.environ["SHOPIFY_STORE"]
TOKEN = os.environ["SHOPIFY_TOKEN"]
H = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}
RH = {"X-Shopify-Access-Token": TOKEN}
API = f"https://{STORE}/admin/api/2025-01"

# Check payment gateways via REST
r = httpx.get(f"{API}/payment_gateways.json", headers=RH, timeout=15)
print("=== Payment Gateways ===")
for g in r.json().get("payment_gateways", []):
    print(f"  {g['name']} | provider={g.get('provider_type','')} | enabled={g.get('enabled','')} | currencies={g.get('currencies',[])} | multi_currency={g.get('multi_currency_supported','?')}")

# Check shop info
r2 = httpx.get(f"{API}/shop.json", headers=RH, timeout=15)
shop = r2.json().get("shop", {})
print(f"\n=== Shop Currency ===")
print(f"  currency: {shop.get('currency')}")
print(f"  money_format: {shop.get('money_format')}")
print(f"  money_with_currency_format: {shop.get('money_with_currency_format')}")
print(f"  enabled_presentment_currencies: {shop.get('enabled_presentment_currencies')}")
