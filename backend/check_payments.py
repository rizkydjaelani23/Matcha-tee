"""Check current payment gateways on the store."""
import os, sys, httpx
from dotenv import load_dotenv
sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
STORE = os.environ["SHOPIFY_STORE"]
RH = {"X-Shopify-Access-Token": os.environ["SHOPIFY_TOKEN"]}
API = f"https://{STORE}/admin/api/2025-01"

r = httpx.get(f"{API}/payment_gateways.json", headers=RH, timeout=15)
print("Payment gateways:")
for g in r.json().get("payment_gateways", []):
    print(f"  [{g['id']}] {g['name']}  enabled={g.get('enabled')}  type={g.get('provider_type', g.get('type',''))}")
