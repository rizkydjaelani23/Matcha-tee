"""Find UK-based CC1717 providers — identified by having a specific GB shipping rate."""
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

uk_providers = []
all_results = []

for p in providers:
    pid   = p["id"]
    pname = p["title"]

    # Check shipping for GB-specific rate
    rs = httpx.get(f"{PAPI}/catalog/blueprints/{BLUEPRINT_ID}/print_providers/{pid}/shipping.json",
                   headers=PH, timeout=20)
    profiles = rs.json().get("profiles", [])

    gb_cost = None
    gb_currency = ""
    row_cost = None
    row_currency = ""
    for profile in profiles:
        countries = profile.get("countries", [])
        first = profile.get("first_item", {})
        cost = first.get("cost", 0) / 100
        curr = first.get("currency", "")
        if "GB" in countries:
            gb_cost = cost
            gb_currency = curr
        if "REST_OF_THE_WORLD" in countries:
            row_cost = cost
            row_currency = curr

    is_uk = gb_cost is not None
    ship_str = f"GB={gb_cost} {gb_currency}" if is_uk else f"REST={row_cost} {row_currency}"

    # Get colour coverage
    rv = httpx.get(f"{PAPI}/catalog/blueprints/{BLUEPRINT_ID}/print_providers/{pid}/variants.json",
                   headers=PH, timeout=20)
    variants = rv.json().get("variants", [])
    colors = {v.get("options", {}).get("color", "").lower() for v in variants if v.get("options", {}).get("color")}
    matched = len(WANTED & colors)
    missing = sorted(WANTED - colors)

    tag = "🇬🇧 UK" if is_uk else "🌍 Non-UK"
    print(f"{tag}  {pname:<28}  {ship_str:<22}  {matched}/15 colours")
    if missing:
        print(f"       Missing: {', '.join(missing)}")
    print()

    if is_uk:
        uk_providers.append((pname, pid, gb_cost, gb_currency, matched, missing))

print("\n" + "="*60)
print("UK-BASED PROVIDERS SUMMARY:")
if uk_providers:
    for name, pid, cost, curr, matched, missing in uk_providers:
        print(f"  {name} (ID={pid}): GB shipping={cost} {curr}, {matched}/15 colours")
        if missing:
            print(f"    Missing: {', '.join(missing)}")
else:
    print("  No providers with GB-specific shipping found for CC1717")
