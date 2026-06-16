import os, sys, json, httpx
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

STORE = os.environ["SHOPIFY_STORE"]
TOKEN = os.environ["SHOPIFY_TOKEN"]
HR = {"X-Shopify-Access-Token": TOKEN}
H  = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}
API = f"https://{STORE}/admin/api/2025-01"

# Sales channels / publications
r = httpx.get(f"{API}/publications.json", headers=HR, timeout=20)
pubs = r.json().get("publications", [])
print("Publications (sales channels):")
for p in pubs:
    print(f"  {p['id']}: {p['name']}")

# Collections
r2 = httpx.get(f"{API}/custom_collections.json?limit=250", headers=HR, timeout=20)
colls = r2.json().get("custom_collections", [])
print("\nCustom collections:")
for c in colls:
    print(f"  {c['id']}: {c['title']}")

# Sample product — check its publications
r3 = httpx.get(f"{API}/products.json?limit=1&fields=id,title,status", headers=HR, timeout=20)
prods = r3.json().get("products", [])
if prods:
    pid = prods[0]["id"]
    print(f"\nSample product: {prods[0]['title']} (id={pid})")
    r4 = httpx.get(f"{API}/products/{pid}/collection_listings.json", headers=HR, timeout=20)
    print(f"  collection_listings status: {r4.status_code}")
    # Check if published to online store via collects
    r5 = httpx.get(f"{API}/products/{pid}/collects.json", headers=HR, timeout=20)
    collects = r5.json().get("collects", [])
    print(f"  In {len(collects)} collections: {[c['collection_id'] for c in collects]}")
    # Check published scope
    r6 = httpx.get(f"{API}/products/{pid}.json?fields=id,title,status,published_at,published_scope", headers=HR, timeout=20)
    p = r6.json().get("product", {})
    print(f"  status={p.get('status')}  published_at={p.get('published_at')}  scope={p.get('published_scope')}")
