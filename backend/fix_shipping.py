"""
Fix Shopify shipping:
- Add 'United Kingdom' zone with FREE shipping (£0)
- Delete the 'International' / catch-all zone (£14.14)
UK customers will see 'Free Shipping' at checkout.
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
        for err in d["errors"]:
            print(f"GQL error: {err['message']}")
    return d

QUERY = """{
  deliveryProfiles(first: 10) {
    edges { node {
      id name default
      profileLocationGroups {
        locationGroup { id }
        locationGroupZones(first: 30) {
          edges { node {
            zone {
              id name
              countries { code { countryCode } name }
            }
            methodDefinitions(first: 10) {
              edges { node {
                id name active
                rateProvider {
                  ... on DeliveryRateDefinition {
                    id
                    price { amount currencyCode }
                  }
                }
              } }
            }
          } }
        }
      }
    } }
  }
}"""

profiles_data = gql(QUERY)
if "data" not in profiles_data:
    print("Failed to query profiles:", profiles_data)
    sys.exit(1)

profiles = profiles_data["data"]["deliveryProfiles"]["edges"]
print(f"Found {len(profiles)} delivery profile(s)\n")

default_profile = None
for e in profiles:
    p = e["node"]
    marker = "[DEFAULT]" if p["default"] else "        "
    print(f"{marker} Profile: '{p['name']}' id={p['id']}")
    if p["default"]:
        default_profile = p
    for plg in p["profileLocationGroups"]:
        for ze in plg["locationGroupZones"]["edges"]:
            z = ze["node"]["zone"]
            countries = [c["code"]["countryCode"] for c in z["countries"]]
            print(f"  Zone: '{z['name']}' countries={countries or '(catch-all)'}")
            for me in ze["node"]["methodDefinitions"]["edges"]:
                m = me["node"]
                rp = m.get("rateProvider") or {}
                price = rp.get("price", {}) if isinstance(rp, dict) else {}
                print(f"    Rate: '{m['name']}' {price.get('currencyCode','')} "
                      f"{price.get('amount','?')} active={m['active']}")

if not default_profile:
    print("\nNo default profile found — exiting.")
    sys.exit(1)

# Analyse zones in default profile
lg_id = None
uk_zone_exists = False
zones_to_delete = []

for plg in default_profile["profileLocationGroups"]:
    if not lg_id:
        lg_id = plg["locationGroup"]["id"]
    for ze in plg["locationGroupZones"]["edges"]:
        z = ze["node"]["zone"]
        countries = [c["code"]["countryCode"] for c in z["countries"]]
        name_lower = z["name"].lower()

        if "GB" in countries:
            uk_zone_exists = True
            print(f"\nUK zone already exists: '{z['name']}' — will skip creation")
        elif (not countries
              or any(kw in name_lower for kw in
                     ["international", "rest of world", "worldwide", "everywhere"])):
            zones_to_delete.append(z["id"])
            print(f"\nWill delete zone: '{z['name']}' (international catch-all, £14.14)")

print(f"\n--- PLAN ---")
print(f"Location group: {lg_id}")
print(f"UK zone exists: {uk_zone_exists}")
print(f"Zones to delete: {zones_to_delete}")

if uk_zone_exists and not zones_to_delete:
    print("\nNothing to change — UK free zone exists, no old zones to remove.")
    sys.exit(0)

# Build update input
lg_update = {"id": lg_id}

if not uk_zone_exists:
    lg_update["zonesToCreate"] = [{
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
    print("\nAdding: 'United Kingdom' zone → Free Shipping £0.00")

if zones_to_delete:
    lg_update["zonesToDelete"] = zones_to_delete

UPDATE = """mutation upd($id: ID!, $profile: DeliveryProfileInput!) {
  deliveryProfileUpdate(id: $id, profile: $profile) {
    profile { id name }
    userErrors { field message }
  }
}"""

result = gql(UPDATE, {
    "id": default_profile["id"],
    "profile": {"locationGroupsToUpdate": [lg_update]}
})

upd = result.get("data", {}).get("deliveryProfileUpdate", {})
errors = upd.get("userErrors", [])

if errors:
    print(f"\nERROR: {errors}")
else:
    name = upd.get("profile", {}).get("name", "?")
    print(f"\nOK — '{name}' updated successfully!")
    if not uk_zone_exists:
        print("  + Added: 'United Kingdom' → Free Shipping (£0.00)")
    for zid in zones_to_delete:
        print(f"  - Deleted: zone {zid} (International £14.14)")
    print("\nUK customers will now see FREE SHIPPING at checkout.")
