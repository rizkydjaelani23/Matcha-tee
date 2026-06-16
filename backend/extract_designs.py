"""
extract_designs.py
==================
Extracts the print-ready design artwork from dark-shirt flat-lay product photos.

Technique: luminosity-to-alpha
- Black shirt pixels (dark) → transparent
- Design artwork pixels (brighter) → opaque / semi-opaque

Output: PNG files with transparent background in backend/designs/
Each file is named after the product handle from catalogue.csv.

Run:
  python extract_designs.py            # process all
  python extract_designs.py --test     # test on 1 product (Lalo) and open preview
"""
import argparse, csv, os, sys
import numpy as np
from PIL import Image, ImageFilter

sys.stdout.reconfigure(encoding="utf-8")

BASE      = os.path.dirname(os.path.abspath(__file__))
CSV_PATH  = os.path.join(BASE, "..", "scraper", "catalogue.csv")
OUT_DIR   = os.path.join(BASE, "designs")
os.makedirs(OUT_DIR, exist_ok=True)

# Luminosity thresholds — black shirt ≈ lum 20-40; design starts above ~50
SHIRT_DARK_THRESHOLD = 42   # pixels darker than this → fully transparent (pure shirt)
OPAQUE_THRESHOLD     = 85   # pixels brighter than this → fully opaque (clear design)
# Transition zone: 42-85  (narrow band keeps design elements solid, drops shirt bg)

# Minimum output dimension (upscale if smaller)
MIN_DIM = 2400   # px — Printify accepts 300+ DPI; at 8" print width = 2400px


def find_best_flatlay(folder):
    """Return path to the best flat-lay image in the folder.
    Prefer _2.jpg (dark shirt flat-lay). Fall back to _1.jpg."""
    if not folder or not os.path.isdir(folder):
        return None
    base = os.path.basename(folder)
    for suffix in ["_2.jpg", "_3.jpg", "_2.png", "_1.jpg"]:
        cand = os.path.join(folder, base + suffix)
        if os.path.exists(cand):
            return cand
    # fallback: first jpg found
    for f in sorted(os.listdir(folder)):
        if f.endswith((".jpg", ".jpeg", ".png")):
            return os.path.join(folder, f)
    return None


def remove_white_background(arr):
    """Set fully white or near-white pixels to alpha=0 (photo background)."""
    r, g, b = arr[:,:,0], arr[:,:,1], arr[:,:,2]
    white = (r > 235) & (g > 235) & (b > 235)
    arr[:,:,3][white] = 0
    return arr


def crop_shirt_region(img_rgba):
    """Crop out the shirt from the white-background product photo.
    Finds the bounding box of non-white pixels."""
    data = np.array(img_rgba)
    alpha = data[:,:,3]
    rows = np.any(alpha > 10, axis=1)
    cols = np.any(alpha > 10, axis=0)
    if not rows.any():
        return img_rgba
    rmin, rmax = np.where(rows)[0][[0, -1]]
    cmin, cmax = np.where(cols)[0][[0, -1]]
    # Small padding
    pad = 10
    rmin = max(0, rmin - pad)
    rmax = min(data.shape[0]-1, rmax + pad)
    cmin = max(0, cmin - pad)
    cmax = min(data.shape[1]-1, cmax + pad)
    cropped = Image.fromarray(data[rmin:rmax+1, cmin:cmax+1], 'RGBA')
    return cropped


