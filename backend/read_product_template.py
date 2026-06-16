"""Read full product template to find buy-button block location."""
import os, sys, json, httpx
from dotenv import load_dotenv
sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
STORE = os.environ["SHOPIFY_STORE"]
RH    = {"X-Shopify-Access-Token": os.environ["SHOPIFY_TOKEN"]}
API   = f"https://{STORE}/admin/api/2025-01"
THEME = 143507587185

r = httpx.get(f"{API}/themes/{THEME}/assets.json", headers=RH,
              params={"asset[key]": "templates/product.json"}, timeout=15)
pj = json.loads(r.json()["asset"]["value"])

def dump(obj, indent=0):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in ("settings", "blocks") and isinstance(v, dict) and len(v) > 3:
                print("  "*indent + f"{k}: {{...{len(v)} items...}}")
            elif k == "block_order":
                print("  "*indent + f"block_order: {v}")
            elif isinstance(v, (dict, list)):
                print("  "*indent + f"{k}:")
                dump(v, indent+1)
            else:
                val = repr(v)[:60]
                print("  "*indent + f"{k}: {val}")
    elif isinstance(obj, list):
        for item in obj:
            dump(item, indent)

# Just show the block tree
main = pj["sections"]["main"]
prod_details = main["blocks"]["product-details"]
print("product-details block_order:", prod_details.get("block_order"))
print("\nSub-blocks:")
for bkey in prod_details.get("block_order", []):
    block = prod_details["blocks"].get(bkey, {})
    btype = block.get("type")
    bname = block.get("name", "")
    sub_order = block.get("block_order", [])
    print(f"  [{bkey}] type={btype}  name={bname}")
    if sub_order:
        print(f"    block_order: {sub_order}")
        for sbkey in sub_order:
            sblock = block.get("blocks", {}).get(sbkey, {})
            sbtype = sblock.get("type")
            sbname = sblock.get("name", "")
            print(f"      [{sbkey}] type={sbtype}  name={sbname}")
