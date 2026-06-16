"""
Delete old broken menus and wire the correct ones into the theme.
Our correct menus already exist as main-menu-1 and footer-1.
"""
import os, sys, json, time
import httpx
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

STORE    = os.environ["SHOPIFY_STORE"]
TOKEN    = os.environ["SHOPIFY_TOKEN"]
H        = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}
RH       = {"X-Shopify-Access-Token": TOKEN}
GQL      = f"https://{STORE}/admin/api/2025-01/graphql.json"
API      = f"https://{STORE}/admin/api/2025-01"
THEME_ID = 143507587185


def gql(query, variables=None):
    r = httpx.post(GQL, headers=H, json={"query": query, "variables": variables or {}}, timeout=30)
    return r.json()


# ── 1. Fetch all menus ────────────────────────────────────────────────────────
LIST_Q = "{ menus(first:20){ edges{ node{ id handle title } } } }"
menus = {e["node"]["handle"]: e["node"] for e in gql(LIST_Q)["data"]["menus"]["edges"]}

print("Current menus:")
for h, m in menus.items():
    print(f"  {h} — {m['title']}  id={m['id']}")

# ── 2. Delete old broken menus ────────────────────────────────────────────────
DELETE_Q = """mutation menuDelete($id: ID!) {
  menuDelete(id: $id) { deletedMenuId userErrors { message } }
}"""

to_delete = ["main-menu", "footer"]
for handle in to_delete:
    if handle in menus:
        r = gql(DELETE_Q, {"id": menus[handle]["id"]})
        errs = r.get("data", {}).get("menuDelete", {}).get("userErrors", [])
        print(f"Deleted '{handle}': {'OK' if not errs else errs}")
        time.sleep(0.4)

# ── 3. Rename main-menu-1 → main-menu, footer-1 → footer via update ──────────
UPDATE_Q = """mutation menuUpdate($id: ID!, $title: String!, $handle: String!, $items: [MenuItemUpdateInput!]!) {
  menuUpdate(id: $id, title: $title, handle: $handle, items: $items) {
    menu { id handle title items { id title url } }
    userErrors { field message }
  }
}"""

# Fetch full items for main-menu-1 and footer-1
DETAIL_Q = """{ menus(first:20){ edges{ node{
  id handle title
  items { id title url type items { id title url type } }
} } } }"""

time.sleep(0.5)
menus_detail = {e["node"]["handle"]: e["node"]
                for e in gql(DETAIL_Q)["data"]["menus"]["edges"]}

def items_to_update_input(items):
    result = []
    for item in items:
        entry = {"id": item["id"], "title": item["title"], "url": item["url"], "type": item["type"]}
        if item.get("items"):
            entry["items"] = [{"id": s["id"], "title": s["title"], "url": s["url"], "type": s["type"]}
                              for s in item["items"]]
        result.append(entry)
    return result


renames = [("main-menu-1", "main-menu", "Main Menu"),
           ("footer-1",    "footer",    "Footer")]

for old_handle, new_handle, title in renames:
    if old_handle not in menus_detail:
        print(f"'{old_handle}' not found — skipping")
        continue
    node = menus_detail[old_handle]
    update_items = items_to_update_input(node["items"])
    r = gql(UPDATE_Q, {
        "id":     node["id"],
        "title":  title,
        "handle": new_handle,
        "items":  update_items,
    })
    errs = r.get("data", {}).get("menuUpdate", {}).get("userErrors", [])
    menu = r.get("data", {}).get("menuUpdate", {}).get("menu", {})
    print(f"Renamed '{old_handle}' → '{new_handle}': {'OK handle='+menu.get('handle','?') if not errs else errs}")
    time.sleep(0.4)

# ── 4. Update theme header/footer to reference correct menu handles ────────────
print("\nFetching theme settings_data.json...")
r = httpx.get(f"{API}/themes/{THEME_ID}/assets.json", headers=RH,
              params={"asset[key]": "config/settings_data.json"}, timeout=15)
settings = json.loads(r.json()["asset"]["value"])

changed = False
sections = settings.get("current", {}).get("sections", {})

for key, sec in sections.items():
    s = sec.get("settings", {})
    # Fix any section referencing old or wrong menu handles
    for field in ("menu", "main_menu", "navigation", "header_menu"):
        if field in s and s[field] in ("main-menu-1", "main-menu"):
            s[field] = "main-menu"
            changed = True
            print(f"  Set {key}.settings.{field} = main-menu")
    for field in ("footer_menu", "footer_navigation"):
        if field in s and s[field] in ("footer-1", "footer"):
            s[field] = "footer"
            changed = True
            print(f"  Set {key}.settings.{field} = footer")

# Horizon stores header menu reference in header section blocks
# Also check blocks inside sections
for key, sec in sections.items():
    for bkey, block in sec.get("blocks", {}).items():
        bs = block.get("settings", {})
        for field in ("menu", "navigation"):
            if field in bs:
                print(f"  Found block menu ref: {key}.blocks.{bkey}.{field} = {bs[field]}")

if changed:
    print("\nPushing updated settings_data.json...")
    r2 = httpx.put(
        f"{API}/themes/{THEME_ID}/assets.json",
        headers=H,
        json={"asset": {"key": "config/settings_data.json",
                        "value": json.dumps(settings, ensure_ascii=False)}},
        timeout=30,
    )
    print(f"  PUT settings_data.json: {r2.status_code}")
else:
    print("  No menu references found in theme settings — Horizon auto-picks by handle name.")
    print("  Menus with correct handles (main-menu, footer) will be used automatically.")

print("\nDone. Verify at: https://matcha-tees.myshopify.com")
