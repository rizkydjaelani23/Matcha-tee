"""
sync_color_images.py
====================
For each migrated product:
  1. Fetch Printify mockup images (UK_CC for Comfort Colors, UK_GD for Gildan)
  2. Map each mockup to its color via Printify variant data
  3. Pick one front-view mockup per color
  4. Upload to Shopify product images, assigning each to the matching color variants

Result: clicking a color swatch on the product page shows that exact colour's shirt.

Run:
  python sync_color_images.py --dry      # print what would be done
  python sync_color_images.py --limit 1  # test on 1 product
  python sync_color_images.py            # full run
"""
import argparse, json, os, re, sys, time
import httpx
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# ── API setup ─────────────────────────────────────────────────────────────────
STORE = os.environ["SHOPIFY_STORE"]
SHOP_TOKEN = os.environ["SHOPIFY_TOKEN"]
SH  = {"X-Shopify-Access-Token": SHOP_TOKEN, "Content-Type": "application/json"}
SHR = {"X-Shopify-Access-Token": SHOP_TOKEN}
SHAPI = f"https://{STORE}/admin/api/2025-01"

PRINTIFY_TOKEN = os.environ["PRINTIFY_TOKEN"]
PH = {"Authorization": f"Bearer {PRINTIFY_TOKEN}", "Content-Type": "application/json"}
PAPI = "https://api.printify.com/v1"
SHOP_ID = 27883571

BASE    = os.path.dirname(os.path.abspath(__file__))
CP_FILE = os.path.join(BASE, "full_checkpoint.json")
OUT_FILE = os.path.join(BASE, "sync_images_checkpoint.json")

# Which Printify product key to use per fabric type
FABRIC_TO_PKEY = {
    "comfort colors": "UK_CC",
    "gildan":         "UK_GD",
}


def p_get(path):
    for _ in range(5):
        r = httpx.get(f"{PAPI}{path}", headers=PH, timeout=60)
        if r.status_code == 429:
            time.sleep(float(r.headers.get("Retry-After", 30)))
            continue
        return r
    return r


def sh_get(url):
    for _ in range(4):
        r = httpx.get(url, headers=SHR, timeout=30)
        if r.status_code == 429:
            time.sleep(float(r.headers.get("Retry-After", 4)))
            continue
        return r
    return r


def sh_post(path, body):
    for _ in range(4):
        r = httpx.post(f"{SHAPI}{path}", headers=SH, json=body, timeout=30)
        if r.status_code == 429:
            time.sleep(float(r.headers.get("Retry-After", 4)))
            continue
        return r
    return r


def sh_delete(path):
    for _ in range(3):
        r = httpx.delete(f"{SHAPI}{path}", headers=SHR, timeout=30)
        if r.status_code == 429:
            time.sleep(float(r.headers.get("Retry-After", 4)))
            continue
        return r
    return r


def get_printify_color_images(ppid):
    """
    Returns dict: color_name (lowercase) → best front-view mockup src URL
    Uses Printify product's images array, mapped via variant color titles.
    """
    r = p_get(f"/shops/{SHOP_ID}/products/{ppid}.json")
    if r.status_code != 200:
        return None, f"Printify GET {r.status_code}"

    product = r.json()
    variants = product.get("variants", [])
    images   = product.get("images", [])

    # Build: printify_variant_id → color name
    vid_to_color = {}
    for v in variants:
        if not v.get("is_enabled", True):
            continue
        title = v.get("title", "")  # e.g. "Black / M" or "Heather Grey / XL"
        color = title.split(" / ")[0].strip()
        vid_to_color[v["id"]] = color

    # Build: color → list of (position, is_default, src)
    color_images = {}
    for img in images:
        vids = img.get("variant_ids", [])
        src  = img.get("src", "")
        pos  = img.get("position", "other")    # "front", "back", "other"
        if not src or not vids:
            continue
        # Get color from any linked variant
        color = None
        for vid in vids:
            if vid in vid_to_color:
                color = vid_to_color[vid].lower()
                break
        if not color:
            continue
        color_images.setdefault(color, []).append({
            "src": src,
            "position": pos,
            "is_default": img.get("is_default", False),
        })

    # Pick best image per color: prefer front+default, then front, then any
    best = {}
    for color, imgs in color_images.items():
        fronts   = [i for i in imgs if i["position"] == "front"]
        defaults = [i for i in fronts if i["is_default"]]
        chosen   = (defaults or fronts or imgs)[0]
        best[color] = chosen["src"]

    return best, None


def get_shopify_variants(shopify_pid):
    """Returns list of all variants with id, option1 (color), option2 (size), option3 (fabric)."""
    r = sh_get(f"{SHAPI}/products/{shopify_pid}/variants.json?limit=250")
    if r.status_code != 200:
        return None
    return r.json().get("variants", [])


def delete_all_shopify_images(shopify_pid):
    """Delete all current images on a Shopify product (we'll replace them)."""
    r = sh_get(f"{SHAPI}/products/{shopify_pid}/images.json")
    if r.status_code != 200:
        return
    for img in r.json().get("images", []):
        sh_delete(f"/products/{shopify_pid}/images/{img['id']}.json")
        time.sleep(0.15)


def upload_shopify_image(shopify_pid, src_url, variant_ids, position=1):
    body = {
        "image": {
            "src": src_url,
            "variant_ids": variant_ids,
            "position": position,
        }
    }
    r = sh_post(f"/products/{shopify_pid}/images.json", body)
    return r


