"""
Get variant IDs for 9 colors across all 6 provider/blueprint combos.
Output: Python dict ready to paste into migrate_full.py
"""
import httpx, os, sys, json
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

PTOKEN = os.environ["PRINTIFY_TOKEN"]
PAPI   = "https://api.printify.com/v1"
PH     = {"Authorization": f"Bearer {PTOKEN}"}

WANTED = ["Black", "White", "Pepper", "Grey", "Ivory",
          "Light Green", "Chambray", "Washed Denim", "Blossom"]
SIZES  = ["S", "M", "L", "XL", "2XL", "3XL"]

COMBOS = [
    (331, 706, "UK_CC",  "Shirt Monkey",        "UK Premium CC1717"),
    (331, 6,   "UK_GD",  "Shirt Monkey",        "UK Regular Gildan"),
    (29,  706, "US_CC",  "Monster Digital",     "US Premium CC1717"),
    (29,  6,   "US_GD",  "Monster Digital",     "US Regular Gildan"),
    (99,  706, "EU_CC",  "Printify Choice",     "EU Premium CC1717"),
    (26,  6,   "EU_GD",  "Textildruck Europa",  "EU Regular Gildan"),
]

all_maps = {}

for pid, bid, key, pname, label in COMBOS:
    print(f"\n{'='*55}")
    print(f"{label}  (provider={pid}, blueprint={bid})")
    print(f"{'='*55}")

    rv = httpx.get(
        f"{PAPI}/catalog/blueprints/{bid}/print_providers/{pid}/variants.json",
        headers=PH, timeout=20)
    variants = rv.json().get("variants", [])

    by_color = {}
    for v in variants:
        opts  = v.get("options", {})
        color = opts.get("color", "?")
        size  = opts.get("size",  "?")
        by_color.setdefault(color, {})[size] = v["id"]

    variant_map = {}
    for want in WANTED:
        match_key = next((k for k in by_color if k.lower() == want.lower()), None)
        if match_key:
            szs = by_color[match_key]
            ids = {s: szs[s] for s in SIZES if s in szs}
            variant_map[want] = ids
            ids_str = " ".join(f"{s}:{v}" for s, v in ids.items())
            print(f"  ✓ {want:<14} {ids_str}")
        else:
            variant_map[want] = {}
            print(f"  ✗ {want:<14} OOS")

    all_maps[key] = variant_map

# Output as Python dict
print("\n\n" + "="*55)
print("VARIANT_MAPS = " + json.dumps(all_maps, indent=4))
