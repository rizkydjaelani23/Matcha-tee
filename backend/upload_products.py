"""
Upload checked products from catalogue to Shopify.

Run order: 1 of 3

Usage:
    python upload_products.py

Reads:
    scraper/matcha_tees_catalogue.xlsx  (INCLUDE = ✓ rows)
    scraper/catalogue.csv               (fallback, INCLUDE = YES rows)

Outputs:
    backend/products_uploaded.json  —  { "Clean Title": shopify_product_id }

Fully resumable — skip any title already in products_uploaded.json.
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
SCRAPER = os.path.join(BASE, "..", "scraper")

XLSX_PATH     = os.path.join(SCRAPER, "matcha_tees_catalogue.xlsx")
CSV_PATH      = os.path.join(SCRAPER, "catalogue.csv")
PROGRESS_FILE = os.path.join(BASE, "products_uploaded.json")

TARGET_PRICE  = "35.99"
SIZES         = ["S", "M", "L", "XL", "2XL", "3XL"]
INCLUDE_YES   = {"YES", "Y", "TRUE", "1", "✓"}


# ── helpers ───────────────────────────────────────────────────────────────────

def clean_title(raw):
    """First comma-segment, stripped, max 100 chars."""
    return raw.split(",")[0].strip()[:100]


def clean_description(raw, raw_title):
    text = raw

    # Extract real product details after boilerplate
    for split_at in ("***PRODUCT DETAILS***", "PRODUCT DETAILS"):
        if split_at in text:
            after = text[text.find(split_at) + len(split_at):].strip("* \n:")
            # Cut at next boilerplate block
            for end in ["***", "\n\n\n", "- - -"]:
                if end in after:
                    after = after[:after.find(end)]
            if len(after) > 40:
                text = after.strip()
                break
    else:
        # Strip front boilerplate
        for marker in ["**C H A N G E", "*COVID-19", "COVID-19"]:
            if marker in text:
                text = text[:text.find(marker)].strip()
        # If description is just the title repeated, discard it
        if text and text[:30] == raw_title[:30]:
            text = ""

    text = re.sub(r"\s+", " ", text).strip("* \n")

    if len(text) < 30:
        name = clean_title(raw_title)
        text = f"Printed to order on premium cotton. {name} — available in multiple sizes and colours."

    return (
        f"<p>{text[:700]}</p>"
        "<p><strong>Ships within 3–5 business days.</strong> "
        "Tracked delivery to the UK in 7–14 days.</p>"
    )


def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_progress(state):
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def load_catalogue():
    """Try xlsx (✓ rows) first, fall back to csv (YES rows)."""
    try:
        import openpyxl
        if os.path.exists(XLSX_PATH):
            wb = openpyxl.load_workbook(XLSX_PATH, read_only=True, data_only=True)
            ws = wb.active
            # Row 1 = instruction banner, Row 2 = headers, Row 3+ = data
            header_row = next(ws.iter_rows(min_row=2, max_row=2, values_only=True))
            headers = [str(c or "").strip() for c in header_row]
            rows = []
            for row in ws.iter_rows(min_row=3, values_only=True):
                d = {headers[i]: str(v or "").strip() for i, v in enumerate(row) if i < len(headers)}
                rows.append(d)
            wb.close()
            included = [r for r in rows if r.get("INCLUDE", "").strip().lower() in ("true", "1", "✓", "✔", "yes")]
            print(f"xlsx: {len(rows)} total, {len(included)} included")
            if included:
                return included
    except Exception as e:
        print(f"xlsx read failed ({e}), using csv")

    with open(CSV_PATH, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    included = [r for r in rows if r.get("INCLUDE", "").strip().upper() in INCLUDE_YES]
    print(f"csv: {len(rows)} total, {len(included)} included")
    return included


def create_product(title, body_html, tags, images):
    variants = [
        {"option1": s, "price": TARGET_PRICE, "requires_shipping": True, "taxable": True}
        for s in SIZES
    ]
    payload = {
        "product": {
            "title": title,
            "body_html": body_html,
            "vendor": "The Matcha Tee",
            "product_type": "T-Shirt",
            "tags": ", ".join(tags[:13]),
            "status": "active",
            "images": images,
            "options": [{"name": "Size", "values": SIZES}],
            "variants": variants,
        }
    }
    return httpx.post(f"{API}/products.json", headers=H, json=payload, timeout=30)


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    rows     = load_catalogue()
    progress = load_progress()
    print(f"Already uploaded: {sum(1 for v in progress.values() if v)} products\n")

    created = skipped = failed = 0

    for i, row in enumerate(rows, 1):
        raw_title = row.get("TITLE", "").strip()
        if not raw_title:
            continue

        title = clean_title(raw_title)

        if title in progress:
            skipped += 1
            continue

        body_html = clean_description(row.get("DESCRIPTION", ""), raw_title)
        tags = [
            t.replace("_", " ").strip()
            for t in row.get("TAGS", "").split(",")
            if t.strip()
        ]
        images = [
            {"src": url}
            for col in ("IMAGE1_URL", "IMAGE2_URL", "IMAGE3_URL")
            for url in [row.get(col, "").strip()]
            if url
        ]

        # Retry loop for rate limiting
        for attempt in range(3):
            r = create_product(title, body_html, tags, images)
            if r.status_code == 429:
                wait = int(r.headers.get("Retry-After", 10))
                print(f"  Rate limited — sleeping {wait}s")
                time.sleep(wait)
                continue
            break

        if r.status_code in (200, 201):
            pid = r.json()["product"]["id"]
            progress[title] = pid
            save_progress(progress)
            created += 1
            print(f"[{i}/{len(rows)}] ✓ {title}  (id {pid})")
        elif r.status_code == 422:
            err = r.json().get("errors", {})
            print(f"[{i}/{len(rows)}] 422 {title}: {err}")
            progress[title] = None  # mark attempted
            save_progress(progress)
            failed += 1
        else:
            print(f"[{i}/{len(rows)}] ERR {r.status_code}: {r.text[:200]}")
            failed += 1

        time.sleep(0.6)  # stay under 2 req/s REST limit

        if i % 50 == 0:
            print(f"  — checkpoint: {created} created, {failed} failed, {skipped} skipped")

    print(f"\nFinished — {created} created  {failed} failed  {skipped} skipped")
    print(f"IDs saved → {PROGRESS_FILE}")


if __name__ == "__main__":
    main()
