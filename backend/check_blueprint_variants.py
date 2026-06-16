"""
Check existing Printify product details and blueprint 6 print provider variants
to find the correct variant IDs for the sync.
"""
import os, sys, httpx, json
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
PRINTIFY_TOKEN = os.environ["PRINTIFY_TOKEN"]
PH = {"Authorization": f"Bearer {PRINTIFY_TOKEN}"}
PAPI = "https://api.printify.com/v1"
SHOP_ID = 27883571
BLUEPRINT_ID = 6  # Gildan 5000

# ── Look at existing Fitzwilliam product to see provider + variant structure ─
print("=== Existing Fitzwilliam Darcy Regular Shirt ===")
r = httpx.get(f"{PAPI}/shops/{SHOP_ID}/products/6a2a9f8fb1dcb5e915001cb0.json", headers=PH, timeout=20)
p = r.json()
print(f"Title: {p.get('title')}")
print(f"Blueprint: {p.get('blueprint_id')}  Provider: {p.get('print_provider_id')}")
print(f"Variants ({len(p.get('variants',[]))}):")
for v in p.get("variants", [])[:10]:
    print(f"  id={v['id']}  {v.get('title','')}  enabled={v.get('is_enabled')}  price={v.get('price')}")

print(f"\nPrint areas:")
for pa in p.get("print_areas", []):
    print(f"  position={pa.get('position')}  files={[f.get('id') for f in pa.get('files',[])]}")

# ── All print providers for blueprint 6 ──────────────────────────────────────
print("\n\n=== All Print Providers for Blueprint 6 (Gildan 5000) ===")
r = httpx.get(f"{PAPI}/catalog/blueprints/{BLUEPRINT_ID}/print_providers.json", headers=PH, timeout=20)
providers = r.json()
for p in providers:
    print(f"  id={p['id']:4}  {p['title']}")

# ── Check variants for the provider used in existing product ─────────────────
provider_id = p.get("print_provider_id", 26) if hasattr(p, "get") else 26
# Force check provider 26 (Textildruck Europa) and 99 (Printify Choice)
for pid in [26, 99, 6]:
    print(f"\n=== Blueprint {BLUEPRINT_ID} + Provider {pid} variants ===")
    r2 = httpx.get(
        f"{PAPI}/catalog/blueprints/{BLUEPRINT_ID}/print_providers/{pid}/variants.json",
        headers=PH, timeout=20
    )
    if r2.status_code != 200:
        print(f"  Error {r2.status_code}: {r2.text[:100]}")
        continue
    variants = r2.json().get("variants", [])
    # Group by color
    colors = {}
    for v in variants:
        title = v.get("title","")
        parts = title.split(" / ")
        color = parts[1] if len(parts)>1 else title
        size  = parts[0] if len(parts)>0 else ""
        if color not in colors:
            colors[color] = {}
        colors[color][size] = v["id"]

    print(f"  Total variants: {len(variants)}")
    print(f"  Colors available:")
    for color in sorted(colors.keys()):
        sizes_available = list(colors[color].keys())
        print(f"    {color}: {', '.join(sizes_available)}")

    # Check which colors match our Shopify products
    needed = ["White","Black","Navy","Sport Grey","Daisy","Light Blue"]
    print(f"\n  Shopify color mapping check:")
    for c in needed:
        match = [k for k in colors.keys() if c.lower() in k.lower()]
        if match:
            print(f"    {c} -> FOUND as: {match}")
        else:
            print(f"    {c} -> NOT FOUND (available: partial search...)")
            close = [k for k in colors.keys() if any(w in k.lower() for w in c.lower().split())]
            print(f"           Closest: {close[:3]}")
