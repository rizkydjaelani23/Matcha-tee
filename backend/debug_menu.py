import os, httpx, json, sys
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

STORE = os.environ["SHOPIFY_STORE"]
H = {"X-Shopify-Access-Token": os.environ["SHOPIFY_TOKEN"], "Content-Type": "application/json"}
GQL = f"https://{STORE}/admin/api/2025-01/graphql.json"

BASE = f"https://{STORE}"

# Test with absolute URL
q = """
mutation menuCreate($title: String!, $handle: String!, $items: [MenuItemCreateInput!]!) {
  menuCreate(title: $title, handle: $handle, items: $items) {
    menu { id handle items { id title url } }
    userErrors { field message }
  }
}
"""

vars = {
    "title": "Test Menu",
    "handle": "test-debug-2",
    "items": [
        {"title": "T-Shirts", "url": f"{BASE}/collections/t-shirts"},
        {"title": "Contact",  "url": f"{BASE}/pages/contact"},
    ]
}

r = httpx.post(GQL, headers=H, json={"query": q, "variables": vars}, timeout=15)
print(json.dumps(r.json(), indent=2))

# Clean up test menu
cleanup = """
mutation { menuDelete(id: "%s") { deletedMenuId userErrors { message } } }
"""
data = r.json().get("data", {}).get("menuCreate", {}).get("menu")
if data and data.get("id"):
    httpx.post(GQL, headers=H, json={"query": cleanup % data["id"]}, timeout=15)
    print("Test menu cleaned up")
