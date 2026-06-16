"""
Set compare_at_price = price * 1.30 on every variant of all 95 products.
This makes each product show a crossed-out price ~30% above the sale price.
"""
import os, sys, json, time, math
import httpx
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

STORE = os.environ["SHOPIFY_STORE"]
TOKEN = os.environ["SHOPIFY_TOKEN"]
H     = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}
RH    = {"X-Shopify-Access-Token": TOKEN}
API   = f"https://{STORE}/admin/api/2025-01"

MARKUP = 1.30  # compare_at_price = price * 1.30

# Load product IDs
with open("products_uploaded.json", encoding="utf-8") as f:
    uploaded = json.load(f)  # {title: product_id}

product_ids = list(uploaded.values())
print(f"Products to update: {len(product_ids)}")

ok = 0
failed = 0

for i, pid in enumerate(product_ids, 1):
    # Fetch current variants
    r = httpx.get(f"{API}/products/{pid}.json", headers=RH, timeout=15)
    if r.status_code != 200:
        print(f"  [{i}] GET {pid} failed: {r.status_code}")
        failed += 1
        time.sleep(0.6)
        continue

    product = r.json()["product"]
    variants = product.get("variants", [])
    if not variants:
        print(f"  [{i}] {product['title'][:40]}: no variants, skipped")
        time.sleep(0.6)
        continue

    # Build updated variants with compare_at_price
    updated_variants = []
    for v in variants:
        price = float(v.get("price", 0) or 0)
        compare = round(price * MARKUP, 2)
        updated_variants.append({
            "id": v["id"],
            "price": f"{price:.2f}",
            "compare_at_price": f"{compare:.2f}",
        })

    # PUT updated variants
    payload = {"product": {"id": pid, "variants": updated_variants}}
    r2 = httpx.put(f"{API}/products/{pid}.json", headers=H, json=payload, timeout=30)

    if r2.status_code in (200, 201):
        sample_price = float(updated_variants[0]["price"])
        sample_compare = float(updated_variants[0]["compare_at_price"])
        print(f"  [{i:02d}] {product['title'][:45]:<45} {sample_price:.2f} → compare {sample_compare:.2f}  ({len(variants)} variants)")
        ok += 1
    else:
        print(f"  [{i:02d}] FAILED {product['title'][:40]}: {r2.status_code}  {r2.text[:100]}")
        failed += 1

    time.sleep(0.65)

print(f"\nDone. Updated: {ok}  Failed: {failed}")
