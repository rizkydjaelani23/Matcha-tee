"""
sync_main_images.py
===================
Sets the main product images on Shopify from the original Etsy flat-lay photos
(catalogue.csv), then re-attaches the Printify colour mockups with their variant_ids.

Result per product:
  - Image 1/2/3 = original flat-lay photos (no variant_ids, shown in main gallery)
  - Images 4+ = Printify colour mockups WITH variant_ids (shown on swatch click)

Run:
  python sync_main_images.py --dry --limit 2
  python sync_main_images.py
"""
import argparse, base64, csv, json, os, re, sys, time
import httpx
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

STORE = os.environ["SHOPIFY_STORE"]
TOKEN = os.environ["SHOPIFY_TOKEN"]
HR    = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}
API   = f"https://{STORE}/admin/api/2025-01"

BASE    = os.path.dirname(os.path.abspath(__file__))
CP_FILE = os.path.join(BASE, "full_checkpoint.json")
CAT_CSV = os.path.join(BASE, "../scraper/catalogue.csv")
RCP_FILE = os.path.join(BASE, "sync_main_checkpoint.json")


# ── helpers ────────────────────────────────────────────────────────────────

def norm(s):
    return re.sub(r'[^a-z0-9 ]', '', (s or '').lower().split(',')[0].strip())

def s_get(path, params=None):
    for _ in range(4):
        r = httpx.get(f"{API}{path}", headers=HR, params=params, timeout=25)
        if r.status_code == 429:
            time.sleep(float(r.headers.get("Retry-After", 10)))
            continue
        return r
    return r

def s_post(path, body):
    for _ in range(4):
        r = httpx.post(f"{API}{path}", headers=HR, json=body, timeout=60)
        if r.status_code == 429:
            time.sleep(float(r.headers.get("Retry-After", 10)))
            continue
        return r
    return r

def s_delete(path):
    for _ in range(4):
        r = httpx.delete(f"{API}{path}", headers=HR, timeout=25)
        if r.status_code == 429:
            time.sleep(float(r.headers.get("Retry-After", 10)))
            continue
        return r
    return r


def upload_image_local(pid, local_path, position, dry=False):
    if dry:
        return {"id": "DRY", "src": local_path}
    with open(local_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    ext = os.path.splitext(local_path)[1].lower().lstrip(".")
    mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}.get(ext, "image/jpeg")
    r = s_post(f"/products/{pid}/images.json", {
        "image": {
            "attachment": b64,
            "filename": os.path.basename(local_path),
            "position": position,
        }
    })
    if r.status_code in (200, 201):
        return r.json().get("image", {})
    print(f"    ! local upload failed {r.status_code}: {r.text[:100]}")
    return None


def upload_image_url(pid, src_url, position, dry=False):
    if dry:
        return {"id": "DRY", "src": src_url}
    r = s_post(f"/products/{pid}/images.json", {
        "image": {"src": src_url, "position": position}
    })
    if r.status_code in (200, 201):
        return r.json().get("image", {})
    print(f"    ! url upload failed {r.status_code}: {r.text[:100]}")
    return None


def upload_variant_image(pid, src_url, variant_ids, position, dry=False):
    if dry:
        return {"id": "DRY", "src": src_url}
    r = s_post(f"/products/{pid}/images.json", {
        "image": {"src": src_url, "variant_ids": variant_ids, "position": position}
    })
    if r.status_code in (200, 201):
        return r.json().get("image", {})
    print(f"    ! variant img upload failed {r.status_code}: {r.text[:100]}")
    return None


