"""
Retry just the 7 publish_error products in the sync checkpoint.
For each: re-publish the existing Printify product to Shopify,
then migrate collections and handle from old → new product.
"""
import os, sys, time, json, httpx
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

STORE         = os.environ["SHOPIFY_STORE"]
SHOPIFY_TOKEN = os.environ["SHOPIFY_TOKEN"]
PRINTIFY_TOKEN = os.environ["PRINTIFY_TOKEN"]
SH  = {"X-Shopify-Access-Token": SHOPIFY_TOKEN, "Content-Type": "application/json"}
SHR = {"X-Shopify-Access-Token": SHOPIFY_TOKEN}
PH  = {"Authorization": f"Bearer {PRINTIFY_TOKEN}", "Content-Type": "application/json"}
SAPI = f"https://{STORE}/admin/api/2025-01"
PAPI = "https://api.printify.com/v1"
SHOP_ID = 27883571
CHECKPOINT = os.path.join(os.path.dirname(__file__), "sync_checkpoint.json")

cp = json.load(open(CHECKPOINT, encoding="utf-8"))
errors = {k: v for k, v in cp.items() if v.get("status") == "publish_error"}
print(f"Found {len(errors)} error products to retry")

def save_cp():
    with open(CHECKPOINT, "w", encoding="utf-8") as f:
        json.dump(cp, f, indent=2)

ok = fail = 0
for old_sid, data in errors.items():
    pid = data["printify_id"]

    # Fetch old Shopify product for title/handle/collections
    r0 = httpx.get(f"{SAPI}/products/{old_sid}.json",
                   headers=SHR, timeout=20)
    if r0.status_code != 200:
        print(f"  [{old_sid}] Old Shopify product gone (404) — skipping")
        fail += 1
        continue

    sp = r0.json().get("product", {})
    title = sp.get("title", f"product-{old_sid}")
    handle = sp.get("handle", "")
    print(f"\n[{old_sid}] {title[:55]}")
    print(f"  Printify: {pid}")

    # Verify Printify product exists
    r1 = httpx.get(f"{PAPI}/shops/{SHOP_ID}/products/{pid}.json", headers=PH, timeout=20)
    if r1.status_code != 200:
        print(f"  Printify product not found ({r1.status_code}) — cannot retry")
        fail += 1
        continue
    print(f"  Printify product exists")

    # Get collections before migrating
    r2 = httpx.get(f"{SAPI}/products/{old_sid}/collects.json", headers=SHR, timeout=20)
    collection_ids = [c["collection_id"] for c in r2.json().get("collects", [])]
    print(f"  Collections: {collection_ids}")

    # Publish to Shopify
    payload = {"title": True, "description": True, "images": True,
                "variants": True, "tags": True, "keyFeatures": True,
                "shipping_template": True}
    new_sid = None
    for attempt in range(6):
        rp = httpx.post(f"{PAPI}/shops/{SHOP_ID}/products/{pid}/publish.json",
                        headers=PH, json=payload, timeout=60)
        if rp.status_code in (200, 201):
            print(f"  Published!")
            break
        if rp.status_code == 429:
            wait = 70 + attempt * 30
            print(f"  429 — waiting {wait}s...")
            time.sleep(wait)
            continue
        print(f"  Publish failed {rp.status_code}: {rp.text[:150]}")
        fail += 1
        break
    else:
        print(f"  Giving up on publish after 6 attempts")
        fail += 1
        continue

    # Wait for Printify→Shopify sync
    print(f"  Waiting for Shopify ID...")
    time.sleep(20)
    for attempt in range(15):
        r3 = httpx.get(f"{PAPI}/shops/{SHOP_ID}/products/{pid}.json", headers=PH, timeout=20)
        if r3.status_code == 200:
            ext = r3.json().get("external")
            if isinstance(ext, dict):
                eid = ext.get("id")
                if eid:
                    new_sid = str(eid)
                    break
        time.sleep(5)

    if not new_sid:
        print(f"  Could not get new Shopify ID — leaving as publish_error")
        fail += 1
        continue

    print(f"  New Shopify ID: {new_sid}")

    # Add to collections
    for cid in collection_ids:
        httpx.post(f"{SAPI}/collects.json", headers=SH,
                   json={"collect": {"product_id": int(new_sid), "collection_id": cid}},
                   timeout=20)
        time.sleep(0.2)

    # Fix handle: rename old, set new to original handle
    if handle:
        httpx.put(f"{SAPI}/products/{old_sid}.json", headers=SH,
                  json={"product": {"id": old_sid, "handle": f"{handle}-old"}}, timeout=20)
        time.sleep(0.5)
        httpx.put(f"{SAPI}/products/{new_sid}.json", headers=SH,
                  json={"product": {"id": int(new_sid), "handle": handle}}, timeout=20)
        time.sleep(0.5)

    # Delete old product
    rd = httpx.delete(f"{SAPI}/products/{old_sid}.json", headers=SHR, timeout=20)
    if rd.status_code == 200:
        print(f"  Old product deleted")
    else:
        print(f"  WARN: delete failed {rd.status_code}")

    # Update checkpoint
    cp[old_sid]["status"] = "done"
    cp[old_sid]["new_shopify_id"] = new_sid
    save_cp()
    print(f"  DONE")
    ok += 1

    time.sleep(5)

print(f"\n{'='*40}")
print(f"Retried: {ok} fixed, {fail} still failing")
