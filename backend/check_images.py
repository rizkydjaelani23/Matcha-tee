import json, os, httpx
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
TOKEN = os.environ["PRINTIFY_TOKEN"]
SHOP_ID = 27883571
PH = {"Authorization": f"Bearer {TOKEN}"}

cp = json.load(open("full_checkpoint.json", encoding="utf-8"))
entry = next(v for v in cp.values() if "addison rae" in (v.get("title","") or "").lower() and v.get("status")=="done")
ppid = entry["printify_ids"]["UK_CC"]
print(f"Checking product {ppid}")
r = httpx.get(f"https://api.printify.com/v1/shops/{SHOP_ID}/products/{ppid}.json", headers=PH, timeout=30)
p = r.json()
images = p.get("images", [])
print(f"Images count: {len(images)}")
for img in images[:8]:
    src = img.get("src", "")[:80]
    default = img.get("is_default")
    pos = img.get("position")
    print(f"  pos={pos}  default={default}  src={src}")
print()
print("print_areas image ids:")
for area in p.get("print_areas", [])[:1]:
    for ph in area.get("placeholders", []):
        for im in ph.get("images", []):
            print(f"  {im.get('id')}")
