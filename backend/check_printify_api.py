import httpx, os, sys, json
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
TOKEN = os.environ["PRINTIFY_TOKEN"]
PH = {"Authorization": f"Bearer {TOKEN}"}
PAPI = "https://api.printify.com/v1"

# 1. Get shops (find the one linked to matcha-tees.myshopify.com)
r = httpx.get(f"{PAPI}/shops.json", headers=PH, timeout=20)
print("Shops:", r.status_code)
shops = r.json() if r.status_code == 200 else []
if isinstance(shops, list):
    for s in shops:
        print(f"  id={s['id']}  title={s['title']}  sales_channel={s.get('sales_channel','')}")
else:
    print(shops)

# 2. Get popular t-shirt blueprints
print("\nSearching blueprints for t-shirts...")
r2 = httpx.get(f"{PAPI}/catalog/blueprints.json", headers=PH, timeout=30)
blueprints = r2.json() if r2.status_code == 200 else []
tshirts = [b for b in blueprints if "t-shirt" in b.get("title","").lower() or "tee" in b.get("title","").lower()]
print(f"Found {len(tshirts)} t-shirt blueprints. Top options:")
for b in tshirts[:15]:
    print(f"  id={b['id']:4}  {b['title']}")
