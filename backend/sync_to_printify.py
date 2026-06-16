"""
sync_to_printify.py
====================
Creates all 99 Shopify products in Printify (Blueprint 6 = Gildan 5000,
Provider 99 = Printify Choice), publishes each back to Shopify, migrates
collections, and replaces the old manual-fulfillment product.

Run:  python sync_to_printify.py              # full sync
      python sync_to_printify.py --dry        # no changes, show plan
      python sync_to_printify.py --limit 3    # test first 3 products

Checkpoint file (sync_checkpoint.json) lets you resume after errors.
"""
import os, sys, time, json, argparse, httpx
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

STORE          = os.environ["SHOPIFY_STORE"]
SHOPIFY_TOKEN  = os.environ["SHOPIFY_TOKEN"]
PRINTIFY_TOKEN = os.environ["PRINTIFY_TOKEN"]
SH  = {"X-Shopify-Access-Token": SHOPIFY_TOKEN, "Content-Type": "application/json"}
SHR = {"X-Shopify-Access-Token": SHOPIFY_TOKEN}
PH  = {"Authorization": f"Bearer {PRINTIFY_TOKEN}", "Content-Type": "application/json"}
SAPI  = f"https://{STORE}/admin/api/2025-01"
PAPI  = "https://api.printify.com/v1"
SHOP_ID = 27883571  # Printify shop ID for Matcha Tees
BLUEPRINT_ID   = 6   # Gildan 5000 Heavy Cotton Tee
PROVIDER_ID    = 99  # Printify Choice (auto-routes to best provider)
CHECKPOINT     = os.path.join(os.path.dirname(__file__), "sync_checkpoint.json")

# ── Variant IDs: Blueprint 6 + Provider 99, colors × sizes ──────────────────
# Format: (Color, Size) -> Printify variant ID
VARIANT_MAP = {
    ("White",      "S"):   12102, ("White",      "M"):   12101, ("White",      "L"):   12100,
    ("White",      "XL"):  12103, ("White",      "2XL"): 12104, ("White",      "3XL"): 12105,
    ("Black",      "S"):   12126, ("Black",      "M"):   12125, ("Black",      "L"):   12124,
    ("Black",      "XL"):  12127, ("Black",      "2XL"): 12128, ("Black",      "3XL"): 12129,
    ("Navy",       "S"):   11988, ("Navy",       "M"):   11987, ("Navy",       "L"):   11986,
    ("Navy",       "XL"):  11989, ("Navy",       "2XL"): 11990, ("Navy",       "3XL"): 11991,
    ("Sport Grey", "S"):   12072, ("Sport Grey", "M"):   12071, ("Sport Grey", "L"):   12070,
    ("Sport Grey", "XL"):  12073, ("Sport Grey", "2XL"): 12074, ("Sport Grey", "3XL"): 12075,
    ("Daisy",      "S"):   11892, ("Daisy",      "M"):   11891, ("Daisy",      "L"):   11890,
    ("Daisy",      "XL"):  11893, ("Daisy",      "2XL"): 11894, ("Daisy",      "3XL"): 11895,
    ("Light Blue", "S"):   11958, ("Light Blue", "M"):   11957, ("Light Blue", "L"):   11956,
    ("Light Blue", "XL"):  11959, ("Light Blue", "2XL"): 11960, ("Light Blue", "3XL"): 11961,
}
PRINTIFY_VARIANT_IDS = list(set(VARIANT_MAP.values()))
RETAIL_PRICE_PENCE   = 2700  # £27.00

