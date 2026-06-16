"""
migrate_to_comfort_colors.py
=============================
Migrates ALL Shopify products from Gildan 5000 (Blueprint 6) to
Comfort Colors 1717 (Blueprint 706), Printify Choice (Provider 99).

- 15 colours chosen by the store owner
- Price: £29.99 (2999 pence)
- Uses original design images from catalogue.csv where possible,
  falls back to current Shopify product image

Run:  python migrate_to_comfort_colors.py --dry      # plan only
      python migrate_to_comfort_colors.py --limit 2  # test 2 products
      python migrate_to_comfort_colors.py             # full run
"""
import os, sys, time, json, csv, argparse, httpx
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

STORE          = os.environ["SHOPIFY_STORE"]
SHOPIFY_TOKEN  = os.environ["SHOPIFY_TOKEN"]
PRINTIFY_TOKEN = os.environ["PRINTIFY_TOKEN"]
SH  = {"X-Shopify-Access-Token": SHOPIFY_TOKEN, "Content-Type": "application/json"}
SHR = {"X-Shopify-Access-Token": SHOPIFY_TOKEN}
PH  = {"Authorization": f"Bearer {PRINTIFY_TOKEN}", "Content-Type": "application/json"}
SAPI    = f"https://{STORE}/admin/api/2025-01"
PAPI    = "https://api.printify.com/v1"
SHOP_ID = 27883571

BLUEPRINT_ID = 706   # Comfort Colors 1717 Garment-Dyed T-Shirt
PROVIDER_ID  = 29    # Monster Digital — only provider with all 15 colors incl. Neon Pink
RETAIL_PRICE = 2999  # £29.99 in pence

CHECKPOINT = os.path.join(os.path.dirname(__file__), "cc_checkpoint.json")

# ── Variant map: CC1717 via Monster Digital (Provider 29) ────────────────────
# All 15 owner-selected colors confirmed available on this provider
VARIANT_MAP = {
    "White":      {"S":73199, "M":73203, "L":73207, "XL":73211, "2XL":73215, "3XL":79169},
    "Black":      {"S":73196, "M":73200, "L":73204, "XL":73208, "2XL":73212, "3XL":79114},
    "Pepper":     {"S":79046, "M":79047, "L":79048, "XL":79049, "2XL":79050, "3XL":79155},
    "Grey":       {"S":78971, "M":78972, "L":78973, "XL":78974, "2XL":78975, "3XL":79137},
    "Navy":       {"S":73197, "M":73201, "L":73205, "XL":73209, "2XL":73213, "3XL":79152},
    "Red":        {"S":73198, "M":73202, "L":73206, "XL":73210, "2XL":73214, "3XL":79157},
    "Chili":      {"S":78926, "M":78927, "L":78928, "XL":78929, "2XL":78930, "3XL":79125},
    "Espresso":   {"S":102352,"M":102353,"L":102354,"XL":102355,"2XL":102356,"3XL":102357},
    "Ivory":      {"S":78991, "M":78992, "L":78993, "XL":78994, "2XL":78995, "3XL":79142},
    "Mustard":    {"S":79026, "M":79027, "L":79028, "XL":79029, "2XL":79030, "3XL":79150},
    "Butter":     {"S":78866, "M":78867, "L":78868, "XL":78869, "2XL":78870, "3XL":79122},
    "Bay":        {"S":78876, "M":78877, "L":78878, "XL":78879, "2XL":78880, "3XL":79112},
    "Blossom":    {"S":78886, "M":78887, "L":78888, "XL":78889, "2XL":78890, "3XL":79115},
    "Neon Pink":  {"S":148331,"M":148332,"L":148333,"XL":148334,"2XL":148335,"3XL":148336},
    "Light Green":{"S":79006, "M":79007, "L":79008, "XL":79009, "2XL":79010, "3XL":79146},
}

SIZES = ["S", "M", "L", "XL", "2XL", "3XL"]

