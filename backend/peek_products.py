import os, httpx
from dotenv import load_dotenv
load_dotenv()
STORE = os.environ["SHOPIFY_STORE"]
TOKEN = os.environ["SHOPIFY_TOKEN"]
H = {"X-Shopify-Access-Token": TOKEN}
API = f"https://{STORE}/admin/api/2025-01"

products = []
url = f"{API}/products.json?limit=250&fields=id,title,handle,product_type"
while url:
    r = httpx.get(url, headers=H, timeout=30)
    products.extend(r.json()["products"])
    link = r.headers.get("Link","")
    url = None
    for part in link.split(","):
        if 'rel="next"' in part: url = part.strip().split(";")[0].strip("<> ")

for p in products:
    print(f"{p['title']} | {p['handle']} | {p.get('product_type','')}")

print(f"\nTotal: {len(products)}")

r2 = httpx.get(f"{API}/blogs.json", headers=H, timeout=15)
print("\nBlogs:")
for b in r2.json().get("blogs",[]):
    print(f"  id={b['id']} title={b['title']} handle={b['handle']}")

r3 = httpx.get(f"{API}/blogs/{r2.json()['blogs'][0]['id']}/articles.json?limit=250&fields=id,title", headers=H, timeout=15)
print("\nExisting articles:")
for a in r3.json().get("articles",[]):
    print(f"  {a['title']}")
