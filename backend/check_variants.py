import httpx, os, sys
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv(".env")
PTOKEN = os.environ["PRINTIFY_TOKEN"]
SHOP_ID = 27883571
PH = {"Authorization": f"Bearer {PTOKEN}"}

r = httpx.get(f"https://api.printify.com/v1/shops/{SHOP_ID}/products/6a2f6d34932a1fec8803f34a.json", headers=PH, timeout=20)
p = r.json()
print("Variants (first 5):")
for v in p.get("variants", [])[:5]:
    print(f"  id={v['id']}  enabled={v.get('is_enabled')}  title={v.get('title')}")
print(f"Total variants: {len(p.get('variants',[]))}")
print()
print("Print areas:")
for area in p.get("print_areas", []):
    vids = area.get("variant_ids", [])
    print(f"  variant_ids (first 5): {vids[:5]} ... total: {len(vids)}")
