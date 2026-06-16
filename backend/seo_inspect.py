"""Inspect current SEO state: products, collections, pages, blogs, shop."""
import os, sys, json, httpx
from dotenv import load_dotenv
sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
STORE = os.environ["SHOPIFY_STORE"]
TOKEN = os.environ["SHOPIFY_TOKEN"]
RH    = {"X-Shopify-Access-Token": TOKEN}
H     = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}
API   = f"https://{STORE}/admin/api/2025-01"
GQL   = f"https://{STORE}/admin/api/2025-01/graphql.json"

# Shop
shop = httpx.get(f"{API}/shop.json", headers=RH, timeout=15).json()["shop"]
print("=== SHOP ===")
print(f"  name: {shop.get('name')}")
print(f"  primary_domain: {shop.get('domain')}  / {shop.get('primary_domain',{})}")

# Sample product via GraphQL to see seo field + counts
q = """{
  products(first: 3) {
    edges { node {
      id title handle productType
      seo { title description }
      featuredImage { altText }
      description
    } }
  }
  productsCount: productsCount { count }
}"""
r = httpx.post(GQL, headers=H, json={"query": q}, timeout=20)
data = r.json()
print("\n=== PRODUCTS (sample) ===")
try:
    print(f"  total: {data['data']['productsCount']['count']}")
except Exception:
    print("  count query unsupported:", data.get("errors"))
for e in data.get("data",{}).get("products",{}).get("edges",[]):
    n = e["node"]
    print(f"\n  {n['title']}  type={n.get('productType')!r}")
    print(f"    seo.title: {n['seo'].get('title')}")
    print(f"    seo.desc:  {n['seo'].get('description')}")
    print(f"    img alt:   {(n.get('featuredImage') or {}).get('altText')}")
    desc = (n.get('description') or '')[:80]
    print(f"    desc[:80]: {desc}")

# Collections
cols = httpx.get(f"{API}/custom_collections.json", headers=RH, timeout=15).json().get("custom_collections", [])
print("\n=== COLLECTIONS ===")
for c in cols:
    print(f"  [{c['id']}] {c['title']} handle={c['handle']}")

# Pages
pages = httpx.get(f"{API}/pages.json?limit=50", headers=RH, timeout=15).json().get("pages", [])
print(f"\n=== PAGES ({len(pages)}) ===")
for p in pages:
    print(f"  [{p['id']}] {p['title']} handle={p['handle']}")

# Blogs
blogs = httpx.get(f"{API}/blogs.json", headers=RH, timeout=15).json().get("blogs", [])
print(f"\n=== BLOGS ({len(blogs)}) ===")
for b in blogs:
    arts = httpx.get(f"{API}/blogs/{b['id']}/articles/count.json", headers=RH, timeout=15).json()
    print(f"  [{b['id']}] {b['title']} handle={b['handle']}  articles={arts.get('count')}")
