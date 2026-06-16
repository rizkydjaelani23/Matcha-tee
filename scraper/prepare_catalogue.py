"""
Reads the Etsy CSV export, builds a clean filter spreadsheet,
and downloads all product images.

Run once:
    python prepare_catalogue.py

Outputs:
    scraper/catalogue.csv          -- open this, set INCLUDE=YES for products you want
    scraper/images/<slug>/         -- downloaded images per product
"""

import csv
import os
import re
import sys
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.stdout.reconfigure(encoding="utf-8")

ETSY_CSV = r"C:\Users\rizky\Downloads\EtsyListingsDownload (1).csv"
BASE = os.path.dirname(os.path.abspath(__file__))
IMAGES_DIR = os.path.join(BASE, "images")
CATALOGUE_CSV = os.path.join(BASE, "catalogue.csv")
os.makedirs(IMAGES_DIR, exist_ok=True)

IMAGE_COLS = [f"IMAGE{i}" for i in range(1, 11)]
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text[:60]


def download_image(url, dest_path):
    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 1000:
        return True  # already downloaded
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=20) as resp, \
                open(dest_path, "wb") as out:
            out.write(resp.read())
        return True
    except Exception as e:
        return False


def usd_to_gbp(usd_str):
    """Rough USD→GBP conversion + retail markup for UK market."""
    try:
        usd = float(usd_str)
        gbp = usd * 0.79  # approximate rate
        # round to nearest .99
        return f"{(round(gbp) - 0.01):.2f}"
    except Exception:
        return usd_str


def parse_sizes(var1_type, var1_vals, var2_type, var2_vals):
    sizes, colors = [], []
    for vtype, vvals in [(var1_type, var1_vals), (var2_type, var2_vals)]:
        if not vvals:
            continue
        vals = [v.strip() for v in vvals.split(",") if v.strip()]
        vtype_low = vtype.lower()
        if any(k in vtype_low for k in ["size", "style"]):
            sizes = vals
        elif any(k in vtype_low for k in ["color", "colour"]):
            colors = vals
        else:
            # heuristic: if values contain S/M/L/XL they're sizes
            size_like = sum(1 for v in vals if re.search(r"\b(XS|S|M|L|XL|XXL|2XL|3XL)\b", v, re.I))
            if size_like >= 2:
                sizes = vals
            elif not colors:
                colors = vals
    return sizes, colors


def main():
    with open(ETSY_CSV, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    print(f"Loaded {len(rows)} products from Etsy CSV")

    # build catalogue rows
    catalogue = []
    download_tasks = []  # (url, dest_path)

    for row in rows:
        title = row.get("TITLE", "").strip()
        slug = slugify(title)
        img_folder = os.path.join(IMAGES_DIR, slug)
        os.makedirs(img_folder, exist_ok=True)

        # collect image URLs
        img_urls = [row.get(c, "").strip() for c in IMAGE_COLS if row.get(c, "").strip()]

        # queue downloads
        local_imgs = []
        for i, url in enumerate(img_urls):
            ext = ".jpg"
            dest = os.path.join(img_folder, f"{slug}_{i+1}{ext}")
            download_tasks.append((url, dest))
            local_imgs.append(dest)

        # parse sizes and colors
        sizes, colors = parse_sizes(
            row.get("VARIATION 1 TYPE", ""), row.get("VARIATION 1 VALUES", ""),
            row.get("VARIATION 2 TYPE", ""), row.get("VARIATION 2 VALUES", ""),
        )

        # price
        price_gbp = usd_to_gbp(row.get("PRICE", "0"))

        catalogue.append({
            "INCLUDE": "YES",
            "TITLE": title,
            "PRICE_GBP": price_gbp,
            "DESCRIPTION": row.get("DESCRIPTION", "").replace("\n", " ").strip()[:500],
            "SIZES": ", ".join(sizes),
            "COLORS": ", ".join(colors),
            "TAGS": row.get("TAGS", ""),
            "IMAGE_FOLDER": img_folder,
            "IMAGE1_LOCAL": local_imgs[0] if len(local_imgs) > 0 else "",
            "IMAGE2_LOCAL": local_imgs[1] if len(local_imgs) > 1 else "",
            "IMAGE3_LOCAL": local_imgs[2] if len(local_imgs) > 2 else "",
            "IMAGE1_URL": img_urls[0] if len(img_urls) > 0 else "",
            "IMAGE2_URL": img_urls[1] if len(img_urls) > 1 else "",
            "IMAGE3_URL": img_urls[2] if len(img_urls) > 2 else "",
        })

    # write catalogue CSV
    with open(CATALOGUE_CSV, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(catalogue[0].keys()))
        writer.writeheader()
        writer.writerows(catalogue)
    print(f"Catalogue written: {CATALOGUE_CSV}")

    # download images in parallel (8 threads)
    print(f"\nDownloading images ({len(download_tasks)} files across {len(rows)} products)...")
    done = 0
    failed = 0
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(download_image, url, dest): (url, dest)
                   for url, dest in download_tasks}
        for future in as_completed(futures):
            ok = future.result()
            done += 1
            if not ok:
                failed += 1
            if done % 100 == 0:
                print(f"  {done}/{len(download_tasks)} images "
                      f"({failed} failed so far)...")

    print(f"\nDone. {done - failed} images saved, {failed} failed.")
    print(f"\nNext step: open {CATALOGUE_CSV}")
    print("  → Set INCLUDE=NO for products you DON'T want on Shopify")
    print("  → Adjust PRICE_GBP, TITLE, DESCRIPTION as needed")
    print("  → Save and run upload_to_printify.py")


if __name__ == "__main__":
    main()
