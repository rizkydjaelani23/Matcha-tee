"""
Final fix:
1. Update the 'International' zone in the General profile to remove GB from its country list
   (keeps IDR 340000 rate for AE/AT/AU/etc — only affects General profile fallback)
2. Create a new 'United Kingdom' zone at £0.00 free shipping
"""
import os, sys, httpx
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

# ── Step 1: get IDs ───────────────────────────────────────────────────────────
QUERY = """{
  deliveryProfiles(first: 5) {
    edges { node {
      id name default
      profileLocationGroups {
        locationGroup { id }
        locationGroupZones(first: 10) {
          edges { node {
            zone { id name countries { code { countryCode } } }
          } }
        }
      }
    } }
  }
}"""

profiles = gql(QUERY)["data"]["deliveryProfiles"]["edges"]
default_profile = next((e["node"] for e in profiles if e["node"]["default"]), None)
if not default_profile:
    print("No default profile"); sys.exit(1)

lg_id = None
int_zone_id = None
int_countries = []  # all countries currently in that zone

for plg in default_profile["profileLocationGroups"]:
    lg_id = plg["locationGroup"]["id"]
    for ze in plg["locationGroupZones"]["edges"]:
        z = ze["node"]["zone"]
        countries = [c["code"]["countryCode"] for c in z["countries"]]
        if "GB" in countries:
            int_zone_id = z["id"]
            int_countries = countries
            print(f"Found zone '{z['name']}' (id={z['id']}) with GB — will remove GB from it")
            print(f"  Current countries: {countries}")

if not int_zone_id:
    print("GB not found in any General profile zone — nothing to do."); sys.exit(0)

# Countries to KEEP in the International zone (everything except GB)
keep_countries = [c for c in int_countries if c != "GB"]
print(f"\nInternational zone will keep: {keep_countries}")
print("New 'United Kingdom' zone: £0.00 Free Shipping")

# ── Step 2: update zone (remove GB) + create UK zone ─────────────────────────
UPDATE = """mutation upd($id: ID!, $profile: DeliveryProfileInput!) {
  deliveryProfileUpdate(id: $id, profile: $profile) {
    profile { id name }
    userErrors { field message }
  }
}"""

profile_input = {
    "locationGroupsToUpdate": [{
        "id": lg_id,
        "zonesToUpdate": [{
            "id": int_zone_id,
            "countries": [
                {"code": c, "includeAllProvinces": True} for c in keep_countries
            ]
        }],
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

result = gql(UPDATE, {"id": default_profile["id"], "profile": profile_input})
upd = result.get("data", {}).get("deliveryProfileUpdate", {})
errors = upd.get("userErrors", [])

if errors:
    print(f"\nERROR: {errors}")
else:
    print(f"\nOK — '{upd['profile']['name']}' updated.")
    print("  GB removed from International zone (IDR rate preserved for other countries)")
    print("  'United Kingdom' zone created: Free Shipping £0.00")
    print("\nUK customers will now see FREE SHIPPING at checkout.")
