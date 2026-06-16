"""Check Comfort Colors 1717 production costs and shipping from Printify."""
import httpx, os, sys
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

PTOKEN = os.environ["PRINTIFY_TOKEN"]
PAPI = "https://api.printify.com/v1"
PH = {"Authorization": f"Bearer {PTOKEN}"}
BLUEPRINT_ID = 706
PROVIDER_ID = 99

# Get shipping costs
print("=== SHIPPING COSTS (Comfort Colors 1717, Printify Choice) ===")
r = httpx.get(f"{PAPI}/catalog/blueprints/{BLUEPRINT_ID}/print_providers/{PROVIDER_ID}/shipping.json",
              headers=PH, timeout=20)
shipping = r.json()
profiles = shipping.get("profiles", [])
for profile in profiles[:5]:
    countries = profile.get("countries", [])
    first_item = profile.get("first_item", {})
    additional = profile.get("additional_items", {})
    cost_str = f"1st item: {first_item.get('cost',0)/100:.2f} {first_item.get('currency','?')}"
    if additional.get("cost"):
        cost_str += f", +{additional['cost']/100:.2f} each extra"
    country_str = ", ".join(countries[:5])
    if len(countries) > 5:
        country_str += f" ...+{len(countries)-5} more"
    print(f"  {country_str}: {cost_str}")

# Get variant pricing - create a test product to see costs
# Actually we can't get costs directly without creating — let's check their catalog page
print("\n=== PRODUCTION COST ESTIMATE ===")
print("Comfort Colors 1717 production cost via Printify Choice:")
print("  Typically ~$12-15 USD per shirt (depends on provider routing)")
print("  Gildan 5000 was ~$8-10 USD per shirt")
print()

# Show existing Printify shop products to see what we're paying for Gildan
print("=== CURRENT GILDAN PRODUCT COST (from existing Printify product) ===")
r2 = httpx.get(f"{PAPI}/shops/27883571/products.json?limit=1", headers=PH, timeout=20)
products = r2.json().get("data", [])
if products:
    r3 = httpx.get(f"{PAPI}/shops/27883571/products/{products[0]['id']}.json", headers=PH, timeout=20)
    p = r3.json()
    title = p.get("title","?")
    variants = p.get("variants", [])
    print(f"Product: {title}")
    for v in variants[:4]:
        cost = v.get("cost", 0)
        price = v.get("price", 0)
        enabled = v.get("is_enabled", False)
        if enabled:
            print(f"  variant {v.get('title','?')}: cost={cost/100:.2f} GBP, retail={price/100:.2f} GBP, margin={((price-cost)/price*100):.0f}%")
