"""
Cross-reference full_checkpoint.json against live Shopify products.
Rebuilds the ID mapping in the checkpoint to use current live IDs.
"""
import json, os, httpx, time
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
STORE = os.environ["SHOPIFY_STORE"]
TOKEN = os.environ["SHOPIFY_TOKEN"]
HR  = {"X-Shopify-Access-Token": TOKEN}
API = f"https://{STORE}/admin/api/2025-01"

def get_all_products():
    items, url = [], f"{API}/products.json?limit=250&fields=id,title,status,options"
    while url:
        r = httpx.get(url, headers=HR, timeout=30)
        data = r.json()
        items.extend(data.get("products", []))
        link = r.headers.get("Link", "")
        url = None
        for part in link.split(","):
            if 'rel="next"' in part:
                url = part.split("<")[1].split(">")[0]
    return items

print("Fetching all Shopify products...")
all_prods = get_all_products()
print(f"Total: {len(all_prods)}")

# Build title → id map (normalised)
def norm(t): return t.lower().strip()
live_map = {norm(p["title"]): p["id"] for p in all_prods}

# Load checkpoint
cp = json.load(open("full_checkpoint.json", encoding="utf-8"))

found = missing = stale = 0
stale_list = []
for key, entry in cp.items():
    if entry.get("status") != "done":
        continue
    title = (entry.get("title") or "").strip()
    checkpoint_id = entry.get("new_shopify_id")
    live_id = live_map.get(norm(title))

    if live_id is None:
        print(f"  MISSING from Shopify: {title[:60]}")
        missing += 1
    elif str(live_id) != str(checkpoint_id):
        print(f"  STALE ID: {title[:55]}")
        print(f"    checkpoint={checkpoint_id}  live={live_id}")
        stale_list.append((key, entry, live_id))
        stale += 1
    else:
        found += 1

print(f"\nFound (IDs match): {found}")
print(f"Stale IDs (need update): {stale}")
print(f"Missing from Shopify: {missing}")

if stale_list:
    print("\nUpdating checkpoint with live IDs...")
    for key, entry, live_id in stale_list:
        cp[key]["new_shopify_id"] = live_id
    with open("full_checkpoint.json", "w", encoding="utf-8") as f:
        json.dump(cp, f, indent=2)
    print("checkpoint updated.")

    # Also update products_uploaded.json
    pu = json.load(open("products_uploaded.json", encoding="utf-8")) if os.path.exists("products_uploaded.json") else {}
    for key, entry, live_id in stale_list:
        title = entry.get("title","")
        if title in pu:
            pu[title] = live_id
    with open("products_uploaded.json", "w", encoding="utf-8") as f:
        json.dump(pu, f, indent=2)
    print("products_uploaded.json updated.")