def load_catalogue():
    cat = {}
    with open(CAT_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            key = norm(row["TITLE"])
            if key not in cat:
                cat[key] = row
    return cat


def find_catalogue_row(title, cat):
    """Try exact norm match first, then keyword fallback."""
    n = norm(title)
    if n in cat:
        return cat[n]
    # Fallback: check if first 2 significant words appear in any key
    words = n.split()[:3]
    for key, row in cat.items():
        if all(w in key for w in words):
            return row
    # Broader: first word only
    if words:
        for key, row in cat.items():
            if words[0] in key:
                return row
    return None


def get_images_for_product(row):
    """Return list of (source, path_or_url) tuples, up to 3."""
    images = []
    for i in range(1, 4):
        local = row.get(f"IMAGE{i}_LOCAL", "")
        url   = row.get(f"IMAGE{i}_URL", "")
        if local and os.path.exists(local):
            images.append(("local", local))
        elif url:
            images.append(("url", url))
    return images


def save_rcp(rcp):
    with open(RCP_FILE, "w", encoding="utf-8") as f:
        json.dump(rcp, f, indent=2)


# ── main ───────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry",   action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    cp  = json.load(open(CP_FILE, encoding="utf-8"))
    rcp = json.load(open(RCP_FILE, encoding="utf-8")) if os.path.exists(RCP_FILE) else {}
    cat = load_catalogue()

    seen, products = set(), []
    for v in cp.values():
        if v.get("status") != "done" or not v.get("new_shopify_id"): continue
        t = (v.get("title") or "").strip().lower()
        if t in seen: continue
        seen.add(t)
        products.append(v)

    if args.limit:
        products = products[:args.limit]

    mode = "DRY RUN" if args.dry else "LIVE"
    print(f"[{mode}] Syncing main images for {len(products)} products\n")

    done = skip = fail = 0

    for i, entry in enumerate(products, 1):
        title = entry.get("title", "")
        pid   = entry["new_shopify_id"]
        label = f"[{i}/{len(products)}] {title[:55]}"

        if rcp.get(title, {}).get("status") == "done":
            print(f"{label} — SKIP")
            skip += 1
            continue

        # Find catalogue row
        row = find_catalogue_row(title, cat)
        if not row:
            print(f"{label} — NO CATALOGUE MATCH")
            rcp[title] = {"status": "no_match"}
            save_rcp(rcp)
            fail += 1
            continue

        main_imgs = get_images_for_product(row)
        if not main_imgs:
            print(f"{label} — NO IMAGES IN CATALOGUE")
            rcp[title] = {"status": "no_images"}
            save_rcp(rcp)
            fail += 1
            continue

        print(f"\n{label}")
        print(f"  Catalogue match: {row['TITLE'][:55]}")
        print(f"  Main images: {len(main_imgs)} ({main_imgs[0][0]})")

        # 1. Get current Shopify images — save colour variant images
        r = s_get(f"/products/{pid}/images.json", {"limit": 250})
        if r.status_code != 200:
            print(f"  ! GET images failed {r.status_code}")
            fail += 1
            continue

        current_imgs = r.json().get("images", [])
        variant_imgs = [
            {"src": img["src"], "variant_ids": img["variant_ids"]}
            for img in current_imgs
            if img.get("variant_ids")
        ]
        print(f"  Current: {len(current_imgs)} total, {len(variant_imgs)} with variant_ids")

        if args.dry:
            print(f"  → Would delete {len(current_imgs)}, upload {len(main_imgs)} main + {len(variant_imgs)} colour")
            done += 1
            continue

        # 2. Delete all current images
        for img in current_imgs:
            s_delete(f"/products/{pid}/images/{img['id']}")
            time.sleep(0.15)

        time.sleep(0.5)

        # 3. Upload main images (no variant_ids) — these become the gallery
        uploaded_main = 0
        for pos, (src_type, src_val) in enumerate(main_imgs, 1):
            if src_type == "local":
                img = upload_image_local(pid, src_val, pos)
            else:
                img = upload_image_url(pid, src_val, pos)
            if img:
                uploaded_main += 1
            time.sleep(0.4)

        # 4. Re-attach colour variant images WITH their variant_ids
        uploaded_colour = 0
        for j, vi in enumerate(variant_imgs, uploaded_main + 1):
            img = upload_variant_image(pid, vi["src"], vi["variant_ids"], j)
            if img:
                uploaded_colour += 1
            time.sleep(0.4)

        print(f"  ✓ Uploaded {uploaded_main} main + {uploaded_colour} colour images")
        rcp[title] = {"status": "done", "main": uploaded_main, "colour": uploaded_colour}
        save_rcp(rcp)
        done += 1
        time.sleep(0.5)

    print(f"\n{'='*60}")
    print(f"Done: {done}  Skipped: {skip}  Failed: {fail}")


if __name__ == "__main__":
    main()
