"""Inspect a Printify product's print_areas to understand the correct scale/position."""
import json, os, httpx
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
TOKEN   = os.environ["PRINTIFY_TOKEN"]
SHOP_ID = 27883571
PH      = {"Authorization": f"Bearer {TOKEN}"}
PAPI    = "https://api.printify.com/v1"

cp = json.load(open("full_checkpoint.json", encoding="utf-8"))
# grab first done product
entry = next(v for v in cp.values() if v.get("status") == "done")
title  = entry["title"]
ppid   = entry["printify_ids"]["UK_CC"]
print(f"Product: {title[:60]}\nPrintify ID: {ppid}\n")

r = httpx.get(f"{PAPI}/shops/{SHOP_ID}/products/{ppid}.json", headers=PH, timeout=30)
p = r.json()

for i, area in enumerate(p.get("print_areas", [])):
    vids = area.get("variant_ids", [])
    print(f"Area {i}: {len(vids)} variants")
    for ph in area.get("placeholders", []):
        pos = ph.get("position")
        imgs = ph.get("images", [])
        if imgs:
            img = imgs[0]
            print(f"  placeholder pos={pos}  id={img.get('id')}  x={img.get('x')}  y={img.get('y')}  scale={img.get('scale')}  angle={img.get('angle')}")
        else:
            print(f"  placeholder pos={pos}  (no images)")
