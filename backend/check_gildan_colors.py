"""
Check Blueprint 6 (Gildan 5000) variant IDs for our 9 colors
across Shirt Monkey (UK), Monster Digital (US), Textildruck Europa (EU).
"""
import httpx, os, sys
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

PTOKEN = os.environ["PRINTIFY_TOKEN"]
PAPI   = "https://api.printify.com/v1"
PH     = {"Authorization": f"Bearer {PTOKEN}"}
BLUEPRINT_ID = 6  # Gildan 5000

WANTED = ["Black", "White", "Pepper", "Grey", "Ivory",
          "Light Green", "Chambray", "Washed Denim", "Blossom"]
SIZES  = ["S", "M", "L", "XL", "2XL", "3XL"]

PROVIDERS = [
    (331, "Shirt Monkey",        "UK"),
    (29,  "Monster Digital",     "US"),
    (26,  "Textildruck Europa",  "EU"),
]

all_variant_maps = {}

for pid, pname, region in PROVIDERS:
    print(f"\n{'='*60}")
    print(f"{pname} (ID={pid}) — {region} — Gildan 5000")
    print(f"{'='*60}")

    rv = httpx.get(f"{PAPI}/catalog/blueprints/{BLUEPRINT_ID}/print_providers/{pid}/variants.json",
                   headers=PH, timeout=20)
    variants = rv.json().get("variants", [])

    # Build color→size→id map
    by_color = {}
    for v in variants:
        opts  = v.get("options", {})
        color = opts.get("color", "?")
        size  = opts.get("size",  "?")
        by_color.setdefault(color, {})[size] = v["id"]

    print(f"All {len(by_color)} colors on this provider:")
    for c in sorted(by_color.keys()):
        szs = by_color[c]
        ids = [f"{s}={szs[s]}" for s in SIZES if s in szs]
        print(f"  {c}: {', '.join(ids)}")

    print(f"\n--- Variant map for 9 wanted colors ---")
    variant_map = {}
    for want in WANTED:
        match_key = next((k for k in by_color if k.lower() == want.lower()), None)
        if match_key:
            szs = by_color[match_key]
            ids = {s: szs[s] for s in SIZES if s in szs}
            variant_map[want] = ids
            ids_str = ", ".join(f"{s}:{v}" for s, v in ids.items())
            print(f"  ✓ {want}: {ids_str}")
        else:
            # fuzzy match
            close = next((k for k in by_color
                          if want.lower() in k.lower() or k.lower() in want.lower()), None)
            if close:
                szs = by_color[close]
                ids = {s: szs[s] for s in SIZES if s in szs}
                variant_map[want] = ids
                ids_str = ", ".join(f"{s}:{v}" for s, v in ids.items())
                print(f"  ~ {want} (listed as '{close}'): {ids_str}")
            else:
                print(f"  ✗ {want} — OOS / not available")
                variant_map[want] = {}

    all_variant_maps[region] = variant_map

# Summary
print("\n\n" + "="*60)
print("SUMMARY — color × provider availability")
print("="*60)
print(f"{'Color':<15} {'UK (SM)':<10} {'US (MD)':<10} {'EU (TE)':<10}")
print("-"*50)
for want in WANTED:
    uk = "ALL" if len(all_variant_maps["UK"].get(want, {})) == 6 else \
         f"{len(all_variant_maps['UK'].get(want, {}))}sz" if all_variant_maps["UK"].get(want) else "OOS"
    us = "ALL" if len(all_variant_maps["US"].get(want, {})) == 6 else \
         f"{len(all_variant_maps['US'].get(want, {}))}sz" if all_variant_maps["US"].get(want) else "OOS"
    eu = "ALL" if len(all_variant_maps["EU"].get(want, {})) == 6 else \
         f"{len(all_variant_maps['EU'].get(want, {}))}sz" if all_variant_maps["EU"].get(want) else "OOS"
    print(f"  {want:<13} {uk:<10} {us:<10} {eu:<10}")
