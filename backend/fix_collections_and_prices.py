"""
fix_collections_and_prices.py
1. Assigns all migrated products to:
   - T-Shirts (305615667313)            — non-sweatshirt products
   - Hoodies & Sweatshirts (305615700081) — titles containing "sweatshirt"
   - Home page (305611079793)            — all products
2. Sets compare_at_price = price * 1.30, rounded up to nearest .99
   e.g. 29.99 -> 38.99 | 25.99 -> 33.99
"""
import os, sys, time, math, httpx
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

STORE = os.environ["SHOPIFY_STORE"]
TOKEN = os.environ["SHOPIFY_TOKEN"]
SH  = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}
SHR = {"X-Shopify-Access-Token": TOKEN}
API = f"https://{STORE}/admin/api/2025-01"

COLL_TSHIRTS  = 305615667313
COLL_HOODIES  = 305615700081
COLL_HOMEPAGE = 305611079793

def compare_at(price_str):
    """price * 1.30 rounded up to nearest X.99"""
    raw = float(price_str) * 1.30
    base = math.floor(raw)
    result = base + 0.99
    if result < raw:
        result += 1.0
    return f"{result:.2f}"

# Quick sanity check
assert compare_at("29.99") == "38.99", compare_at("29.99")
assert compare_at("25.99") == "33.99", compare_at("25.99")

def sh_get(url, **kw):
    for _ in range(4):
        r = httpx.get(url, headers=SHR, timeout=30, **kw)
        if r.status_code == 429:
            time.sleep(float(r.headers.get("Retry-After", 4)))
            continue
        return r
    return r

def sh_put(path, body):
    for _ in range(4):
        r = httpx.put(f"{API}{path}", headers=SH, json=body, timeout=30)
        if r.status_code == 429:
            time.sleep(float(r.headers.get("Retry-After", 4)))
            continue
        return r
    return r

def sh_post(path, body):
    for _ in range(4):
        r = httpx.post(f"{API}{path}", headers=SH, json=body, timeout=30)
        if r.status_code == 429:
            time.sleep(float(r.headers.get("Retry-After", 4)))
            continue
        return r
    return r

# ── Fetch all 3-option products ───────────────────────────────────────────────
print("Fetching products...")
products = []
next_url = f"{API}/products.json?limit=250&fields=id,title,options,variants"
while next_url:
    r = sh_get(next_url)
    for p in r.json().get("products", []):
        opt_names = [o["name"] for o in p.get("options", [])]
        if opt_names == ["Color", "Size", "Fabric"]:
            products.append(p)
    link = r.headers.get("Link", "")
    next_url = None
    for part in link.split(","):
        if 'rel="next"' in part:
            next_url = part.split("<")[1].split(">")[0]
            break

print(f"Found {len(products)} 3-option products\n")

done_colls = 0
done_prices = 0
errors = 0

for i, p in enumerate(products, 1):
    pid   = p["id"]
    title = p["title"]
    is_hoodie  = "sweatshirt" in title.lower() or "hoodie" in title.lower()
    type_coll  = COLL_HOODIES if is_hoodie else COLL_TSHIRTS
    type_label = "Hoodies & Sweatshirts" if is_hoodie else "T-Shirts"

    print(f"[{i}/{len(products)}] {title[:60]}")

    # ── 1. Current collection memberships ────────────────────────────────────
    r = sh_get(f"{API}/products/{pid}/collects.json")
    existing_cids = set()
    if r.status_code == 200:
        existing_cids = {c["collection_id"] for c in r.json().get("collects", [])}

    # ── 2. Add to Homepage + type collection if missing ───────────────────────
    for cid, label in [(COLL_HOMEPAGE, "Homepage"), (type_coll, type_label)]:
        if cid not in existing_cids:
            rr = sh_post("/collects.json", {"collect": {"product_id": pid, "collection_id": cid}})
            if rr.status_code in (200, 201):
                print(f"  + Added to {label}")
                done_colls += 1
            else:
                print(f"  ! Collection {label} failed {rr.status_code}: {rr.text[:80]}")
                errors += 1
            time.sleep(0.25)
        else:
            print(f"  = Already in {label}")

    # ── 3. Set compare_at_price on all variants ───────────────────────────────
    variants = p.get("variants", [])
    already_set = all(v.get("compare_at_price") not in (None, "") for v in variants)
    if already_set:
        print("  = compare_at_price already set")
    else:
        updated = [{"id": v["id"], "compare_at_price": compare_at(v["price"])} for v in variants]
        sample  = f"£{variants[0]['price']} → £{updated[0]['compare_at_price']}"
        r2 = sh_put(f"/products/{pid}.json",
                    {"product": {"id": pid, "variants": updated}})
        if r2.status_code == 200:
            print(f"  ✓ compare_at_price set ({sample}) on {len(updated)} variants")
            done_prices += 1
        else:
            print(f"  ! Price update failed {r2.status_code}: {r2.text[:120]}")
            errors += 1

    time.sleep(0.4)

print(f"\n{'='*50}")
print(f"Collections added  : {done_colls}")
print(f"Products price-set : {done_prices}")
print(f"Errors             : {errors}")