# Build flat list of all variant IDs
ALL_VARIANT_IDS = []
VARIANTS_PAYLOAD = []
for color, sizes in VARIANT_MAP.items():
    for size in SIZES:
        vid = sizes.get(size)
        if vid:
            ALL_VARIANT_IDS.append(vid)
            VARIANTS_PAYLOAD.append({
                "id": vid,
                "price": RETAIL_PRICE,
                "is_enabled": True,
            })

print(f"Configured {len(VARIANT_MAP)} colors × {len(SIZES)} sizes = {len(ALL_VARIANT_IDS)} variants")
print(f"Colors: {', '.join(VARIANT_MAP.keys())}")
print(f"Retail price: £{RETAIL_PRICE/100:.2f}")

# ── Load catalogue CSV for design images ─────────────────────────────────────
CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "scraper", "catalogue.csv")
catalogue = {}
with open(CSV_PATH, encoding="utf-8-sig") as f:
    for row in csv.DictReader(f):
        img1 = row.get("IMAGE1_URL", "").strip()
        if not img1:
            continue
        title = row.get("TITLE", "").split(",")[0].strip()
        if title:
            catalogue[title.lower()] = img1

print(f"Loaded {len(catalogue)} design images from CSV\n")

# ── Checkpoint helpers ────────────────────────────────────────────────────────
def load_cp():
    if os.path.exists(CHECKPOINT):
        return json.load(open(CHECKPOINT, encoding="utf-8"))
    return {}

