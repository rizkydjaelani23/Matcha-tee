"""
Distribute unmatched Etsy reviews randomly across all uploaded products.

Run order: 2b (after upload_reviews.py, before or after setup_reviews.py)

What it does:
  - Re-reads the CSV and collects reviews that didn't match any product
  - Randomly shuffles them and spreads them across all 95 products
  - Caps each product at MAX_TOTAL reviews total (matched + random)
  - Updates metafields on Shopify
"""
import csv, json, os, random, re, sys, time
import httpx
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

STORE = os.environ["SHOPIFY_STORE"]
H = {"X-Shopify-Access-Token": os.environ["SHOPIFY_TOKEN"], "Content-Type": "application/json"}
API   = f"https://{STORE}/admin/api/2025-01"
BASE  = os.path.dirname(os.path.abspath(__file__))

REVIEWS_CSV   = os.path.join(BASE, "..", "scraper", "etsy3_reviews_cleaned.csv")
PRODUCTS_FILE = os.path.join(BASE, "products_uploaded.json")

MAX_TOTAL = 20   # don't give any product more than this many reviews total
SEED      = 42   # reproducible shuffle


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
    prefix = 0
    for a, b in zip(rk, pk):
        if a == b:
            prefix += 1
        else:
            break
    sub = 12 if (len(rk) >= 10 and rk[:10] in pk) else (8 if len(rk) >= 6 and rk[:6] in pk else 0)
    return prefix + sub


def fetch_metafield(product_id):
    r = httpx.get(
        f"{API}/products/{product_id}/metafields.json",
        headers={k: v for k, v in H.items() if k != "Content-Type"},
        params={"namespace": "custom", "key": "etsy_reviews"},
        timeout=30,
    )
    mfs = r.json().get("metafields", [])
    if mfs:
        return json.loads(mfs[0]["value"]), mfs[0]["id"]
    return [], None


def set_metafield(product_id, reviews, metafield_id=None):
    payload = {
        "metafield": {
            "namespace": "custom",
            "key": "etsy_reviews",
            "type": "json",
            "value": json.dumps(reviews),
        }
    }
    if metafield_id:
        r = httpx.put(
            f"{API}/metafields/{metafield_id}.json",
            headers=H, json=payload, timeout=30,
        )
    else:
        r = httpx.post(
            f"{API}/products/{product_id}/metafields.json",
            headers=H, json=payload, timeout=30,
        )
    return r.status_code


def main():
    with open(PRODUCTS_FILE, encoding="utf-8") as f:
        product_map = {k: v for k, v in json.load(f).items() if v}
    product_titles = list(product_map.keys())
    print(f"Products: {len(product_titles)}")

    # ── load CSV and split into matched / unmatched ───────────────────────────
    with open(REVIEWS_CSV, encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        next(reader)
        raw_rows = list(reader)

    print(f"Reviews CSV: {len(raw_rows)} rows")

    unmatched = []
    for row in raw_rows:
        if len(row) < 6:
            continue
        reviewer   = (row[2].strip() if len(row) > 2 else "") or "Verified Buyer"
        rating_str = row[4].strip() if len(row) > 4 else ""
        text       = row[5].strip() if len(row) > 5 else ""
        date_raw   = row[1].strip() if len(row) > 1 else ""
        prod_raw   = row[8].strip() if len(row) > 8 else ""
        avatar     = row[0].strip() if len(row) > 0 else ""

        if not text or not prod_raw:
            continue

        # check if this review matched any product
        best_score = max((match_score(prod_raw, pt) for pt in product_titles), default=0)
        if best_score < 8:
            unmatched.append({
                "reviewer": reviewer[:40],
                "rating":   parse_rating(rating_str),
                "date":     parse_date(date_raw),
                "text":     text,
                "avatar":   avatar if "default_avatar" not in avatar else "",
            })

    print(f"Unmatched reviews to distribute: {len(unmatched)}")

    # ── shuffle and plan distribution ─────────────────────────────────────────
    rng = random.Random(SEED)
    rng.shuffle(unmatched)

    # figure out how many slots each product has left
    print("\nFetching current review counts from Shopify...")
    product_data = {}   # title -> {pid, current_reviews, metafield_id}
    for title, pid in product_map.items():
        existing, mfid = fetch_metafield(pid)
        slots = max(0, MAX_TOTAL - len(existing))
        product_data[title] = {"pid": pid, "existing": existing, "mfid": mfid, "slots": slots}
        time.sleep(0.4)

    total_slots = sum(v["slots"] for v in product_data.values())
    print(f"Total available slots across all products: {total_slots}")
    print(f"Unmatched reviews available: {len(unmatched)}")

    # distribute round-robin across products that still have room
    pool = list(unmatched)
    additions = {title: [] for title in product_data}

    i = 0
    for review in pool:
        if i >= total_slots:
            break
        # find next product with slots (cycle)
        for attempt in range(len(product_data)):
            title = product_titles[(i + attempt) % len(product_titles)]
            if product_data[title]["slots"] > 0:
                additions[title].append(review)
                product_data[title]["slots"] -= 1
                i += 1
                break

    added_count = sum(len(v) for v in additions.values())
    print(f"Reviews to add: {added_count} across {sum(1 for v in additions.values() if v)} products\n")

    # ── push updated metafields ────────────────────────────────────────────────
    ok = fail = skipped = 0
    for title, extra in additions.items():
        if not extra:
            skipped += 1
            continue
        d = product_data[title]
        merged = d["existing"] + extra
        # sort: highest rating first, then by date desc
        merged.sort(key=lambda x: (x["rating"], x.get("date", "")), reverse=True)

        status = set_metafield(d["pid"], merged, d["mfid"])
        if status in (200, 201):
            ok += 1
            print(f"  ✓ {title[:50]}  {len(d['existing'])} → {len(merged)} reviews")
        else:
            fail += 1
            print(f"  ✗ {title[:50]}  status={status}")
        time.sleep(0.5)

    print(f"\nDone — {ok} updated  {fail} failed  {skipped} unchanged")


if __name__ == "__main__":
    main()
