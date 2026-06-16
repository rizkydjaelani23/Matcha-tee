"""Check all Comfort Colors 1717 variant colors — search for pink and green."""
import httpx, os, sys
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

PTOKEN = os.environ["PRINTIFY_TOKEN"]
PAPI = "https://api.printify.com/v1"
PH = {"Authorization": f"Bearer {PTOKEN}"}
BLUEPRINT_ID = 706
PROVIDER_ID = 99

r = httpx.get(f"{PAPI}/catalog/blueprints/{BLUEPRINT_ID}/print_providers/{PROVIDER_ID}/variants.json",
              headers=PH, timeout=20)
variants = r.json().get("variants", [])

colors = {}
for v in variants:
    opts = v.get("options", {})
    color = opts.get("color", "?")
    size = opts.get("size", "?")
    colors.setdefault(color, {})[size] = v["id"]

print(f"ALL {len(colors)} colors:\n")
for color in sorted(colors.keys()):
    sizes = colors[color]
    ids = [f"{s}={sizes[s]}" for s in ["S","M","L","XL","2XL","3XL"] if s in sizes]
    print(f"  {color}: {', '.join(ids)}")

print("\n--- Pink colours ---")
for color in sorted(colors.keys()):
    if "pink" in color.lower() or "neon" in color.lower() or "flo" in color.lower():
        sizes = colors[color]
        ids = [f"{s}={sizes[s]}" for s in ["S","M","L","XL","2XL","3XL"] if s in sizes]
        print(f"  {color}: {', '.join(ids)}")

print("\n--- Green colours ---")
for color in sorted(colors.keys()):
    if "green" in color.lower() or "moss" in color.lower() or "mint" in color.lower() or "sage" in color.lower():
        sizes = colors[color]
        ids = [f"{s}={sizes[s]}" for s in ["S","M","L","XL","2XL","3XL"] if s in sizes]
        print(f"  {color}: {', '.join(ids)}")
