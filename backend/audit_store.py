import os, sys, httpx
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
STORE=os.environ["SHOPIFY_STORE"]; TOKEN=os.environ["SHOPIFY_TOKEN"]
RH={"X-Shopify-Access-Token":TOKEN}
API=f"https://{STORE}/admin/api/2025-01"

def g(path):
    return httpx.get(f"{API}/{path}", headers=RH, timeout=20).json()

shop = g("shop.json")["shop"]
print("== SHOP ==")
print(f"  name: {shop.get('name')}")
print(f"  email: {shop.get('email')}")
print(f"  currency: {shop.get('currency')}  presentment: {shop.get('enabled_presentment_currencies')}")
print(f"  plan: {shop.get('plan_display_name')}")

print("\n== POLICIES ==")
pols = g("policies.json").get("policies", [])
if not pols:
    print("  NONE set")
for p in pols:
    print(f"  {p.get('title')}  ({len(p.get('body','') or '')} chars)")

print("\n== PAGES ==")
pages = g("pages.json?limit=250").get("pages", [])
if not pages:
    print("  NONE")
for p in pages:
    print(f"  {p.get('title')}  /pages/{p.get('handle')}")

print("\n== NAV MENUS ==")
try:
    menus = g("menus.json").get("menus", [])
    for m in menus:
        print(f"  {m.get('title')} ({m.get('handle')}) - {len(m.get('items',[]))} items")
except Exception:
    print("  (menus API not available)")

print("\n== COUNTS ==")
pc = httpx.get(f"{API}/products/count.json", headers=RH, timeout=15).json().get("count")
cc = httpx.get(f"{API}/custom_collections/count.json", headers=RH, timeout=15).json().get("count")
sc = httpx.get(f"{API}/smart_collections/count.json", headers=RH, timeout=15).json().get("count")
ac = httpx.get(f"{API}/blogs/91457585265/articles/count.json", headers=RH, timeout=15).json().get("count")
print(f"  products: {pc}   collections: custom={cc} smart={sc}   blog articles: {ac}")

print("\n== WEBHOOKS ==")
wh = g("webhooks.json").get("webhooks", [])
print(f"  count: {len(wh)}")
for w in wh[:10]:
    print(f"    {w.get('topic')} -> {w.get('address','')[:50]}")
