"""Check how many products have empty descriptions."""
import json, os, httpx
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
STORE = os.environ["SHOPIFY_STORE"]
TOKEN = os.environ["SHOPIFY_TOKEN"]
HR = {"X-Shopify-Access-Token": TOKEN}
API = f"https://{STORE}/admin/api/2025-01"

empty = has_desc = 0
page_info = None
while True:
    params = {"limit": 50, "fields": "id,title,body_html"}
    if page_info:
        params = {"limit": 50, "fields": "id,title,body_html", "page_info": page_info}
    r = httpx.get(f"{API}/products.json", headers=HR, params=params, timeout=30)
    products = r.json().get("products", [])
    for p in products:
        body = (p.get("body_html") or "").strip()
        if body:
            has_desc += 1
        else:
            empty += 1
            print(f"  EMPTY desc: {p['id']} — {p['title'][:60]}")
    link = r.headers.get("Link", "")
    if 'rel="next"' not in link:
        break
    import re
    m = re.search(r'page_info=([^&>]+).*rel="next"', link)
    if not m:
        break
    page_info = m.group(1)

print(f"\nHas description: {has_desc}  |  Empty: {empty}")
