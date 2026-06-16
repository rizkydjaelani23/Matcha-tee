"""
Update the content of the default main-menu and footer menus (can't be deleted).
Replaces all items with the correct navigation structure.
"""
import os, sys, json, time
import httpx
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

STORE = os.environ["SHOPIFY_STORE"]
TOKEN = os.environ["SHOPIFY_TOKEN"]
H     = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}
GQL   = f"https://{STORE}/admin/api/2025-01/graphql.json"
BASE  = f"https://{STORE}"

MAIN_MENU_ID = "gid://shopify/Menu/225987166321"
FOOTER_ID    = "gid://shopify/Menu/225987199089"


def gql(query, variables=None):
    r = httpx.post(GQL, headers=H, json={"query": query, "variables": variables or {}}, timeout=30)
    return r.json()


# ── Step 1: get existing item IDs so we can replace them properly ─────────────
DETAIL_Q = """query getMenu($id: ID!) {
  menu(id: $id) {
    id handle title
    items { id title url type
      items { id title url type }
    }
  }
}"""

def get_menu(menu_id):
    r = gql(DETAIL_Q, {"id": menu_id})
    return r["data"]["menu"]

main = get_menu(MAIN_MENU_ID)
foot = get_menu(FOOTER_ID)

print(f"main-menu current items: {[i['title'] for i in main['items']]}")
print(f"footer   current items: {[i['title'] for i in foot['items']]}")

# ── Step 2: delete all existing items from both menus ─────────────────────────
# We achieve this by updating with a fresh items list — Shopify replaces entirely
# We need to delete child items first, but menuUpdate handles it when we replace the list.

# ── Step 3: update menus with correct content ──────────────────────────────────
# MenuItemUpdateInput allows omitting 'id' to create new; we pass no IDs so all old items
# are implicitly removed and new ones created.

UPDATE_Q = """mutation menuUpdate($id: ID!, $title: String!, $handle: String!, $items: [MenuItemUpdateInput!]!) {
  menuUpdate(id: $id, title: $title, handle: $handle, items: $items) {
    menu {
      id handle title
      items { id title url type items { id title url type } }
    }
    userErrors { field message }
  }
}"""

def mk(title, path, children=None):
    d = {"title": title, "url": f"{BASE}{path}", "type": "HTTP"}
    if children:
        d["items"] = children
    return d

new_main_items = [
    mk("Shop All", "/collections/all", children=[
        mk("T-Shirts",              "/collections/t-shirts"),
        mk("Hoodies & Sweatshirts", "/collections/hoodies-sweatshirts"),
    ]),
    mk("New Releases", "/collections/new-releases"),
    mk("Best Sellers", "/collections/best-sellers"),
]

new_footer_items = [
    mk("FAQ",                "/pages/faq"),
    mk("Shipping Policy",    "/pages/shipping-policy"),
    mk("Returns & Refunds",  "/pages/return-policy"),
    mk("Terms & Conditions", "/pages/terms-and-conditions"),
    mk("Privacy Policy",     "/pages/privacy-policy"),
    mk("Contact Us",         "/pages/contact"),
    mk("Affiliates",         "/pages/affiliates"),
    mk("Wholesale",          "/pages/wholesale"),
]

# Update main-menu
r1 = gql(UPDATE_Q, {
    "id": MAIN_MENU_ID, "title": "Main Menu", "handle": "main-menu",
    "items": new_main_items,
})
errs1 = r1.get("data", {}).get("menuUpdate", {}).get("userErrors", [])
menu1 = r1.get("data", {}).get("menuUpdate", {}).get("menu", {})
if errs1:
    print(f"main-menu update errors: {errs1}")
else:
    items_out = [f"{i['title']} ({len(i.get('items',[]))} children)" for i in menu1.get("items", [])]
    print(f"main-menu updated OK — items: {items_out}")

time.sleep(0.4)

# Update footer
r2 = gql(UPDATE_Q, {
    "id": FOOTER_ID, "title": "Footer", "handle": "footer",
    "items": new_footer_items,
})
errs2 = r2.get("data", {}).get("menuUpdate", {}).get("userErrors", [])
menu2 = r2.get("data", {}).get("menuUpdate", {}).get("menu", {})
if errs2:
    print(f"footer update errors: {errs2}")
else:
    items_out = [i['title'] for i in menu2.get("items", [])]
    print(f"footer updated OK — items: {items_out}")

time.sleep(0.4)

# ── Step 4: delete the now-redundant main-menu-1 and footer-1 ──────────────────
DELETE_Q = """mutation menuDelete($id: ID!) {
  menuDelete(id: $id) { deletedMenuId userErrors { message } }
}"""

LIST_Q = "{ menus(first:20){ edges{ node{ id handle title } } } }"
all_menus = {e["node"]["handle"]: e["node"] for e in gql(LIST_Q)["data"]["menus"]["edges"]}

for handle in ("main-menu-1", "footer-1"):
    if handle in all_menus:
        r = gql(DELETE_Q, {"id": all_menus[handle]["id"]})
        errs = r.get("data", {}).get("menuDelete", {}).get("userErrors", [])
        print(f"Deleted '{handle}': {'OK' if not errs else errs}")
        time.sleep(0.3)

# ── Step 5: verify final state ─────────────────────────────────────────────────
time.sleep(0.3)
final = {e["node"]["handle"]: e["node"] for e in gql(LIST_Q)["data"]["menus"]["edges"]}
print("\nFinal menus:")
for h, m in final.items():
    print(f"  {h} — {m['title']}")

print("\nDone! Menus are live at https://thematchatee.com")
