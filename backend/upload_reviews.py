"""
Parse Etsy reviews, match to uploaded products, store as metafields.

Run order: 2 of 3  (after upload_products.py)

Usage:
    python upload_reviews.py

Inputs:
    scraper/etsy3_reviews_cleaned.csv
    backend/products_uploaded.json

Outputs:
    Each matched product gets metafield custom.etsy_reviews (JSON array)
    backend/homepage_reviews.json  —  top 12 reviews for homepage section

CSV column layout (0-indexed):
    0  avatar_url
    1  date  e.g. "on Jun 9, 2026"
    2  reviewer name
    3  reviewer profile URL
    4  rating  e.g. "5 out of 5 stars"
    5  review text
    6  listing URL
    7  product image (small)
    8  product full title
"""
import csv
import json
import os
import re
import sys
import time

import httpx
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

STORE = os.environ["SHOPIFY_STORE"]
H = {
    "X-Shopify-Access-Token": os.environ["SHOPIFY_TOKEN"],
    "Content-Type": "application/json",
}
API = f"https://{STORE}/admin/api/2025-01"
BASE = os.path.dirname(os.path.abspath(__file__))

REVIEWS_CSV   = os.path.join(BASE, "..", "scraper", "etsy3_reviews_cleaned.csv")
PRODUCTS_FILE = os.path.join(BASE, "products_uploaded.json")
HOMEPAGE_OUT  = os.path.join(BASE, "homepage_reviews.json")


# ── helpers ───────────────────────────────────────────────────────────────────

def parse_rating(s):
    m = re.search(r"(\d+)\s*out\s*of", s or "")
    return int(m.group(1)) if m else 5


def parse_date(s):
    s = (s or "").replace("Inactive account ", "").replace("on ", "").strip()
    m = re.match(r"(\w+)\s+\d+,\s+(\d{4})", s)
    return f"{m.group(1)} {m.group(2)}" if m else s


def norm(text):
    return re.sub(r"[^a-z0-9]", "", (text or "").lower())


def match_score(review_title, prod_title):
    rk = norm(review_title.split(",")[0])
    pk = norm(prod_title)
    prefix = sum(1 for a, b in zip(rk, pk) if a == b and
                 all(rk[j] == pk[j] for j in range(len(rk[:rk.index(a)+1]))))
    # Simpler: count matching chars from start
    prefix = 0
    for a, b in zip(rk, pk):
        if a == b:
            prefix += 1
        else:
            break
    sub = 12 if (len(rk) >= 10 and rk[:10] in pk) else (8 if rk[:6] in pk else 0)
    return prefix + sub


def find_best_match(review_title, product_titles):
    best, best_score = None, 0
    for pt in product_titles:
        s = match_score(review_title, pt)
        if s > best_score:
            best_score, best = s, pt
    return best if best_score >= 8 else None


def set_metafield(product_id, reviews):
    payload = {
        "metafield": {
            "namespace": "custom",
            "key": "etsy_reviews",
            "type": "json",
            "value": json.dumps(reviews),
        }
    }
    r = httpx.post(
        f"{API}/products/{product_id}/metafields.json",
        headers=H, json=payload, timeout=30,
    )
    return r.status_code


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    if not os.path.exists(PRODUCTS_FILE):
        print(f"ERROR: {PRODUCTS_FILE} not found — run upload_products.py first")
        sys.exit(1)

    with open(PRODUCTS_FILE, encoding="utf-8") as f:
        product_map = {k: v for k, v in json.load(f).items() if v}

    product_titles = list(product_map.keys())
    print(f"Loaded {len(product_titles)} uploaded products")

    with open(REVIEWS_CSV, encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        next(reader)  # skip header row
        raw_rows = list(reader)

    print(f"Loaded {len(raw_rows)} raw reviews")

    reviews_by_product = {}
    unmatched = 0

    for row in raw_rows:
        if len(row) < 6:
            continue

        avatar     = row[0].strip() if len(row) > 0 else ""
        date_raw   = row[1].strip() if len(row) > 1 else ""
        reviewer   = (row[2].strip() if len(row) > 2 else "") or "Verified Buyer"
        rating_str = row[4].strip() if len(row) > 4 else ""
        text       = row[5].strip() if len(row) > 5 else ""
        prod_raw   = row[8].strip() if len(row) > 8 else ""

        if not text or not prod_raw:
            continue

        review = {
            "reviewer": reviewer[:40],
            "rating":   parse_rating(rating_str),
            "date":     parse_date(date_raw),
            "text":     text,
            # Only keep real avatars (not Etsy default placeholders)
            "avatar":   avatar if "default_avatar" not in avatar else "",
        }

        matched = find_best_match(prod_raw, product_titles)
        if matched:
            reviews_by_product.setdefault(matched, []).append(review)
        else:
            unmatched += 1

    print(f"Matched: {len(reviews_by_product)} products  |  Unmatched: {unmatched} reviews\n")

    ok = fail = 0
    for title, reviews in reviews_by_product.items():
        pid = product_map[title]
        status = set_metafield(pid, reviews)
        if status in (200, 201):
            ok += 1
            print(f"  ✓ {title[:55]}  ({len(reviews)} review{'s' if len(reviews) > 1 else ''})")
        else:
            fail += 1
            print(f"  ✗ {title[:55]}  status={status}")
        time.sleep(0.4)

    print(f"\nMetafields: {ok} set  {fail} failed")

    # Build homepage reviews — top 12 by rating then most recent
    all_flat = [
        {**rv, "product_title": title}
        for title, revs in reviews_by_product.items()
        for rv in revs
    ]
    all_flat.sort(key=lambda x: (x["rating"], x["date"]), reverse=True)
    top12 = all_flat[:12]

    with open(HOMEPAGE_OUT, "w", encoding="utf-8") as f:
        json.dump(top12, f, indent=2, ensure_ascii=False)

    print(f"\nHomepage reviews saved → {HOMEPAGE_OUT}  ({len(top12)} reviews)")
    print("Next: run setup_reviews.py")


if __name__ == "__main__":
    main()
