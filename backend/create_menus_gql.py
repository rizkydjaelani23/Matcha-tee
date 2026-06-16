"""Create navigation menus via Shopify GraphQL Admin API."""
import os, sys, time
import httpx
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

STORE = os.environ["SHOPIFY_STORE"]
TOKEN = os.environ["SHOPIFY_TOKEN"]
GQL   = f"https://{STORE}/admin/api/2025-01/graphql.json"
H     = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}


def gql(query, variables=None):
    r = httpx.post(GQL, headers=H, json={"query": query, "variables": variables or {}}, timeout=30)
    return r.status_code, r.json()


# ── delete existing menus by handle ──────────────────────────────────────────

DELETE_QUERY = """
mutation menuDelete($id: ID!) {
  menuDelete(id: $id) {
    deletedMenuId
    userErrors { field message }
  }
}
"""

LIST_QUERY = """
{
  menus(first: 20) {
    edges {
      node { id handle title }
    }
  }
}
"""

CREATE_QUERY = """
mutation menuCreate($title: String!, $handle: String!, $items: [MenuItemCreateInput!]!) {
  menuCreate(title: $title, handle: $handle, items: $items) {
    menu {
      id
      handle
      title
      items { id title url }
    }
    userErrors { field message }
  }
}
"""


def delete_menu_by_handle(handle):
    status, data = gql(LIST_QUERY)
    if status != 200:
        return
    for edge in data.get("data", {}).get("menus", {}).get("edges", []):
        node = edge["node"]
        if node["handle"] == handle:
            gql(DELETE_QUERY, {"id": node["id"]})
            print(f"  Deleted existing '{handle}' (id {node['id']})")
            time.sleep(0.3)


def create_menu(title, handle, items):
    delete_menu_by_handle(handle)
    time.sleep(0.3)
    status, data = gql(CREATE_QUERY, {"title": title, "handle": handle, "items": items})
    print(f"  menuCreate '{handle}': HTTP {status}")
    if status != 200:
        print(f"    {data}")
        return False
    errors = data.get("data", {}).get("menuCreate", {}).get("userErrors", [])
    if errors:
        print(f"    userErrors: {errors}")
        return False
    menu = data.get("data", {}).get("menuCreate", {}).get("menu", {})
    print(f"    Created: {menu.get('id')}  items: {len(menu.get('items', []))}")
    return True


# ── menu definitions ──────────────────────────────────────────────────────────

BASE = f"https://{STORE}"

def item(title, path, children=None):
    d = {"title": title, "url": f"{BASE}{path}", "type": "HTTP"}
    if children:
        d["items"] = children
    return d

header_items = [
    item("Shop All", "/collections/all", children=[
        item("T-Shirts",              "/collections/t-shirts"),
        item("Hoodies & Sweatshirts", "/collections/hoodies-sweatshirts"),
    ]),
    item("New Releases", "/collections/new-releases"),
    item("Best Sellers", "/collections/best-sellers"),
]

footer_items = [
    item("FAQ",                "/pages/faq"),
    item("Shipping Policy",    "/pages/shipping-policy"),
    item("Returns & Refunds",  "/pages/return-policy"),
    item("Terms & Conditions", "/pages/terms-and-conditions"),
    item("Privacy Policy",     "/pages/privacy-policy"),
    item("Contact Us",         "/pages/contact"),
    item("Affiliates",         "/pages/affiliates"),
    item("Wholesale",          "/pages/wholesale"),
]


print("Creating main-menu (header)...")
ok1 = create_menu("Main Menu", "main-menu", header_items)

print("\nCreating footer menu...")
ok2 = create_menu("Footer", "footer", footer_items)

print("\n" + ("All menus created." if ok1 and ok2 else "Some menus failed — see above."))
