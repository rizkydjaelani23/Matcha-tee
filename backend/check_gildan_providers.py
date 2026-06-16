"""
Check Blueprint 6 (Gildan 5000) providers:
- Find Textiledruck (EU)
- Find best US domestic provider
- Check Shirt Monkey for Gildan (UK)
"""
import httpx, os, sys
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

PTOKEN = os.environ["PRINTIFY_TOKEN"]
PAPI   = "https://api.printify.com/v1"
PH     = {"Authorization": f"Bearer {PTOKEN}"}
BLUEPRINT_ID = 6  # Gildan 5000

r = httpx.get(f"{PAPI}/catalog/blueprints/{BLUEPRINT_ID}/print_providers.json", headers=PH, timeout=20)
providers = r.json()

print(f"All providers for Blueprint 6 (Gildan 5000):\n")

for p in providers:
    pid   = p["id"]
    pname = p["title"]

    rs = httpx.get(f"{PAPI}/catalog/blueprints/{BLUEPRINT_ID}/print_providers/{pid}/shipping.json",
                   headers=PH, timeout=20)
    profiles = rs.json().get("profiles", [])

    gb_cost, us_cost, eu_cost = None, None, None
    gb_curr = us_curr = eu_curr = ""
    for profile in profiles:
        countries = profile.get("countries", [])
        first = profile.get("first_item", {})
        cost = first.get("cost", 0) / 100
        curr = first.get("currency", "")
        if "GB" in countries:
            gb_cost, gb_curr = cost, curr
        if "US" in countries:
            us_cost, us_curr = cost, curr
        if "DE" in countries or "FR" in countries:
            eu_cost, eu_curr = cost, curr

    flags = []
    if gb_cost is not None: flags.append(f"🇬🇧 GB={gb_cost:.2f}{gb_curr}")
    if us_cost is not None: flags.append(f"🇺🇸 US={us_cost:.2f}{us_curr}")
    if eu_cost is not None: flags.append(f"🇪🇺 EU={eu_cost:.2f}{eu_curr}")

    name_lower = pname.lower()
    highlight = " ◄◄◄" if ("textile" in name_lower or "druck" in name_lower or
                             "shirt monkey" in name_lower or pid == 331) else ""
    print(f"  ID={pid:4d}  {pname:<30}  {' | '.join(flags)}{highlight}")

print("\n--- Looking specifically for Textiledruck ---")
for p in providers:
    if "textile" in p["title"].lower() or "druck" in p["title"].lower():
        print(f"  FOUND: {p['title']} (ID={p['id']})")
        # Get variants to see colors
        rv = httpx.get(f"{PAPI}/catalog/blueprints/{BLUEPRINT_ID}/print_providers/{p['id']}/variants.json",
                       headers=PH, timeout=20)
        variants = rv.json().get("variants", [])
        colors = {}
        for v in variants:
            opts = v.get("options", {})
            color = opts.get("color", "?")
            size  = opts.get("size", "?")
            colors.setdefault(color, []).append(size)
        print(f"  Colors ({len(colors)}): {', '.join(sorted(colors.keys()))}")
