"""
1. Shirt Monkey full color list + variant IDs for 9 chosen colors
2. US domestic providers (providers with a US-specific shipping rate)
3. Printify Choice colors
"""
import httpx, os, sys
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

PTOKEN = os.environ["PRINTIFY_TOKEN"]
PAPI   = "https://api.printify.com/v1"
PH     = {"Authorization": f"Bearer {PTOKEN}"}
BLUEPRINT_ID = 706

SHIRT_MONKEY_WANTED = [
    "Black", "White", "Pepper", "Grey", "Ivory",
    "Light Green", "Chambray", "Washed Denim", "Blossom",
]
SIZES = ["S","M","L","XL","2XL","3XL"]

# ── 1. SHIRT MONKEY ──────────────────────────────────────────────────────────
print("=" * 60)
print("SHIRT MONKEY (ID=331) — full color list + variant IDs")
print("=" * 60)

rv = httpx.get(f"{PAPI}/catalog/blueprints/{BLUEPRINT_ID}/print_providers/331/variants.json",
               headers=PH, timeout=20)
variants = rv.json().get("variants", [])

sm_colors = {}
for v in variants:
    opts  = v.get("options", {})
    color = opts.get("color", "?")
    size  = opts.get("size",  "?")
    sm_colors.setdefault(color, {})[size] = v["id"]

print(f"\nAll {len(sm_colors)} colors available on Shirt Monkey:")
for c in sorted(sm_colors.keys()):
    sizes = sm_colors[c]
    ids   = [f"{s}={sizes[s]}" for s in SIZES if s in sizes]
    avail = ", ".join(ids) if ids else "(no sizes)"
    print(f"  {c}: {avail}")

print("\n--- Variant map for our 9 chosen colors ---")
sm_variant_map = {}
for want in SHIRT_MONKEY_WANTED:
    match_key = next((k for k in sm_colors if k.lower() == want.lower()), None)
    if match_key:
        sizes = sm_colors[match_key]
        ids   = {s: sizes[s] for s in SIZES if s in sizes}
        sm_variant_map[want] = ids
        ids_str = ", ".join(f"{s}:{v}" for s, v in ids.items())
        print(f"  ✓ {want}: {ids_str}")
    else:
        print(f"  ✗ {want} — NOT FOUND")

# ── 2. US DOMESTIC PROVIDERS ─────────────────────────────────────────────────
print("\n" + "=" * 60)
print("US-BASED PROVIDERS (have US domestic shipping rate)")
print("=" * 60)

r = httpx.get(f"{PAPI}/catalog/blueprints/{BLUEPRINT_ID}/print_providers.json", headers=PH, timeout=20)
providers = r.json()

WANTED_SET = {c.lower() for c in SHIRT_MONKEY_WANTED}

us_providers = []
for p in providers:
    pid   = p["id"]
    pname = p["title"]

    rs = httpx.get(f"{PAPI}/catalog/blueprints/{BLUEPRINT_ID}/print_providers/{pid}/shipping.json",
                   headers=PH, timeout=20)
    profiles = rs.json().get("profiles", [])

    us_cost = None
    us_curr = ""
    for profile in profiles:
        countries = profile.get("countries", [])
        if "US" in countries:
            first   = profile.get("first_item", {})
            us_cost = first.get("cost", 0) / 100
            us_curr = first.get("currency", "")
            break

    if us_cost is not None:
        rv = httpx.get(f"{PAPI}/catalog/blueprints/{BLUEPRINT_ID}/print_providers/{pid}/variants.json",
                       headers=PH, timeout=20)
        variants2 = rv.json().get("variants", [])
        avail = {v.get("options", {}).get("color", "").lower() for v in variants2
                 if v.get("options", {}).get("color")}
        matched = len(WANTED_SET & avail)
        missing = sorted(WANTED_SET - avail)
        us_providers.append((pname, pid, us_cost, us_curr, matched, missing))
        print(f"\n  {pname} (ID={pid}): US={us_cost:.2f} {us_curr}  {matched}/9 of our colors")
        if missing:
            print(f"    Missing: {', '.join(missing)}")

# ── 3. PRINTIFY CHOICE ───────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("PRINTIFY CHOICE (ID=99) — color coverage")
print("=" * 60)
rv = httpx.get(f"{PAPI}/catalog/blueprints/{BLUEPRINT_ID}/print_providers/99/variants.json",
               headers=PH, timeout=20)
variants = rv.json().get("variants", [])
pc_colors = {v.get("options", {}).get("color", "").lower() for v in variants
             if v.get("options", {}).get("color")}

for want in SHIRT_MONKEY_WANTED:
    if want.lower() in pc_colors:
        print(f"  ✓ {want}")
    else:
        close = next((c for c in pc_colors if want.lower() in c or c in want.lower()), None)
        if close:
            print(f"  ~ {want} (closest: '{close}')")
        else:
            print(f"  ✗ {want} — NOT AVAILABLE on Printify Choice")
