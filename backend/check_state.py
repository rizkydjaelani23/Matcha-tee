import os, sys, json, httpx
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

STORE = os.environ["SHOPIFY_STORE"]
RH = {"X-Shopify-Access-Token": os.environ["SHOPIFY_TOKEN"]}
H  = {"X-Shopify-Access-Token": os.environ["SHOPIFY_TOKEN"], "Content-Type": "application/json"}
API = f"https://{STORE}/admin/api/2025-01"
GQL = f"https://{STORE}/admin/api/2025-01/graphql.json"
THEME_ID = 143507587185

# Collections
cols = httpx.get(f"{API}/custom_collections.json", headers=RH, timeout=15).json()
print("=== CUSTOM COLLECTIONS ===")
for c in cols.get("custom_collections", []):
    print(f"  [{c['id']}] {c['title']} — {c['handle']}")

# Menus via GraphQL
r = httpx.post(GQL, headers=H, json={"query": "{ menus(first:20){ edges{ node{ id handle title items{ title url } } } } }"}, timeout=15)
print("\n=== MENUS (GraphQL) ===")
for edge in r.json().get("data", {}).get("menus", {}).get("edges", []):
    m = edge["node"]
    print(f"  {m['handle']} — {m['title']}")
    for item in m.get("items", []):
        print(f"    - {item['title']} → {item['url']}")

# Theme settings — what menu handles does Horizon reference?
r2 = httpx.get(f"{API}/themes/{THEME_ID}/assets.json", headers=RH,
               params={"asset[key]": "config/settings_data.json"}, timeout=15)
settings = json.loads(r2.json()["asset"]["value"])
sections = settings.get("current", {}).get("sections", {})
print("\n=== THEME HEADER SECTION SETTINGS ===")
for key, sec in sections.items():
    if "header" in key.lower() or "nav" in key.lower() or "footer" in key.lower():
        print(f"  section key: {key}  type: {sec.get('type')}")
        print(f"    settings: {sec.get('settings', {})}")
