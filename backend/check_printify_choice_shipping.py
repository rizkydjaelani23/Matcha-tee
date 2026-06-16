"""Check Printify Choice and Monster Digital full shipping profiles."""
import httpx, os, sys
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

PTOKEN = os.environ["PRINTIFY_TOKEN"]
PAPI = "https://api.printify.com/v1"
PH = {"Authorization": f"Bearer {PTOKEN}"}
BLUEPRINT_ID = 706

for pid, name in [(99, "Printify Choice"), (29, "Monster Digital")]:
    print(f"\n{'='*50}")
    print(f"{name} (Provider {pid}) — all shipping profiles:")
    rs = httpx.get(f"{PAPI}/catalog/blueprints/{BLUEPRINT_ID}/print_providers/{pid}/shipping.json",
                   headers=PH, timeout=20)
    for profile in rs.json().get("profiles", []):
        countries = profile.get("countries", [])
        first = profile.get("first_item", {})
        additional = profile.get("additional_items", {})
        cost = first.get("cost", 0) / 100
        curr = first.get("currency", "")
        add_cost = additional.get("cost", 0) / 100
        # Show if GB is in this profile
        has_gb = "GB" in countries
        flag = " ← UK" if has_gb else ""
        country_str = ", ".join(countries[:6])
        if len(countries) > 6:
            country_str += f" (+{len(countries)-6} more)"
        print(f"  [{cost:.2f} {curr} / +{add_cost:.2f}]{flag}  {country_str}")
