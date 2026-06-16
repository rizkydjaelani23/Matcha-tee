"""
extract_missing.py
For checkpoint products with no local IMAGE_FOLDER, download their Shopify
product image and run the same luminosity-to-alpha extraction on it.
"""
import json, os, re, sys, tempfile
import httpx, numpy as np
from PIL import Image, ImageFilter
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

STORE = os.environ["SHOPIFY_STORE"]
TOKEN = os.environ["SHOPIFY_TOKEN"]
HR  = {"X-Shopify-Access-Token": TOKEN}
API = f"https://{STORE}/admin/api/2025-01"

BASE        = os.path.dirname(os.path.abspath(__file__))
CP_FILE     = os.path.join(BASE, "full_checkpoint.json")
DESIGNS_DIR = os.path.join(BASE, "designs")

SHIRT_DARK_THRESHOLD = 42
OPAQUE_THRESHOLD     = 85
MIN_DIM = 2400


def slug(title):
    return re.sub(r"[^a-z0-9]+", "-", (title or "").lower()).strip("-")


def find_png(title):
    handle = slug(title)
    p = os.path.join(DESIGNS_DIR, f"{handle}.png")
    if os.path.exists(p):
        return p
    key = re.sub(r"[^a-z0-9]", "", (title or "").lower())[:15]
    for f in os.listdir(DESIGNS_DIR):
        if f.endswith(".png") and re.sub(r"[^a-z0-9]", "", f[:-4].lower()).startswith(key):
            return os.path.join(DESIGNS_DIR, f)
    return None


def extract_design(img_rgba):
    data = np.array(img_rgba, dtype=np.float32)
    r, g, b = data[:,:,0], data[:,:,1], data[:,:,2]
    white_bg = (r > 232) & (g > 232) & (b > 232)
    non_white = ~white_bg
    if not non_white.any():
        raise ValueError("Image appears all-white")

    rows_nw = np.any(non_white, axis=1)
    cols_nw = np.any(non_white, axis=0)
    rmin = int(np.where(rows_nw)[0][0])
    rmax = int(np.where(rows_nw)[0][-1])
    cmin = int(np.where(cols_nw)[0][0])
    cmax = int(np.where(cols_nw)[0][-1])

    sh = rmax - rmin
    sw = cmax - cmin

    dt = int(rmin + sh * 0.22)
    db = int(rmin + sh * 0.72)
    dl = int(cmin + sw * 0.22)
    dr = int(cmax - sw * 0.22)

    crop = data[dt:db, dl:dr].copy()
    ch, cw = crop.shape[:2]

    cr, cg, cb = crop[:,:,0], crop[:,:,1], crop[:,:,2]
    lum = cr * 0.299 + cg * 0.587 + cb * 0.114

    span  = float(OPAQUE_THRESHOLD - SHIRT_DARK_THRESHOLD)
    raw   = np.clip((lum - SHIRT_DARK_THRESHOLD) / span, 0.0, 1.0)
    alpha = np.power(raw, 0.45) * 255

    white_in_crop = (cr > 232) & (cg > 232) & (cb > 232)
    alpha[white_in_crop] = 0

    alpha_img = Image.fromarray(alpha.astype(np.uint8), "L")
    alpha_img = alpha_img.filter(ImageFilter.GaussianBlur(radius=1.5))
    alpha_arr = np.array(alpha_img, dtype=np.float32)

    Y, X = np.mgrid[0:ch, 0:cw]
    dy   = (Y - ch / 2) / (ch / 2)
    dx   = (X - cw / 2) / (cw / 2)
    dist = np.sqrt(dx**2 + dy**2)
    vign = np.clip((1.05 - dist) / (1.05 - 0.80), 0.0, 1.0)
    vign = np.power(vign, 0.55)
    alpha_arr = np.minimum(alpha_arr, vign * 255)

    crop[:,:,3] = alpha_arr
    result = Image.fromarray(crop.astype(np.uint8), "RGBA")

    bbox = result.getbbox()
    if bbox:
        result = result.crop(bbox)

    w, h = result.size
    if min(w, h) < MIN_DIM:
        scale = MIN_DIM / min(w, h)
        result = result.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    return result


cp = json.load(open(CP_FILE, encoding="utf-8"))
seen, products = set(), []
for v in cp.values():
    if v.get("status") != "done":
        continue
    t = (v.get("title") or "").strip().lower()
    if t in seen:
        continue
    seen.add(t)
    title = v.get("title", "")
    if not find_png(title):
        products.append(v)

print(f"Processing {len(products)} products with no local image...\n")
done = fail = 0

for i, entry in enumerate(products, 1):
    title  = entry.get("title", "")
    shopid = entry.get("new_shopify_id")
    handle = slug(title)
    out_path = os.path.join(DESIGNS_DIR, f"{handle}.png")

    print(f"[{i}/{len(products)}] {title[:65]}")

    if not shopid:
        print("  ! No Shopify ID in checkpoint")
        fail += 1
        continue

    # Get product images from Shopify
    r = httpx.get(f"{API}/products/{shopid}/images.json?limit=10", headers=HR, timeout=30)
    if r.status_code != 200:
        print(f"  ! Shopify {r.status_code}")
        fail += 1
        continue

    images = r.json().get("images", [])
    if not images:
        print("  ! No images on Shopify product")
        fail += 1
        continue

    # Try each image; prefer one that's dark/flat-lay (not lifestyle white)
    # The flat-lay is typically not the first image; try all until extraction succeeds
    extracted = None
    for img_info in images:
        src = img_info.get("src", "")
        try:
            resp = httpx.get(src, timeout=30, follow_redirects=True)
            resp.raise_for_status()
            img = Image.open(__import__("io").BytesIO(resp.content)).convert("RGBA")
            design = extract_design(img)
            w, h = design.size
            print(f"  ✓ from {os.path.basename(src)[:50]}  ({w}×{h}px)")
            design.save(out_path, "PNG")
            extracted = out_path
            break
        except Exception as e:
            print(f"  ~ {os.path.basename(src)[:40]}: {e}")
            continue

    if extracted:
        done += 1
    else:
        print(f"  ! All images failed for {title[:50]}")
        fail += 1

print(f"\nDone: {done}  Failed: {fail}")
