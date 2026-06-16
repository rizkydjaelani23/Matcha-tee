import os, sys, httpx
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
STORE=os.environ["SHOPIFY_STORE"]; TOKEN=os.environ["SHOPIFY_TOKEN"]
RH={"X-Shopify-Access-Token":TOKEN}
API=f"https://{STORE}/admin/api/2025-01"

# first product
p=httpx.get(f"{API}/products.json?limit=1&fields=id,title,variants",headers=RH,timeout=20).json()["products"][0]
print(f"Product: {p['title']}  ({len(p['variants'])} variants)")
for v in p["variants"][:6]:
    print(f"  {v['title']:30} policy={v['inventory_policy']:9} qty={v['inventory_quantity']}")
