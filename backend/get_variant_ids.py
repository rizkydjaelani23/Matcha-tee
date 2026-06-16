"""
Get exact Printify variant IDs for the blueprint+provider we'll use for sync.
Title format: "Color / Size"  (e.g. "White / S")
"""
import os, sys, httpx, json
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
PRINTIFY_TOKEN = os.environ["PRINTIFY_TOKEN"]
PH = {"Authorization": f"Bearer {PRINTIFY_TOKEN}"}
PAPI = "https://api.printify.com/v1"

# Colors on Shopify (option2) -> what Printify calls them
SHOPIFY_COLORS = ["White","Black","Navy","Sport Grey","Daisy","Light Blue"]
# Sizes on Shopify (option1)
SHOPIFY_SIZES  = ["XS","S","M","L","XL","2XL","3XL"]

def check_provider(blueprint_id, provider_id, label=""):
    print(f"\n{'='*60}")
    print(f"Blueprint {blueprint_id} + Provider {provider_id} {label}")
    r = httpx.get(
        f"{PAPI}/catalog/blueprints/{blueprint_id}/print_providers/{provider_id}/variants.json",
        headers=PH, timeout=20
    )
    if r.status_code != 200:
        print(f"  Error {r.status_code}")
        return {}

    variants = r.json().get("variants", [])
    print(f"  Total variants: {len(variants)}")

    # Build lookup: (color, size) -> variant_id
    lookup = {}
    for v in variants:
        title = v.get("title","")
        parts = [p.strip() for p in title.split(" / ")]
        if len(parts) == 2:
            color, size = parts[0], parts[1]
            lookup[(color, size)] = v["id"]

    # Find all unique colors and sizes
    all_colors = sorted(set(k[0] for k in lookup))
    all_sizes  = sorted(set(k[1] for k in lookup),
                        key=lambda s: ["XS","S","M","L","XL","2XL","3XL","4XL","5XL"].index(s)
                        if s in ["XS","S","M","L","XL","2XL","3XL","4XL","5XL"] else 99)

    print(f"  Sizes: {all_sizes}")

    # Check color matches
    print(f"\n  Shopify color -> Printify match:")
    color_map = {}  # shopify_color -> printify_color
    for sc in SHOPIFY_COLORS:
        # Exact match first
        exact = [c for c in all_colors if c.lower() == sc.lower()]
        if exact:
            color_map[sc] = exact[0]
            print(f"    {sc:15} -> {exact[0]} ✓")
        else:
            # Partial
            partial = [c for c in all_colors if sc.lower() in c.lower() or c.lower() in sc.lower()]
            if partial:
                color_map[sc] = partial[0]
                print(f"    {sc:15} -> {partial[0]} (partial match)")
            else:
                print(f"    {sc:15} -> NOT FOUND")

    # Show which sizes match
    print(f"\n  Shopify size -> available?")
    size_map = {}  # shopify_size -> printify_size
    for ss in SHOPIFY_SIZES:
        if ss in all_sizes:
            size_map[ss] = ss
            print(f"    {ss:5} -> ✓")
        else:
            print(f"    {ss:5} -> NOT FOUND")

    # Build variant ID map for matched colors+sizes
    print(f"\n  Matched variant IDs (color/size -> printify_id):")
    matched = {}
    for sc, pc in color_map.items():
        for ss, ps in size_map.items():
            vid = lookup.get((pc, ps))
            if vid:
                matched[(sc, ss)] = vid
                print(f"    {sc}/{ss} -> {vid}")
            else:
                print(f"    {sc}/{ss} -> MISSING")

    print(f"\n  Total matched: {len(matched)} / {len(SHOPIFY_COLORS)*len(SHOPIFY_SIZES)} variants")
    return {"color_map": color_map, "size_map": size_map, "variant_lookup": lookup, "matched": matched}

# Check blueprint 6 (Gildan 5000) with provider 99 (Printify Choice)
r6_99 = check_provider(6, 99, "(Gildan 5000 + Printify Choice)")

# Check blueprint 12 (Bella+Canvas 3001) with provider 26 (Textildruck Europa - has XS?)
r12_26 = check_provider(12, 26, "(Bella+Canvas 3001 + Textildruck Europa)")

# Check blueprint 12 with provider 99 for XS
r12_99 = check_provider(12, 99, "(Bella+Canvas 3001 + Printify Choice)")