def save_cp(data):
    with open(CHECKPOINT, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

# ── Shopify helpers ───────────────────────────────────────────────────────────
def sh_get(path, params=None):
    for _ in range(3):
        r = httpx.get(f"{SAPI}{path}", headers=SHR, params=params, timeout=30)
        if r.status_code == 429:
            time.sleep(float(r.headers.get("Retry-After", 2)))
            continue
        return r
    return r

def sh_post(path, body):
    for _ in range(3):
        r = httpx.post(f"{SAPI}{path}", headers=SH, json=body, timeout=30)
        if r.status_code == 429:
            time.sleep(float(r.headers.get("Retry-After", 2)))
            continue
        return r
    return r

def sh_put(path, body):
    for _ in range(3):
        r = httpx.put(f"{SAPI}{path}", headers=SH, json=body, timeout=30)
        if r.status_code == 429:
            time.sleep(float(r.headers.get("Retry-After", 2)))
            continue
        return r
    return r

def sh_delete(path):
    for _ in range(3):
        r = httpx.delete(f"{SAPI}{path}", headers=SHR, timeout=30)
        if r.status_code == 429:
            time.sleep(float(r.headers.get("Retry-After", 2)))
            continue
        return r
    return r

# ── Printify helpers ──────────────────────────────────────────────────────────
def p_post(path, body):
    for _ in range(4):
        r = httpx.post(f"{PAPI}{path}", headers=PH, json=body, timeout=60)
        if r.status_code == 429:
            time.sleep(15)
            continue
        return r
    return r

def p_get(path):
    for _ in range(3):
        r = httpx.get(f"{PAPI}{path}", headers=PH, timeout=30)
        if r.status_code == 429:
            time.sleep(10)
            continue
        return r
    return r

# ── Upload design image to Printify ──────────────────────────────────────────
def upload_image(img_url, fname):
    r = p_post("/uploads/images.json", {"file_name": fname, "url": img_url})
    if r.status_code not in (200, 201):
        raise Exception(f"Image upload failed {r.status_code}: {r.text[:200]}")
    return r.json()["id"]

# ── Create CC1717 product on Printify ────────────────────────────────────────
def create_cc_product(title, description, image_id, tags=""):
    body = {
        "title": title,
        "description": description or "",
        "blueprint_id": BLUEPRINT_ID,
        "print_provider_id": PROVIDER_ID,
        "variants": VARIANTS_PAYLOAD,
        "print_areas": [{
            "variant_ids": ALL_VARIANT_IDS,
            "placeholders": [{
                "position": "front",
                "images": [{
                    "id": image_id,
                    "x": 0.5, "y": 0.5,
                    "scale": 1.0,
                    "angle": 0,
                }]
            }]
        }],
    }
    if tags:
        body["tags"] = [t.strip() for t in tags.split(",") if t.strip()][:10]
    r = p_post(f"/shops/{SHOP_ID}/products.json", body)
    if r.status_code not in (200, 201):
        raise Exception(f"Create product failed {r.status_code}: {r.text[:300]}")
    return r.json()["id"]

# ── Publish Printify product to Shopify ──────────────────────────────────────
def publish_product(pid):
    payload = {"title":True,"description":True,"images":True,
               "variants":True,"tags":True,"keyFeatures":True,"shipping_template":True}
    for attempt in range(6):
        r = p_post(f"/shops/{SHOP_ID}/products/{pid}/publish.json", payload)
        if r.status_code in (200, 201):
            return True
        if r.status_code == 429:
            wait = 70 + attempt * 30
            print(f"    429 — waiting {wait}s...")
            time.sleep(wait)
            continue
        raise Exception(f"Publish failed {r.status_code}: {r.text[:200]}")
    raise Exception("Publish failed after 6 retries")

# ── Wait for new Shopify product ID ──────────────────────────────────────────
def get_new_shopify_id(pid):
    time.sleep(15)
    for _ in range(15):
        r = p_get(f"/shops/{SHOP_ID}/products/{pid}.json")
        if r.status_code == 200:
            ext = r.json().get("external")
            if isinstance(ext, dict) and ext.get("id"):
                return str(ext["id"])
        time.sleep(5)
    return None

# ── Fetch all current Shopify products ───────────────────────────────────────
def fetch_shopify_products():
    products = []
    url = f"{SAPI}/products.json?limit=250&fields=id,title,body_html,handle,images,variants,tags,status"
    while url:
        r = httpx.get(url, headers=SHR, timeout=30)
        products.extend([p for p in r.json().get("products", []) if p.get("status") == "active"])
        link = r.headers.get("Link", "")
        url = None
        for part in link.split(","):
            if 'rel="next"' in part:
                url = part.strip().split(";")[0].strip("<> ")
    return products

# ── Get product collections ───────────────────────────────────────────────────
def get_collections(shopify_id):
    r = sh_get(f"/products/{shopify_id}/collects.json")
    if r.status_code != 200:
        return []
    return [c["collection_id"] for c in r.json().get("collects", [])]

# ── Add to collections ────────────────────────────────────────────────────────
def add_to_collections(new_sid, collection_ids):
    for cid in collection_ids:
        sh_post("/collects.json", {"collect": {"product_id": int(new_sid), "collection_id": cid}})
        time.sleep(0.2)

# ── Migrate handle and delete old ────────────────────────────────────────────
def migrate_and_delete(old_handle, new_sid, old_sid):
    sh_put(f"/products/{old_sid}.json",
           {"product": {"id": old_sid, "handle": f"{old_handle}-old-gildan"}})
    time.sleep(0.5)
    sh_put(f"/products/{new_sid}.json",
           {"product": {"id": int(new_sid), "handle": old_handle}})
    time.sleep(0.5)
    sh_post("/redirects.json", {"redirect": {
        "path": f"/products/{old_handle}-old-gildan",
        "target": f"/products/{old_handle}",
    }})
    time.sleep(0.3)
    sh_delete(f"/products/{old_sid}.json")

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry",   action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--reset", action="store_true")
    args = ap.parse_args()

    if args.reset and os.path.exists(CHECKPOINT):
        os.remove(CHECKPOINT)
        print("Checkpoint cleared.")

    cp = load_cp()

    print("Fetching Shopify products...")
    products = fetch_shopify_products()
    print(f"Found {len(products)} active products\n")

    # Deduplicate by title — keep first occurrence (lowest ID = older, safer to keep)
    seen_titles = {}
    deduped = []
    for p in products:
        t = p["title"].strip().lower()
        if t not in seen_titles:
            seen_titles[t] = p["id"]
            deduped.append(p)
        else:
            print(f"  [DEDUP] Skipping duplicate: {p['title']} (id={p['id']}, keeping id={seen_titles[t]})")
    products = deduped
    print(f"After dedup: {len(products)} unique products\n")

    if args.limit:
        products = products[:args.limit]

    if args.dry:
        print("[DRY RUN] Would migrate:")
        for p in products:
            sid = str(p["id"])
            status = "SKIP (done)" if cp.get(sid, {}).get("status") == "done" else "MIGRATE"
            img = catalogue.get(p["title"].lower(), "NO CSV MATCH — use current image")
            img_short = img[:60] if img else "none"
            print(f"  [{status}] {p['title'][:50]}  img={img_short}")
        return

    total = len(products)
    ok = fail = skip = 0

    for i, product in enumerate(products, 1):
        sid    = str(product["id"])
        title  = product["title"]
        handle = product["handle"]
        desc   = product.get("body_html", "") or ""
        tags   = product.get("tags", "")

        print(f"\n[{i}/{total}] {title[:55]}")

        # Skip already done
        if cp.get(sid, {}).get("status") == "done":
            print(f"  SKIP (already migrated to CC)")
            skip += 1
            continue

        # Find design image — prefer CSV, fall back to current Shopify image
        img_url = catalogue.get(title.lower())
        if img_url:
            print(f"  Using CSV design image")
        elif product.get("images"):
            img_url = product["images"][0]["src"]
            print(f"  Using current Shopify image (no CSV match)")
        else:
            print(f"  SKIP — no image available")
            cp[sid] = {"status": "no_image", "title": title}
            save_cp(cp)
            skip += 1
            continue

        img_name = img_url.split("/")[-1].split("?")[0] or "design.jpg"
        if not img_name.endswith((".jpg", ".jpeg", ".png")):
            img_name += ".jpg"

        try:
            # Add "Comfort Colors" to description if not already there
            cc_note = (
                '<p><strong>Premium Comfort Colors® 1717 Garment-Dyed Tee</strong> — '
                '100% ring-spun cotton, garment-dyed for a soft, lived-in feel. '
                'Heavyweight 6.1 oz fabric. Available in 15 premium colours. '
                'Free worldwide shipping.</p>'
            )
            if "comfort colors" not in desc.lower():
                desc = cc_note + "\n" + desc

            # 1. Upload design image
            image_id = cp.get(sid, {}).get("image_id")
            if not image_id:
                print(f"  Uploading design image...")
                image_id = upload_image(img_url, img_name)
                cp[sid] = {**cp.get(sid, {}), "image_id": image_id, "title": title}
                save_cp(cp)

            # 2. Create CC product on Printify
            pp_id = cp.get(sid, {}).get("printify_id")
            if not pp_id:
                print(f"  Creating Comfort Colors product on Printify...")
                pp_id = create_cc_product(title, desc, image_id, tags)
                cp[sid] = {**cp.get(sid, {}), "printify_id": pp_id}
                save_cp(cp)
                print(f"  Printify product: {pp_id}")

            # 3. Publish to Shopify
            print(f"  Publishing to Shopify...")
            publish_product(pp_id)

            # 4. Wait for new Shopify ID
            new_sid = get_new_shopify_id(pp_id)
            if not new_sid:
                raise Exception("Could not get new Shopify product ID after publish")
            print(f"  New Shopify ID: {new_sid}")

            # 5. Migrate collections
            collection_ids = get_collections(sid)
            if collection_ids:
                add_to_collections(new_sid, collection_ids)
                print(f"  Added to {len(collection_ids)} collections")

            # 6. Fix handle and delete old
            migrate_and_delete(handle, new_sid, int(sid))
            print(f"  Old product deleted, handle migrated")

            cp[sid] = {
                "status": "done",
                "title": title,
                "image_id": image_id,
                "printify_id": pp_id,
                "new_shopify_id": new_sid,
            }
            save_cp(cp)
            print(f"  DONE ✓")
            ok += 1

        except Exception as e:
            print(f"  ERROR: {e}")
            cp[sid] = {**cp.get(sid, {}), "status": "error", "error": str(e)[:200], "title": title}
            save_cp(cp)
            fail += 1

        # Rate limit pause between products
        if i < total:
            print(f"  Waiting 65s...")
            time.sleep(65)

    print(f"\n{'='*50}")
    print(f"Done: {ok} migrated, {skip} skipped, {fail} errors")

if __name__ == "__main__":
    main()