# ── Checkpoint helpers ────────────────────────────────────────────────────────
def load_checkpoint():
    if os.path.exists(CHECKPOINT):
        with open(CHECKPOINT, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_checkpoint(data):
    with open(CHECKPOINT, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

# ── Shopify helpers ───────────────────────────────────────────────────────────
def shopify_get(path, params=None):
    for _ in range(3):
        r = httpx.get(f"{SAPI}{path}", headers=SHR, params=params, timeout=30)
        if r.status_code == 429:
            time.sleep(float(r.headers.get("Retry-After", 2)))
            continue
        return r
    return r

def shopify_post(path, body):
    for _ in range(3):
        r = httpx.post(f"{SAPI}{path}", headers=SH, json=body, timeout=30)
        if r.status_code == 429:
            time.sleep(float(r.headers.get("Retry-After", 2)))
            continue
        return r
    return r

def shopify_put(path, body):
    for _ in range(3):
        r = httpx.put(f"{SAPI}{path}", headers=SH, json=body, timeout=30)
        if r.status_code == 429:
            time.sleep(float(r.headers.get("Retry-After", 2)))
            continue
        return r
    return r

def shopify_delete(path):
    for _ in range(3):
        r = httpx.delete(f"{SAPI}{path}", headers=SHR, timeout=30)
        if r.status_code == 429:
            time.sleep(float(r.headers.get("Retry-After", 2)))
            continue
        return r
    return r

# ── Printify helpers ──────────────────────────────────────────────────────────
def printify_get(path):
    for _ in range(3):
        r = httpx.get(f"{PAPI}{path}", headers=PH, timeout=30)
        if r.status_code == 429:
            time.sleep(10)
            continue
        return r
    return r

def printify_post(path, body):
    for _ in range(3):
        r = httpx.post(f"{PAPI}{path}", headers=PH, json=body, timeout=60)
        if r.status_code == 429:
            time.sleep(10)
            continue
        return r
    return r

# ── Fetch all Shopify products ────────────────────────────────────────────────
def fetch_all_shopify_products():
    products = []
    url = f"{SAPI}/products.json?limit=250&fields=id,title,body_html,handle,images,variants,tags"
    while url:
        r = httpx.get(url, headers=SHR, timeout=30)
        products.extend(r.json().get("products", []))
        link = r.headers.get("Link", "")
        url = None
        for part in link.split(","):
            if 'rel="next"' in part:
                url = part.strip().split(";")[0].strip("<> ")
    return products

def fetch_product_collections(shopify_product_id):
    """Returns list of collection IDs the product belongs to."""
    r = shopify_get(f"/products/{shopify_product_id}/collects.json")
    if r.status_code != 200:
        return []
    return [c["collection_id"] for c in r.json().get("collects", [])]

# ── Step 1: Upload image to Printify ─────────────────────────────────────────
def upload_image(image_url, file_name):
    r = printify_post("/uploads/images.json", {
        "file_name": file_name,
        "url": image_url,
    })
    if r.status_code not in (200, 201):
        raise Exception(f"Image upload failed {r.status_code}: {r.text[:200]}")
    return r.json()["id"]

# ── Step 2: Create Printify product ──────────────────────────────────────────
def create_printify_product(title, description, image_upload_id):
    variants = [
        {"id": vid, "price": RETAIL_PRICE_PENCE, "is_enabled": True}
        for vid in PRINTIFY_VARIANT_IDS
    ]
    body = {
        "title": title,
        "description": description or "",
        "blueprint_id": BLUEPRINT_ID,
        "print_provider_id": PROVIDER_ID,
        "variants": variants,
        "print_areas": [
            {
                "variant_ids": PRINTIFY_VARIANT_IDS,
                "placeholders": [
                    {
                        "position": "front",
                        "images": [
                            {
                                "id": image_upload_id,
                                "x": 0.5,
                                "y": 0.5,
                                "scale": 1.0,
                                "angle": 0,
                            }
                        ],
                    }
                ],
            }
        ],
    }
    r = printify_post(f"/shops/{SHOP_ID}/products.json", body)
    if r.status_code not in (200, 201):
        raise Exception(f"Create product failed {r.status_code}: {r.text[:300]}")
    return r.json()["id"]

# ── Step 3: Publish Printify product to Shopify ───────────────────────────────
def publish_to_shopify(printify_product_id):
    payload = {
        "title": True,
        "description": True,
        "images": True,
        "variants": True,
        "tags": True,
        "keyFeatures": True,
        "shipping_template": True,
    }
    # Retry with back-off for 429 rate limit
    for attempt in range(6):
        r = printify_post(
            f"/shops/{SHOP_ID}/products/{printify_product_id}/publish.json",
            payload,
        )
        if r.status_code in (200, 201):
            return r.json()
        if r.status_code == 429:
            wait = 70 + attempt * 30  # 70s, 100s, 130s...
            print(f"  Rate limited (429). Waiting {wait}s before retry...")
            time.sleep(wait)
            continue
        raise Exception(f"Publish failed {r.status_code}: {r.text[:300]}")
    raise Exception("Publish still rate-limited after 6 retries")

# ── Step 4: Get new Shopify product ID from Printify product ──────────────────
def get_new_shopify_id(printify_product_id):
    """
    Poll Printify until the product has an external_id (Shopify product ID).
    Uses the listing endpoint which is more reliable for fresh publishes.
    """
    # Wait for Printify→Shopify sync (typically 5-15 seconds)
    time.sleep(15)
    for attempt in range(15):
        # Single product endpoint
        r = printify_get(f"/shops/{SHOP_ID}/products/{printify_product_id}.json")
        if r.status_code == 200:
            p = r.json()
            ext = p.get("external")
            if isinstance(ext, dict):
                eid = ext.get("id")
                if eid:
                    return str(eid)
        # Also try listing endpoint (more reliable after fresh publish)
        r2 = printify_get(f"/shops/{SHOP_ID}/products.json?limit=50")
        if r2.status_code == 200:
            for prod in r2.json().get("data", []):
                if prod.get("id") == printify_product_id:
                    ext = prod.get("external")
                    if isinstance(ext, dict):
                        eid = ext.get("id")
                        if eid:
                            return str(eid)
        time.sleep(5)
    return None

# ── Step 5: Add new Shopify product to collections ───────────────────────────
def add_to_collections(new_shopify_id, collection_ids):
    for cid in collection_ids:
        r = shopify_post("/collects.json", {
            "collect": {"product_id": int(new_shopify_id), "collection_id": cid}
        })
        if r.status_code not in (200, 201):
            print(f"    WARN: failed to add to collection {cid}: {r.status_code}")
        time.sleep(0.2)

# ── Step 6: Fix handle and delete old Shopify product ────────────────────────
def migrate_handle(old_handle, new_shopify_id, old_shopify_id, dry_run=False):
    if dry_run:
        return

    # Rename old product handle to free up the slug
    old_new_handle = f"{old_handle}-printify-old"
    shopify_put(f"/products/{old_shopify_id}.json", {
        "product": {"id": old_shopify_id, "handle": old_new_handle}
    })
    time.sleep(0.5)

    # Set new product handle to match the original
    r = shopify_put(f"/products/{new_shopify_id}.json", {
        "product": {"id": int(new_shopify_id), "handle": old_handle}
    })
    if r.status_code not in (200, 201):
        print(f"    WARN: could not set handle {old_handle}: {r.status_code}")

    # Create URL redirect: /products/old_handle -> /products/old_handle (same, already handled by new product)
    # Actually create redirect from the -printify-old handle just in case
    shopify_post("/redirects.json", {
        "redirect": {
            "path": f"/products/{old_new_handle}",
            "target": f"/products/{old_handle}",
        }
    })

    # Delete old product
    time.sleep(0.5)
    r = shopify_delete(f"/products/{old_shopify_id}.json")
    if r.status_code != 200:
        print(f"    WARN: delete old product failed: {r.status_code}")

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true", help="Dry run, no changes")
    ap.add_argument("--limit", type=int, default=0, help="Process only first N products")
    ap.add_argument("--reset", action="store_true", help="Clear checkpoint and start fresh")
    args = ap.parse_args()

    if args.reset and os.path.exists(CHECKPOINT):
        os.remove(CHECKPOINT)
        print("Checkpoint cleared.")

    checkpoint = load_checkpoint()

    print("Fetching all Shopify products...")
    products = fetch_all_shopify_products()
    print(f"Found {len(products)} products.")

    if args.limit:
        products = products[:args.limit]
        print(f"Limiting to first {args.limit} products.")

    if args.dry:
        print("\n[DRY RUN] Would process:")
        for p in products:
            img = p["images"][0]["src"] if p.get("images") else "NO IMAGE"
            print(f"  [{p['id']}] {p['title'][:55]}  variants={len(p['variants'])}  img={img[:60]}")
        return

    total = len(products)
    ok = fail = skip = 0

    for i, product in enumerate(products, 1):
        pid     = str(product["id"])
        title   = product["title"]
        handle  = product["handle"]
        desc    = product.get("body_html", "") or ""
        images  = product.get("images", [])

        print(f"\n[{i}/{total}] {title[:55]}")

        # Skip if already done
        cp = checkpoint.get(pid, {})
        if cp.get("status") == "done":
            print(f"  SKIP (already migrated)")
            skip += 1
            continue

        # Clear stale publish_error so the publish step re-runs
        if cp.get("status") == "publish_error":
            checkpoint[pid]["status"] = None
            save_checkpoint(checkpoint)

        if not images:
            print(f"  SKIP — no images")
            checkpoint[pid] = {"status": "no_image", "title": title}
            save_checkpoint(checkpoint)
            skip += 1
            continue

        img_url = images[0]["src"]
        img_name = img_url.split("/")[-1].split("?")[0] or "design.jpg"
        if not img_name.endswith((".jpg",".jpeg",".png")):
            img_name += ".jpg"

        try:
            # 1. Upload image to Printify
            print(f"  Uploading image...")
            image_id = checkpoint.get(pid, {}).get("image_id")
            if not image_id:
                image_id = upload_image(img_url, img_name)
                checkpoint[pid] = {"image_id": image_id}
                save_checkpoint(checkpoint)
            else:
                print(f"  (reusing cached image_id={image_id})")

            # 2. Create Printify product
            print(f"  Creating Printify product...")
            printify_id = checkpoint.get(pid, {}).get("printify_id")
            if not printify_id:
                printify_id = create_printify_product(title, desc, image_id)
                checkpoint[pid]["printify_id"] = printify_id
                save_checkpoint(checkpoint)
                print(f"  Printify product: {printify_id}")
            else:
                print(f"  (reusing printify_id={printify_id})")

            time.sleep(1)

            # 3. Publish to Shopify
            print(f"  Publishing to Shopify...")
            new_shopify_id = checkpoint.get(pid, {}).get("new_shopify_id")
            if not new_shopify_id:
                publish_to_shopify(printify_id)
                new_shopify_id = get_new_shopify_id(printify_id)
                if not new_shopify_id:
                    print(f"  ERROR: could not get new Shopify ID after publish")
                    checkpoint[pid]["status"] = "publish_error"
                    save_checkpoint(checkpoint)
                    fail += 1
                    continue
                checkpoint[pid]["new_shopify_id"] = new_shopify_id
                save_checkpoint(checkpoint)
                print(f"  New Shopify product: {new_shopify_id}")
            else:
                print(f"  (reusing new_shopify_id={new_shopify_id})")

            # 4. Migrate collections
            if not checkpoint.get(pid, {}).get("collections_done"):
                print(f"  Migrating collections...")
                collection_ids = fetch_product_collections(product["id"])
                if collection_ids:
                    add_to_collections(new_shopify_id, collection_ids)
                checkpoint[pid]["collections_done"] = True
                save_checkpoint(checkpoint)

            # 5. Fix handle + delete old product
            if not checkpoint.get(pid, {}).get("handle_done"):
                print(f"  Fixing handle and deleting old product...")
                migrate_handle(handle, new_shopify_id, product["id"])
                checkpoint[pid]["handle_done"] = True
                save_checkpoint(checkpoint)

            checkpoint[pid]["status"] = "done"
            save_checkpoint(checkpoint)
            print(f"  DONE")
            ok += 1

        except Exception as e:
            print(f"  ERROR: {e}")
            checkpoint.setdefault(pid, {})["error"] = str(e)
            save_checkpoint(checkpoint)
            fail += 1

        time.sleep(65)  # Printify publish rate limit: ~1/min

    print(f"\n{'='*50}")
    print(f"Sync complete: {ok} migrated, {skip} skipped, {fail} errors")
    if fail:
        print(f"Re-run to retry errors (checkpoint preserves progress).")
    if os.path.exists(CHECKPOINT):
        print(f"Checkpoint: {CHECKPOINT}")

if __name__ == "__main__":
    main()