def save_cp(cp):
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(cp, f, indent=2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry",   action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    cp_data = json.load(open(CP_FILE, encoding="utf-8"))
    done_cp = json.load(open(OUT_FILE, encoding="utf-8")) if os.path.exists(OUT_FILE) else {}

    # Unique products from checkpoint
    seen, products = set(), []
    for v in cp_data.values():
        if v.get("status") != "done":
            continue
        t = (v.get("title") or "").strip().lower()
        if t in seen:
            continue
        seen.add(t)
        products.append(v)

    print(f"Products to process: {len(products)}")
    if args.limit:
        products = products[:args.limit]

    total_ok = total_fail = total_skip = 0

    for i, entry in enumerate(products, 1):
        title      = entry.get("title", "")
        shopify_id = entry.get("new_shopify_id")
        pid_map    = entry.get("printify_ids", {})

        print(f"\n[{i}/{len(products)}] {title[:65]}")

        if done_cp.get(title, {}).get("status") == "done":
            print("  SKIP")
            total_skip += 1
            continue

        if not shopify_id:
            print("  ! No Shopify ID")
            total_fail += 1
            continue

        # ── 1. Get Shopify variants ──────────────────────────────────────────
        variants = get_shopify_variants(shopify_id)
        if not variants:
            print("  ! Could not fetch Shopify variants")
            total_fail += 1
            continue

        # Group Shopify variants: (color_lower, fabric_lower) → [variant_id, ...]
        shopify_map = {}
        for v in variants:
            color  = (v.get("option1") or "").strip().lower()
            fabric = (v.get("option3") or "").strip().lower()
            shopify_map.setdefault((color, fabric), []).append(v["id"])

        all_fabrics = set(k[1] for k in shopify_map)
        print(f"  Shopify variants: {len(variants)}  fabrics: {sorted(all_fabrics)}")

        # ── 2. Get Printify color→image maps ────────────────────────────────
        color_image_map = {}   # (color, fabric) → src_url
        for fabric_key, pkey in FABRIC_TO_PKEY.items():
            # Only process fabrics that actually exist on this product
            has_fabric = any(fabric_key in f for f in all_fabrics)
            if not has_fabric:
                continue
            ppid = pid_map.get(pkey)
            if not ppid:
                print(f"  ! No Printify ID for {pkey}")
                continue
            color_map, err = get_printify_color_images(ppid)
            if err:
                print(f"  ! Printify {pkey}: {err}")
                continue
            print(f"  Printify {pkey}: {len(color_map)} colors")
            for color, src in color_map.items():
                color_image_map[(color, fabric_key)] = src
            time.sleep(0.5)

        if not color_image_map:
            print("  ! No Printify color images found")
            total_fail += 1
            continue

        # ── 3. Match Shopify variants to Printify images ─────────────────────
        # Build list: (src_url, [shopify_variant_ids])
        uploads = []
        unmatched = []
        for (sh_color, sh_fabric), sh_vids in shopify_map.items():
            # Try exact fabric match first, then any fabric
            src = color_image_map.get((sh_color, sh_fabric))
            if not src:
                # Try with partial fabric match (e.g. "comfort colors" in "premium comfort colors")
                for (p_color, p_fabric), p_src in color_image_map.items():
                    if p_color == sh_color and (p_fabric in sh_fabric or sh_fabric in p_fabric):
                        src = p_src
                        break
            if not src:
                # Fallback: any image for this color regardless of fabric
                for (p_color, _), p_src in color_image_map.items():
                    if p_color == sh_color:
                        src = p_src
                        break
            if src:
                uploads.append((src, sh_vids, sh_color))
            else:
                unmatched.append(f"{sh_color}/{sh_fabric}")

        if unmatched:
            print(f"  ! Unmatched colors: {', '.join(unmatched[:8])}")

        print(f"  Uploading {len(uploads)} color images to Shopify...")

        if args.dry:
            for src, vids, color in uploads[:3]:
                print(f"    DRY: {color} → {src[:60]}  ({len(vids)} variants)")
            done_cp[title] = {"status": "done", "colors": len(uploads)}
            save_cp(done_cp)
            total_ok += 1
            continue

        # ── 4. Delete existing images and upload new ones ────────────────────
        delete_all_shopify_images(shopify_id)
        time.sleep(0.5)

        ok_imgs = fail_imgs = 0
        for pos, (src, sh_vids, color) in enumerate(uploads, 1):
            r = upload_shopify_image(shopify_id, src, sh_vids, position=pos)
            if r.status_code in (200, 201):
                ok_imgs += 1
            else:
                print(f"    ! {color}: {r.status_code} {r.text[:80]}")
                fail_imgs += 1
            time.sleep(0.3)

        print(f"  ✓ {ok_imgs} images uploaded, {fail_imgs} failed")
        done_cp[title] = {"status": "done" if fail_imgs == 0 else "partial",
                          "ok": ok_imgs, "fail": fail_imgs}
        save_cp(done_cp)
        if fail_imgs == 0:
            total_ok += 1
        else:
            total_fail += 1
        time.sleep(1)

    print(f"\n{'='*60}")
    print(f"Done: {total_ok}  Failed: {total_fail}  Skipped: {total_skip}")


if __name__ == "__main__":
    main()
