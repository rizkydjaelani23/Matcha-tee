import os, httpx
from dotenv import load_dotenv
load_dotenv()
STORE = os.environ["SHOPIFY_STORE"]
TOKEN = os.environ["SHOPIFY_TOKEN"]
H = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}
GQL = f"https://{STORE}/admin/api/2025-01/graphql.json"

def gql(q, v=None):
    d = httpx.post(GQL, headers=H, json={"query": q, "variables": v or {}}, timeout=15).json()
    if "errors" in d: print("GQL errors:", [e["message"][:80] for e in d["errors"]])
    return d

def obj_fields(name):
    d = gql(f'{{ __type(name: "{name}") {{ fields {{ name type {{ name kind ofType {{ name }} }} }} }} }}')
    return (d.get("data",{}).get("__type") or {}).get("fields") or []

# Check RegionsCondition
fs = obj_fields("RegionsCondition")
print("=== RegionsCondition ===")
for f in fs:
    t = f["type"]; ot = t.get("ofType") or {}
    print(f"  {f['name']}: {t['name'] or t['kind']}({ot.get('name','')})")

# Simple markets query
d = gql("{ markets(first: 10) { edges { node { id name status type currencySettings { baseCurrency { currencyCode } } } } } }")
print("\n=== Existing Markets ===")
for e in (d.get("data",{}).get("markets",{}).get("edges") or []):
    n = e["node"]
    currency = (n.get("currencySettings") or {}).get("baseCurrency",{}).get("currencyCode","?")
    print(f"  {n['name']} type={n['type']} status={n['status']} currency={currency} id={n['id']}")

# Check MarketConditionsRegionsInput sub-types
d2 = gql('{ __type(name: "MarketConditionsRegionsInput") { inputFields { name type { name kind ofType { name kind ofType { name } } } } } }')
fs2 = (d2.get("data",{}).get("__type") or {}).get("inputFields") or []
print("\n=== MarketConditionsRegionsInput fields ===")
for f in fs2:
    t = f["type"]; ot = t.get("ofType") or {}; oot = ot.get("ofType") or {}
    print(f"  {f['name']}: {t['name'] or t['kind']}({ot.get('name') or oot.get('name','')})")
