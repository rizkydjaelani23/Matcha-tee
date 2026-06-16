"""Deep check Shirt Monkey (Provider 331) — all raw variant data."""
import httpx, os, sys, json
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

PTOKEN = os.environ["PRINTIFY_TOKEN"]
PAPI = "https://api.printify.com/v1"
PH = {"Authorization": f"Bearer {PTOKEN}"}
BLUEPRINT_ID = 706
PROVIDER_ID = 331

r = httpx.get(f"{PAPI}/catalog/blueprints/{BLUEPRINT_ID}/print_providers/{PROVIDER_ID}/variants.json",
              headers=PH, timeout=20)
data = r.json()

# Print full raw response to see everything
print(f"Status: {r.status_code}")
print(f"Top-level keys: {list(data.keys()) if isinstance(data, dict) else 'list'}")
variants = data.get("variants", data) if isinstance(data, dict) else data
print(f"Total variants: {len(variants)}")
print()

# Print ALL raw variant data
for v in variants:
    print(json.dumps(v, indent=2))
    print()
