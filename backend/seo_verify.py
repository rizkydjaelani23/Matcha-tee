"""Verify SEO landed: product seo, image alt, collection seo, page metafield, articles."""
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

q = """{
  products(first: 2) { edges { node {
    title seo { title description }
    images(first: 2) { edges { node { altText } } }
  } } }
  collections(first: 2) { edges { node { handle seo { title description } } } }
}"""
d = httpx.post(GQL, headers=H, json={"query": q}, timeout=20).json()["data"]

print("=== PRODUCTS ===")
for e in d["products"]["edges"]:
    n = e["node"]
    print(f"  {n['title']}")
    print(f"    seo.title: {n['seo']['title']}")
    print(f"    alt texts: {[i['node']['altText'] for i in n['images']['edges']]}")

print("\n=== COLLECTIONS ===")
for e in d["collections"]["edges"]:
    n = e["node"]
    print(f"  {n['handle']}: {n['seo']['title']}")

# page metafield
pages = httpx.get(f"{API}/pages.json?limit=50", headers=RH, timeout=15).json()["pages"]
faq = next(p for p in pages if p["handle"]=="faq")
mf = httpx.get(f"{API}/pages/{faq['id']}/metafields.json", headers=RH, timeout=15).json()["metafields"]
print("\n=== FAQ PAGE METAFIELDS ===")
for m in mf:
    if m["namespace"]=="global":
        print(f"  {m['key']}: {m['value'][:70]}")

# blog count
blogs = httpx.get(f"{API}/blogs.json", headers=RH, timeout=15).json()["blogs"]
b = blogs[0]
cnt = httpx.get(f"{API}/blogs/{b['id']}/articles/count.json", headers=RH, timeout=15).json()["count"]
print(f"\n=== BLOG ===\n  {b['title']} ({b['handle']}): {cnt} articles")
