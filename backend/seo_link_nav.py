"""Add About Us + Style Guide (blog) into footer & main menus for crawlability/SEO."""
import os, sys, json, time
import httpx
from dotenv import load_dotenv
sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
STORE = os.environ["SHOPIFY_STORE"]
TOKEN = os.environ["SHOPIFY_TOKEN"]
H     = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}
GQL   = f"https://{STORE}/admin/api/2025-01/graphql.json"
BASE  = f"https://{STORE}"   # use myshopify base; Shopify maps to primary domain

def gql(q, v=None):
    return httpx.post(GQL, headers=H, json={"query": q, "variables": v or {}}, timeout=30).json()

DETAIL = """{ menus(first:20){ edges{ node{
  id handle title
  items { id title url type items { id title url type } }
} } } }"""

menus = {e["node"]["handle"]: e["node"] for e in gql(DETAIL)["data"]["menus"]["edges"]}

def to_input(items):
    out=[]
    for it in items:
        d={"id":it["id"],"title":it["title"],"url":it["url"],"type":it["type"]}
        if it.get("items"):
            d["items"]=[{"id":s["id"],"title":s["title"],"url":s["url"],"type":s["type"]} for s in it["items"]]
        out.append(d)
    return out

def new_item(title, url):
    return {"title": title, "url": url, "type": "HTTP"}

UPDATE = """mutation upd($id: ID!, $title: String!, $handle: String!, $items: [MenuItemUpdateInput!]!) {
  menuUpdate(id:$id, title:$title, handle:$handle, items:$items) {
    menu { id items { title } } userErrors { field message }
  }
}"""

# ── Footer: add About Us + Style Guide if missing ─────────────────────────────
f = menus.get("footer")
if f:
    items = to_input(f["items"])
    titles = {i["title"] for i in items}
    if "About Us" not in titles:
        items.insert(0, new_item("About Us", f"{BASE}/pages/about"))
    if "Style Guide" not in titles:
        items.append(new_item("Style Guide", f"{BASE}/blogs/style-guide"))
    r = gql(UPDATE, {"id": f["id"], "title": "Footer", "handle": "footer", "items": items})
    errs = r.get("data",{}).get("menuUpdate",{}).get("userErrors",[])
    print(f"Footer: {'OK' if not errs else errs}  -> {[i['title'] for i in r['data']['menuUpdate']['menu']['items']]}")
    time.sleep(0.4)

# ── Main menu: add Style Guide ────────────────────────────────────────────────
m = menus.get("main-menu")
if m:
    items = to_input(m["items"])
    titles = {i["title"] for i in items}
    if "Style Guide" not in titles:
        items.append(new_item("Style Guide", f"{BASE}/blogs/style-guide"))
    r = gql(UPDATE, {"id": m["id"], "title": "Main Menu", "handle": "main-menu", "items": items})
    errs = r.get("data",{}).get("menuUpdate",{}).get("userErrors",[])
    print(f"Main menu: {'OK' if not errs else errs}  -> {[i['title'] for i in r['data']['menuUpdate']['menu']['items']]}")

print("\nNav linking done.")
