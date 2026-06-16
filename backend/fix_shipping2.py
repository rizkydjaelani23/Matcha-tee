"""
Targeted fix:
- General profile has 'International' zone with GB lumped in at IDR 340000 (= £14.14)
- Delete that zone entirely (Printify profiles already cover those countries with real rates)
- Create a clean 'United Kingdom' zone at £0.00 free shipping
"""
import os, sys, json, httpx
from dotenv import load_dotenv
sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
STORE = os.environ["SHOPIFY_STORE"]
TOKEN = os.environ["SHOPIFY_TOKEN"]
H = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}
GQL = f"https://{STORE}/admin/api/2025-01/graphql.json"

def gql(q, v=None):
    r = httpx.post(GQL, headers=H, json={"query": q, "variables": v or {}}, timeout=30)
    d = r.json()
    if "errors" in d:
        print("GQL errors:", d["errors"])
    return d

# ── Step 1: query default profile with zone IDs ───────────────────────────────
QUERY = """{
  deliveryProfiles(first: 5) {
    edges { node {
      id name default
      profileLocationGroups {
        locationGroup { id }
        locationGroupZones(first: 10) {
          edges { node {
            zone { id name countries { code { countryCode } } }
            methodDefinitions(first: 5) {
              edges { node { id name rateProvider {
                ... on DeliveryRateDefinition { id price { amount currencyCode } }
              } } }
            }
          } }
        }
      }
    } }
  }
}"""

data = gql(QUERY)["data"]["deliveryProfiles"]["edges"]
default_profile = next((e["node"] for e in data if e["node"]["default"]), None)

if not default_profile:
    print("No default profile found"); sys.exit(1)

print(f"Default profile: '{default_profile['name']}' id={default_profile['id']}\n")

# Find location group and the zone that contains GB
lg_id = None
int_zone_id = None

for plg in default_profile["profileLocationGroups"]:
    lg_id = plg["locationGroup"]["id"]
    for ze in plg["locationGroupZones"]["edges"]:
        z = ze["node"]["zone"]
        countries = [c["code"]["countryCode"] for c in z["countries"]]
        methods = ze["node"]["methodDefinitions"]["edges"]
        rates_str = ", ".join(
            f"{m['node']['rateProvider'].get('price',{}).get('currencyCode','?')} "
            f"{m['node']['rateProvider'].get('price',{}).get('amount','?')}"
            for m in methods if isinstance(m['node']['rateProvider'], dict)
        )
        print(f"  Zone: '{z['name']}' id={z['id']}")
        print(f"    countries: {countries}")
        print(f"    rates: {rates_str}")
        if "GB" in countries:
            int_zone_id = z["id"]
            print(f"    ^ FOUND GB HERE — will delete this zone")

if not lg_id:
    print("No location group found"); sys.exit(1)

if not int_zone_id:
    print("\nGB not found in any General profile zone. Nothing to fix.")
    sys.exit(0)

# ── Step 2: delete old zone + create UK free zone ─────────────────────────────
UPDATE = """mutation upd($id: ID!, $profile: DeliveryProfileInput!) {
  deliveryProfileUpdate(id: $id, profile: $profile) {
    profile { id name }
    userErrors { field message }
  }
}"""

profile_input = {
    "locationGroupsToUpdate": [{
        "id": lg_id,
        "zonesToDelete": [int_zone_id],
        "zonesToCreate": [{
            "name": "United Kingdom",
            "countries": [{"code": "GB", "includeAllProvinces": True}],
            "methodDefinitionsToCreate": [{
                "name": "Free Shipping",
                "active": True,
                "rateDefinition": {
                    "price": {"amount": "0.00", "currencyCode": "GBP"}
                }
            }]
        }]
    }]
}

print(f"\nDeleting zone {int_zone_id} (International with £14.14)...")
print("Creating 'United Kingdom' zone at £0.00...")

result = gql(UPDATE, {"id": default_profile["id"], "profile": profile_input})
upd = result.get("data", {}).get("deliveryProfileUpdate", {})
errors = upd.get("userErrors", [])

if errors:
    print(f"\nERROR: {errors}")
else:
    print(f"\nOK — '{upd['profile']['name']}' updated.")
    print("UK customers now see: FREE SHIPPING")
    print("Old 'International £14.14' rate: GONE")
