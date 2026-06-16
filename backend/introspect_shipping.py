import os, json, httpx
from dotenv import load_dotenv
load_dotenv()
STORE = os.environ["SHOPIFY_STORE"]
TOKEN = os.environ["SHOPIFY_TOKEN"]
H = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}
GQL = f"https://{STORE}/admin/api/2025-01/graphql.json"

q = """
{
  zi: __type(name: "DeliveryLocationGroupZoneInput") {
    inputFields {
      name
      type { name kind ofType { name kind ofType { name } } }
    }
  }
  dc: __type(name: "DeliveryCountryInput") {
    inputFields { name type { name kind } }
  }
}
"""
d = httpx.post(GQL, headers=H, json={"query": q}, timeout=15).json()

print("=== DeliveryLocationGroupZoneInput ===")
for f in d["data"]["zi"]["inputFields"]:
    t = f["type"]
    ot = t.get("ofType") or {}
    oot = ot.get("ofType") or {}
    type_str = t["name"] or f"{t['kind']}({ot.get('name') or oot.get('name', '')})"
    print(f"  {f['name']}: {type_str}")

print("\n=== DeliveryCountryInput ===")
for f in d["data"]["dc"]["inputFields"]:
    print(f"  {f['name']}: {f['type']['name']} ({f['type']['kind']})")
