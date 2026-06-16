import httpx, os, sys
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
STORE=os.environ["SHOPIFY_STORE"]; TOKEN=os.environ["SHOPIFY_TOKEN"]
H={"X-Shopify-Access-Token":TOKEN}
API=f"https://{STORE}/admin/api/2025-01"

# Fulfillment services (Printify registers here when connected)
r=httpx.get(f"{API}/fulfillment_services.json",headers=H,timeout=20)
svcs=r.json().get("fulfillment_services",[])
print("Fulfillment services:")
for s in svcs:
    print(f"  id={s['id']}  name={s['name']}  handle={s['handle']}")
    print(f"    callback={s.get('callback_url','')}")

# Installed apps / carrier services
r2=httpx.get(f"{API}/carrier_services.json",headers=H,timeout=20)
print("\nCarrier services:")
for c in r2.json().get("carrier_services",[]):
    print(f"  {c['name']} -> {c.get('callback_url','')}")

# Check one product's fulfillment_service field
r3=httpx.get(f"{API}/products.json?limit=1&fields=id,title,variants",headers=H,timeout=20)
p=r3.json()["products"][0]
print(f"\nSample product: {p['title']}")
for v in p["variants"][:3]:
    print(f"  variant {v['id']} fulfillment_service={v.get('fulfillment_service')} sku={v.get('sku','')}")
