"""Check a product that hasn't been reuploaded yet to see the original print_area config."""
import json, os, httpx
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
TOKEN   = os.environ["PRINTIFY_TOKEN"]
SHOP_ID = 27883571
PH      = {"Authorization": f"Bearer {TOKEN}"}
PAPI    = "https://api.printify.com/v1"

rcp = json.load(open("reupload_checkpoint.json", encoding="utf-8")) if os.path.exists("reupload_checkpoint.json") else {}
cp  = json.load(open("full_checkpoint.json", encoding="utf-8"))

# Find a product NOT yet in reupload checkpoint
entry = None
seen  = set()
for v in cp.values():
    if v.get("status") != "done": continue
    t = (v.get("title") or "").strip().lower()
    if t in seen: continue
    seen.add(t)
    if v.get("title","") not in rcp:
        entry = v
        break

if not entry:
    print("All products already reuploaded")
else:
    title = entry["title"]
    for pkey in ["UK_CC", "UK_GD"]:
        ppid = entry["printify_ids"].get(pkey)
        if not ppid: continue
        r = httpx.get(f"{PAPI}/shops/{SHOP_ID}/products/{ppid}.json", headers=PH, timeout=30)
        p = r.json()
        print(f"\n{title[:55]} — {pkey} ({ppid})")
        for area in p.get("print_areas", []):
            for ph in area.get("placeholders", []):
                pos  = ph.get("position")
                imgs = ph.get("images", [])
                if imgs:
                    img = imgs[0]
                    print(f"  {pos}: x={img.get('x')} y={img.get('y')} scale={img.get('scale')} angle={img.get('angle')}")
                else:
                    print(f"  {pos}: (empty)")
        break
