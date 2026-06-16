"""
reupload_designs.py
====================
For each product in the checkpoint:
  1. Load the extracted design PNG from backend/designs/
  2. Upload it to Printify's image hosting (base64)
  3. GET each of the 6 Printify draft products to read current print_areas
  4. PUT updated print_areas with new image_id (x=0.5, y=0.5, scale=1.0)

Idempotent: uses reupload_checkpoint.json to skip already-done products.

Run:
  python reupload_designs.py            # full run
  python reupload_designs.py --dry      # print what would be done, no API calls
  python reupload_designs.py --limit 1  # test on 1 product
"""
import argparse, base64, json, os, re, sys, time
import httpx
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

PRINTIFY_TOKEN = os.environ["PRINTIFY_TOKEN"]
SHOP_ID        = 27883571
PH             = {"Authorization": f"Bearer {PRINTIFY_TOKEN}", "Content-Type": "application/json"}
PAPI           = "https://api.printify.com/v1"

BASE        = os.path.dirname(os.path.abspath(__file__))
DESIGNS_DIR = os.path.join(BASE, "designs")
CP_FILE     = os.path.join(BASE, "full_checkpoint.json")
RCP_FILE    = os.path.join(BASE, "reupload_checkpoint.json")

PKEYS = ["UK_CC", "UK_GD", "US_CC", "US_GD", "EU_CC", "EU_GD"]


def p_get(path):
    for _ in range(5):
        r = httpx.get(f"{PAPI}{path}", headers=PH, timeout=60)
        if r.status_code == 429:
            time.sleep(float(r.headers.get("Retry-After", 30)))
            continue
        return r
    return r


def p_post(path, body):
    for _ in range(5):
        r = httpx.post(f"{PAPI}{path}", headers=PH, json=body, timeout=120)
        if r.status_code == 429:
            time.sleep(float(r.headers.get("Retry-After", 30)))
            continue
        return r
    return r


def p_put(path, body):
    for _ in range(5):
        r = httpx.put(f"{PAPI}{path}", headers=PH, json=body, timeout=120)
        if r.status_code == 429:
            time.sleep(float(r.headers.get("Retry-After", 30)))
            continue
        return r
    return r


def upload_png(png_path, fname):
    with open(png_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    r = p_post("/uploads/images.json", {"file_name": fname, "contents": b64})
    if r.status_code not in (200, 201):
        raise Exception(f"Upload failed {r.status_code}: {r.text[:200]}")
    return r.json()["id"]


def update_printify_product(ppid, new_image_id, dry=False):
    r = p_get(f"/shops/{SHOP_ID}/products/{ppid}.json")
    if r.status_code == 404:
        return "not_found"
    if r.status_code != 200:
        return f"get_err:{r.status_code}"

    product = r.json()
    print_areas = product.get("print_areas", [])
    if not print_areas:
        return "no_print_areas"

    updated = []
    for area in print_areas:
        placeholders = []
        for ph in area.get("placeholders", []):
            pos            = ph.get("position", "")
            existing_imgs  = ph.get("images", [])
            if pos == "front":
                # Replace with our extracted design, centred, filling print area
                placeholders.append({
                    "position": "front",
                    "images": [{"id": new_image_id, "x": 0.5, "y": 0.5, "scale": 1.0, "angle": 0}]
                })
            elif existing_imgs:
                # Keep original image on back/sleeves — Printify rejects empty images[]
                placeholders.append({"position": pos, "images": existing_imgs})
            # Positions that were already empty (no images) are simply omitted
        updated.append({"variant_ids": area.get("variant_ids", []), "placeholders": placeholders})

    if dry:
        return "dry_ok"

    r2 = p_put(f"/shops/{SHOP_ID}/products/{ppid}.json", {"print_areas": updated})
    if r2.status_code in (200, 201):
        return "ok"
    return f"put_err:{r2.status_code}"


def slug(title):
    return re.sub(r"[^a-z0-9]+", "-", (title or "").lower()).strip("-")


def find_png(title, handle):
    # Exact handle match
    p = os.path.join(DESIGNS_DIR, f"{handle}.png")
    if os.path.exists(p):
        return p
    # Prefix match on filename
    key = re.sub(r"[^a-z0-9]", "", (title or "").lower())[:15]
    for f in os.listdir(DESIGNS_DIR):
        if f.endswith(".png") and re.sub(r"[^a-z0-9]", "", f[:-4].lower()).startswith(key):
            return os.path.join(DESIGNS_DIR, f)
    return None


def save_rcp(rcp):
    with open(RCP_FILE, "w", encoding="utf-8") as f:
        json.dump(rcp, f, indent=2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry",   action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    cp  = json.load(open(CP_FILE, encoding="utf-8"))
    rcp = json.load(open(RCP_FILE, encoding="utf-8")) if os.path.exists(RCP_FILE) else {}

    # One entry per unique title (skip duplicates)
    seen, products = set(), []
    for v in cp.values():
        if v.get("status") != "done":
            continue
        t = (v.get("title") or "").strip().lower()
        if t in seen:
            continue
        seen.add(t)
        products.append(v)

    print(f"Unique products: {len(products)}")
    if args.limit:
        products = products[:args.limit]

    done = skip = fail = 0

    for i, entry in enumerate(products, 1):
        title   = entry.get("title", "")
        pid_map = entry.get("printify_ids", {})
        handle  = slug(title)

        print(f"\n[{i}/{len(products)}] {title[:62]}")

        if rcp.get(title, {}).get("status") == "done":
            print("  SKIP")
            skip += 1
            continue

        png = find_png(title, handle)
        if not png:
            print("  ! No design PNG — run extract_designs.py first")
            rcp[title] = {"status": "no_png"}
            save_rcp(rcp)
            fail += 1
            continue

        size_kb = os.path.getsize(png) // 1024
        print(f"  Uploading {os.path.basename(png)} ({size_kb} KB)...")
        if args.dry:
            new_img_id = "DRY_ID"
        else:
            try:
                new_img_id = upload_png(png, os.path.basename(png))
                print(f"  → image_id: {new_img_id}")
            except Exception as e:
                print(f"  ! Upload error: {e}")
                rcp[title] = {"status": "upload_failed", "error": str(e)}
                save_rcp(rcp)
                fail += 1
                time.sleep(3)
                continue

        results = {}
        for pkey in PKEYS:
            ppid = pid_map.get(pkey)
            if not ppid:
                results[pkey] = "no_id"
                continue
            res = update_printify_product(ppid, new_img_id, dry=args.dry)
            results[pkey] = res
            if not args.dry:
                time.sleep(0.7)

        all_ok = all(v in ("ok", "dry_ok", "no_id", "not_found") for v in results.values())
        result_str = "  ".join(f"{k}:{v}" for k, v in results.items())
        if all_ok:
            print(f"  ✓  {result_str}")
            rcp[title] = {"status": "done", "image_id": new_img_id}
            done += 1
        else:
            print(f"  !  {result_str}")
            rcp[title] = {"status": "partial", "image_id": new_img_id, "results": results}
            fail += 1

        save_rcp(rcp)
        if not args.dry:
            time.sleep(1)

    print(f"\n{'='*60}")
    print(f"Done: {done}  Skipped: {skip}  Failed: {fail}")


if __name__ == "__main__":
    main()
