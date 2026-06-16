import httpx, os, sys
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
STORE=os.environ["SHOPIFY_STORE"]; TOKEN=os.environ["SHOPIFY_TOKEN"]
H={"X-Shopify-Access-Token":TOKEN}
API=f"https://{STORE}/admin/api/2025-01"

# Check published locales via shopify/languages
r=httpx.get(f"https://{STORE}/admin/api/2025-01/shop.json",headers=H,timeout=20)
shop=r.json()["shop"]
print("Primary locale:", shop.get("primary_locale"))

# Check all markets
r2=httpx.get(f"{API}/markets.json",headers=H,timeout=20)
for m in r2.json().get("markets",[]):
    print(f"\nMarket '{m['name']}' id={m['id']} enabled={m['enabled']}")

# Check published locales for this store
r3=httpx.get(f"https://{STORE}/admin/api/2025-01/markets.json",headers=H,timeout=20)
print()

# Try Translate & Adapt API — get languages
r4=httpx.get(f"https://{STORE}/admin/api/2025-01/markets.json",headers=H,timeout=20)
markets=r4.json().get("markets",[])
for m in markets:
    mid=m["id"]
    rl=httpx.get(f"{API}/markets/{mid}/web_presences.json",headers=H,timeout=20)
    presences=rl.json().get("web_presences",[])
    for wp in presences:
        print(f"  Market {m['name']}: subdomain={wp.get('subdomain')} alt_locales={wp.get('alternate_locales')} primary={wp.get('primary_locale')}")

# Check translatable resources count for 'de'
r5=httpx.get(f"{API}/translatable_resources/count.json?resource_type=ONLINE_STORE_THEME",headers=H,timeout=20)
print("\nTheme translatable resources:", r5.status_code, r5.text[:200])

# Check if any DE translations exist on a product
r6=httpx.get(f"{API}/products.json?limit=1&fields=id,title",headers=H,timeout=20)
pid=r6.json()["products"][0]["id"]
r7=httpx.get(f"{API}/products/{pid}/translations.json?locale=de",headers=H,timeout=20)
print(f"\nProduct {pid} DE translations:", r7.status_code, r7.text[:300])
