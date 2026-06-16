"""Check Monster Digital (Provider 29) CC1717 full color and variant list."""
import httpx, os, sys
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

PTOKEN = os.environ["PRINTIFY_TOKEN"]
PAPI = "https://api.printify.com/v1"
PH = {"Authorization": f"Bearer {PTOKEN}"}
BLUEPRINT_ID = 706
PROVIDER_ID = 29  # Monster Digital

r = httpx.get(f"{PAPI}/catalog/blueprints/{BLUEPRINT_ID}/print_providers/{PROVIDER_ID}/variants.json",
              headers=PH, timeout=20)
variants = r.json().get("variants", [])
print(f"Total variants: {len(variants)}\n")

colors = {}
for v in variants:
    opts = v.get("options", {})
    color = opts.get("color", "?")
    size = opts.get("size", "?")
    colors.setdefault(color, {})[size] = v["id"]

print(f"{len(colors)} colors available:\n")
for color in sorted(colors.keys()):
    sizes = colors[color]
    ids = [f"{s}={sizes[s]}" for s in ["S","M","L","XL","2XL","3XL"] if s in sizes]
    print(f"  {color}: {', '.join(ids)}")

# Check which of our 15 colors are available
WANTED = ["White","Black","Pepper","Grey","Navy","Red","Chili","Espresso",
          "Ivory","Mustard","Butter","Bay","Blossom","Neon Pink","Light Green"]
print(f"\n--- Our 15 color check ---")
for c in WANTED:
    match = colors.get(c)
    if match:
        print(f"  ✓ {c}")
    else:
        # Try case-insensitive
        found = next((k for k in colors if k.lower() == c.lower()), None)
        if found:
            print(f"  ✓ {c} (as '{found}')")
        else:
            print(f"  ✗ {c} — NOT AVAILABLE")

# Check shipping
print("\n--- Shipping costs ---")
rs = httpx.get(f"{PAPI}/catalog/blueprints/{BLUEPRINT_ID}/print_providers/{PROVIDER_ID}/shipping.json",
               headers=PH, timeout=20)
for profile in rs.json().get("profiles", [])[:6]:
    countries = profile.get("countries", [])
    first = profile.get("first_item", {})
    print(f"  {', '.join(countries[:3])}{'...' if len(countries)>3 else ''}: "
          f"{first.get('cost',0)/100:.2f} {first.get('currency','?')}")