def extract_design(flatlay_path):
    """
    Extract the design from a dark-shirt flat-lay photo.

    Algorithm:
    1. Find the shirt bounding box (non-white area of the product photo)
    2. Crop to the DESIGN AREA only (skip collar, sleeves, shirt hem)
    3. Apply luminosity-to-alpha on that crop:
       - Dark shirt background pixels → transparent
       - Design artwork pixels (brighter/more colourful) → opaque
    4. Final crop to bounding box + optional upscale

    Returns a PIL RGBA image with the design on transparent background.
    """
    img = Image.open(flatlay_path).convert("RGBA")
    data = np.array(img, dtype=np.float32)

    r = data[:,:,0]
    g = data[:,:,1]
    b = data[:,:,2]

    # ── Step 1: locate the shirt (non-white area of the photo) ────────────────
    white_bg = (r > 232) & (g > 232) & (b > 232)
    non_white = ~white_bg

    if not non_white.any():
        raise ValueError("No shirt found — image appears to be all-white")

    rows_nw = np.any(non_white, axis=1)
    cols_nw = np.any(non_white, axis=0)
    rmin, rmax = int(np.where(rows_nw)[0][[0, -1]].tolist()[0]), \
                 int(np.where(rows_nw)[0][[0, -1]].tolist()[1])
    cmin, cmax = int(np.where(cols_nw)[0][[0, -1]].tolist()[0]), \
                 int(np.where(cols_nw)[0][[0, -1]].tolist()[1])

    sh = rmax - rmin   # shirt height in pixels
    sw = cmax - cmin   # shirt width in pixels

    # ── Step 2: crop tightly to print / design area ───────────────────────────
    # Skip collar+shoulder (22% top), full sleeve area (22% each side), hem (28%)
    dt = int(rmin + sh * 0.22)    # below collar & shoulder
    db = int(rmin + sh * 0.72)    # above shirt hem
    dl = int(cmin + sw * 0.22)    # past left sleeve
    dr = int(cmax - sw * 0.22)    # past right sleeve

    crop = data[dt:db, dl:dr].copy()
    ch, cw = crop.shape[:2]

    # ── Step 3: luminosity → alpha on the crop ────────────────────────────────
    cr, cg, cb = crop[:,:,0], crop[:,:,1], crop[:,:,2]
    lum = cr * 0.299 + cg * 0.587 + cb * 0.114

    span  = float(OPAQUE_THRESHOLD - SHIRT_DARK_THRESHOLD)
    raw   = np.clip((lum - SHIRT_DARK_THRESHOLD) / span, 0.0, 1.0)
    alpha = np.power(raw, 0.45) * 255

    # White/near-white → transparent
    white_in_crop = (cr > 232) & (cg > 232) & (cb > 232)
    alpha[white_in_crop] = 0

    # Soft blur to smooth pixel-level noise at design boundary
    alpha_img = Image.fromarray(alpha.astype(np.uint8), 'L')
    alpha_img = alpha_img.filter(ImageFilter.GaussianBlur(radius=1.5))
    alpha_arr = np.array(alpha_img, dtype=np.float32)

    # ── Step 3b: fill interior holes so dark artwork stays opaque ─────────────
    # Dark elements inside the design (hair, shadows, outlines) look transparent
    # because their luminosity is low — same as the shirt background. But they
    # are ENCLOSED by brighter design pixels, forming "holes" in the mask.
    # Flood-filling from the image border marks only the exterior shirt background
    # as transparent; any hole fully surrounded by opaque design gets filled.
    try:
        from scipy.ndimage import binary_fill_holes
        mask   = alpha_arr > 64                  # True = opaque design pixel
        filled = binary_fill_holes(mask)         # True = opaque OR interior hole
        interior_holes = filled & ~mask          # pixels that were holes
        alpha_arr[interior_holes] = 230          # make them fully opaque
    except ImportError:
        # scipy not available — fall back to PIL flood-fill from all four corners
        from PIL import ImageDraw
        binary = Image.fromarray((alpha_arr > 64).astype(np.uint8) * 255, 'L')
        padded = Image.new('L', (cw + 2, ch + 2), 255)
        padded.paste(binary, (1, 1))
        draw = ImageDraw.Draw(padded)
        for corner in [(0, 0), (cw + 1, 0), (0, ch + 1), (cw + 1, ch + 1)]:
            ImageDraw.floodfill(padded, corner, 128)
        padded_arr = np.array(padded)[1:-1, 1:-1]
        interior_holes = (padded_arr != 128) & (alpha_arr <= 64)
        alpha_arr[interior_holes] = 230

    # ── Step 4: elliptical vignette — fades all edges to zero ─────────────────
    # Eliminates any residual shirt outline or hard crop border visible on
    # Printify mockups with different shirt poses / folded shirts
    Y, X = np.mgrid[0:ch, 0:cw]
    dy   = (Y - ch / 2) / (ch / 2)     # -1..1 vertically
    dx   = (X - cw / 2) / (cw / 2)     # -1..1 horizontally
    dist = np.sqrt(dx**2 + dy**2)
    # Full opacity inside r=0.80, fades to 0 at r=1.05
    vign = np.clip((1.05 - dist) / (1.05 - 0.80), 0.0, 1.0)
    vign = np.power(vign, 0.55)         # gentle falloff
    alpha_arr = np.minimum(alpha_arr, vign * 255)

    crop[:,:,3] = alpha_arr

    result = Image.fromarray(crop.astype(np.uint8), 'RGBA')

    # ── Step 5: tight crop to non-transparent bounding box ────────────────────
    bbox = result.getbbox()
    if bbox:
        result = result.crop(bbox)

    # ── Step 6: upscale if below minimum print resolution ─────────────────────
    w, h = result.size
    if min(w, h) < MIN_DIM:
        scale = MIN_DIM / min(w, h)
        result = result.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    return result


def handle_from_row(row):
    folder = row.get("IMAGE_FOLDER", "").strip()
    if folder:
        return os.path.basename(folder)
    title = row.get("TITLE", "").strip()
    import re
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true", help="Test on one product only")
    args = parser.parse_args()

    with open(CSV_PATH, encoding="utf-8-sig") as f:
        rows = [r for r in csv.DictReader(f) if r.get("INCLUDE","").strip().upper() == "YES"]

    print(f"Loaded {len(rows)} products from catalogue.csv")
    if args.test:
        # Pick lalo for test
        rows = [r for r in rows if "lalo" in r.get("TITLE","").lower()][:1]
        print(f"Test mode: {rows[0]['TITLE'][:60]}")

    done = skip = fail = 0
    for i, row in enumerate(rows, 1):
        handle   = handle_from_row(row)
        out_path = os.path.join(OUT_DIR, f"{handle}.png")
        title    = row.get("TITLE","")[:55]

        if os.path.exists(out_path) and not args.test:
            skip += 1
            continue

        folder   = row.get("IMAGE_FOLDER","").strip()
        flatlay  = find_best_flatlay(folder)
        if not flatlay:
            print(f"  [{i}] NO IMAGE: {title}")
            fail += 1
            continue

        try:
            design = extract_design(flatlay)
            design.save(out_path, "PNG")
            w, h = design.size
            src_file = os.path.basename(flatlay)
            print(f"  [{i}] ✓ {title}  ({w}×{h}px)  ← {src_file}")
            done += 1
        except Exception as e:
            print(f"  [{i}] ✗ {title}  ERROR: {e}")
            fail += 1

    print(f"\nDone: {done}  Skipped: {skip}  Failed: {fail}")
    print(f"Output folder: {OUT_DIR}")

    if args.test and done:
        import subprocess
        last_out = os.path.join(OUT_DIR, f"{handle_from_row(rows[0])}.png")
        print(f"\nOpening preview: {last_out}")
        subprocess.Popen(["explorer", last_out])


if __name__ == "__main__":
    main()
