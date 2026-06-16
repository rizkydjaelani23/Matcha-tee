"""Check all CC1717 providers — UK shipping cost and colour coverage."""
import httpx, os, sys
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

PTOKEN = os.environ["PRINTIFY_TOKEN"]
PAPI = "https://api.printify.com/v1"
PH = {"Authorization": f"Bearer {PTOKEN}"}
BLUEPRINT_ID = 706

WANTED = {"white","black","pepper","grey","navy","red","chili","espresso",
          "ivory","mustard","butter","bay","blossom","neon pink","light green"}

r = httpx.get(f"{PAPI}/catalog/blueprints/{BLUEPRINT_ID}/print_providers.json", headers=PH, timeout=20)
providers = r.json()

print(f"{'Provider':<30} {'UK Ship':>8}  {'Our 15 colours':>14}  Notes")
print("-" * 80)

for p in providers:
    pid   = p["id"]
    pname = p["title"]

    # Get variants
    rv = httpx.get(f"{PAPI}/catalog/blueprints/{BLUEPRINT_ID}/print_providers/{pid}/variants.json",
                   headers=PH, timeout=20)
    variants = rv.json().get("variants", [])
    colors = set()
    for v in variants:
        c = v.get("options", {}).get("color", "")
        if c:
            colors.add(c.lower())

    matched = WANTED & colors
    missing = WANTED - colors

    # Get shipping — find GB cost
    rs = httpx.get(f"{PAPI}/catalog/blueprints/{BLUEPRINT_ID}/print_providers/{pid}/shipping.json",
                   headers=PH, timeout=20)
    uk_cost = "?"
    currency = ""
    for profile in rs.json().get("profiles", []):
        countries = profile.get("countries", [])
        if "GB" in countries:
            first = profile.get("first_item", {})
            uk_cost   = first.get("cost", 0) / 100
            currency  = first.get("currency", "")
            break

    missing_str = ", ".join(sorted(missing)) if missing else "ALL ✓"
    print(f"  {pname:<28} {uk_cost:>5} {currency}  {len(matched):>2}/15 matched")
    if missing:
        print(f"    Missing: {missing_str}")
    print()
