"""Compare print_area dimensions between UK_CC and UK_GD to find why GD costs more."""
import json, os, httpx
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
TOKEN   = os.environ["PRINTIFY_TOKEN"]
SHOP_ID = 27883571
PH      = {"Authorization": f"Bearer {TOKEN}"}
PAPI    = "https://api.printify.com/v1"

cp = json.load(open("full_checkpoint.json", encoding="utf-8"))
entry = next(v for v in cp.values()
             if v.get("status") == "done"
             and v.get("new_shopify_id")
             and v["printify_ids"].get("UK_CC")
             and v["printify_ids"].get("UK_GD"))

print(f"Product: {entry['title'][:60]}\n")

for pkey in ["UK_CC", "UK_GD"]:
    ppid = entry["printify_ids"][pkey]
    r = httpx.get(f"{PAPI}/shops/{SHOP_ID}/products/{ppid}.json", headers=PH, timeout=30)
    p = r.json()

    # Cost summary
    costs = {}
    for v in p.get("variants", []):
        if not v.get("is_enabled"): continue
        parts = v.get("title", "").split(" / ")
        size = parts[1] if len(parts) > 1 else "?"
        if size not in costs:
            costs[size] = v.get("cost", 0)
    base = costs.get("M") or costs.get("S") or 0

    print(f"{'='*55}")
    print(f"{pkey}  blueprint={p.get('blueprint_id')}  provider={p.get('print_provider_id')}")
    print(f"Base cost (M/S): £{base/100:.2f}")

    # Print area details
    for area in p.get("print_areas", []):
        n_variants = len(area.get("variant_ids", []))
        print(f"\n  print_area covering {n_variants} variants:")
        for ph in area.get("placeholders", []):
            pos  = ph.get("position")
            imgs = ph.get("images", [])
            w    = ph.get("width")
            h    = ph.get("height")
            print(f"    position: {pos}  width={w}  height={h}")
            for img in imgs:
                print(f"      image_id={img.get('id')}  x={img.get('x')}  y={img.get('y')}  "
                      f"scale={img.get('scale')}  angle={img.get('angle')}")
    print()
