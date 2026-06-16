"""Build main menu + footer menu now that navigation scope is granted."""
import json
import os
import sys

import httpx
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

STORE = os.environ["SHOPIFY_STORE"]
H = {"X-Shopify-Access-Token": os.environ["SHOPIFY_TOKEN"],
     "Content-Type": "application/json"}
GQL = f"https://{STORE}/admin/api/2025-01/graphql.json"


def gql(query, variables=None):
    r = httpx.post(GQL, headers=H, json={"query": query,
                                         "variables": variables or {}}, timeout=30)
    return r.json()


# 1. check current menus
data = gql("{ menus(first: 10) { nodes { id handle title items { id title url } } } }")
if "errors" in data:
    print("STILL DENIED:", json.dumps(data["errors"])[:300])
    sys.exit(1)

menus = data["data"]["menus"]["nodes"]
print("menus:", [(m["handle"], m["title"], len(m["items"])) for m in menus])

MAIN_ITEMS = [
    {"title": "New Releases", "type": "HTTP", "url": "/collections/new-releases", "items": []},
    {"title": "Best Sellers", "type": "HTTP", "url": "/collections/best-sellers", "items": []},
    {"title": "T-Shirts", "type": "HTTP", "url": "/collections/t-shirts", "items": []},
    {"title": "Hoodies", "type": "HTTP", "url": "/collections/hoodies-sweatshirts", "items": []},
    {"title": "Tank Tops", "type": "HTTP", "url": "/collections/tank-tops", "items": []},
    {"title": "Accessories", "type": "HTTP", "url": "/collections/accessories", "items": []},
    {"title": "Wholesale", "type": "HTTP", "url": "/pages/wholesale", "items": []},
    {"title": "Affiliates", "type": "HTTP", "url": "/pages/affiliates", "items": []},
]

FOOTER_ITEMS = [
    {"title": "Shipping Policy", "type": "HTTP", "url": "/pages/shipping-policy", "items": []},
    {"title": "Return & Refund Policy", "type": "HTTP", "url": "/pages/return-policy", "items": []},
    {"title": "Wholesale", "type": "HTTP", "url": "/pages/wholesale", "items": []},
    {"title": "Affiliates", "type": "HTTP", "url": "/pages/affiliates", "items": []},
    {"title": "Privacy Policy", "type": "HTTP", "url": "/pages/privacy-policy", "items": []},
    {"title": "Terms & Conditions", "type": "HTTP", "url": "/pages/terms-and-conditions", "items": []},
]

UPDATE_MUT = """
mutation menuUpdate($id: ID!, $title: String!, $handle: String!, $items: [MenuItemUpdateInput!]!) {
  menuUpdate(id: $id, title: $title, handle: $handle, items: $items) {
    menu { id handle items { title url } }
    userErrors { field message }
  }
}"""

CREATE_MUT = """
mutation menuCreate($title: String!, $handle: String!, $items: [MenuItemCreateInput!]!) {
  menuCreate(title: $title, handle: $handle, items: $items) {
    menu { id handle items { title url } }
    userErrors { field message }
  }
}"""


def upsert(handle, title, items):
    existing = next((m for m in menus if m["handle"] == handle), None)
    if existing:
        res = gql(UPDATE_MUT, {"id": existing["id"], "title": title,
                               "handle": handle, "items": items})
        node = res.get("data", {}).get("menuUpdate") or {}
    else:
        res = gql(CREATE_MUT, {"title": title, "handle": handle, "items": items})
        node = res.get("data", {}).get("menuCreate") or {}
    errs = node.get("userErrors") or res.get("errors")
    if errs:
        print(f"{handle}: ERRORS {json.dumps(errs)[:400]}")
    else:
        got = [i["title"] for i in node["menu"]["items"]]
        print(f"{handle}: OK -> {got}")


upsert("main-menu", "Main menu", MAIN_ITEMS)
upsert("footer", "Footer menu", FOOTER_ITEMS)
