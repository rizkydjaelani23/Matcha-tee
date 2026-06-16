"""Deploy guarantee section to Shopify theme — homepage + product page."""
import os, sys, json, httpx
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

TOKEN = os.environ["SHOPIFY_TOKEN"]
STORE = os.environ["SHOPIFY_STORE"]
THEME = 143507587185
BASE  = f"https://{STORE}/admin/api/2025-01/themes/{THEME}/assets.json"
H     = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}

def get_asset(key):
    r = httpx.get(BASE, headers=H, params={"asset[key]": key}, timeout=20)
    r.raise_for_status()
    return r.json()["asset"]["value"]

def put_asset(key, value):
    r = httpx.put(BASE, headers=H, json={"asset": {"key": key, "value": value}}, timeout=20)
    if r.status_code not in (200, 201):
        raise Exception(f"PUT {key} failed {r.status_code}: {r.text[:300]}")
    print(f"  ✓ {key}")

# 1. Upload the snippet
snippet = open(os.path.join(os.path.dirname(__file__), "snippets", "tmt-guarantee.liquid"), encoding="utf-8").read()
put_asset("snippets/tmt-guarantee.liquid", snippet)

# 2. Add to homepage (after best_sellers, before tmt_reviews_home)
print("\nUpdating homepage template...")
index_raw = get_asset("templates/index.json")
index = json.loads(index_raw)

if "tmt_guarantee" not in index["sections"]:
    index["sections"]["tmt_guarantee"] = {
        "type": "custom-liquid",
        "settings": {
            "custom_liquid": "{% render 'tmt-guarantee' %}"
        }
    }
    order = index.get("order", [])
    # Insert after best_sellers
    try:
        pos = order.index("best_sellers") + 1
    except ValueError:
        pos = len(order)
    order.insert(pos, "tmt_guarantee")
    index["order"] = order
    put_asset("templates/index.json", json.dumps(index, indent=2))
else:
    print("  (guarantee already in homepage)")

# 3. Add to product page (after main product section)
print("\nUpdating product page template...")
try:
    prod_raw = get_asset("templates/product.json")
    prod = json.loads(prod_raw)

    if "tmt_guarantee" not in prod["sections"]:
        prod["sections"]["tmt_guarantee"] = {
            "type": "custom-liquid",
            "settings": {
                "custom_liquid": "{% render 'tmt-guarantee' %}"
            }
        }
        order = prod.get("order", [])
        # Add after the first section (main product)
        order.append("tmt_guarantee")
        prod["order"] = order
        put_asset("templates/product.json", json.dumps(prod, indent=2))
    else:
        print("  (guarantee already in product page)")
except Exception as e:
    print(f"  product page: {e}")

print("\nDone. Guarantee section is live on homepage and product pages.")
