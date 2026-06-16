"""
remap_and_restore_reviews.py
1. Rebuilds products_uploaded.json with new Shopify product IDs
2. Re-runs upload_reviews.py logic to set metafields on new products
3. Re-runs distribute_reviews.py logic to fill gaps with unmatched reviews
"""
import csv, json, os, re, random, sys, time
import httpx
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

STORE = os.environ["SHOPIFY_STORE"]
TOKEN = os.environ["SHOPIFY_TOKEN"]
H    = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}
HR   = {"X-Shopify-Access-Token": TOKEN}
API  = f"https://{STORE}/admin/api/2025-01"
BASE = os.path.dirname(os.path.abspath(__file__))

REVIEWS_CSV   = os.path.join(BASE, "..", "scraper", "etsy3_reviews_cleaned.csv")
PRODUCTS_FILE = os.path.join(BASE, "products_uploaded.json")
CHECKPOINT    = os.path.join(BASE, "full_checkpoint.json")
HOMEPAGE_OUT  = os.path.join(BASE, "homepage_reviews.json")

MAX_TOTAL = 20
SEED      = 42


# ── helpers ───────────────────────────────────────────────────────────────────

def norm(text):
    return re.sub(r"[^a-z0-9]", "", (text or "").lower())

def parse_rating(s):
    m = re.search(r"(\d+)\s*out\s*of", s or "")
    return int(m.group(1)) if m else 5

def parse_date(s):
    s = (s or "").replace("Inactive account ", "").replace("on ", "").strip()
    m = re.match(r"(\w+)\s+\d+,\s+(\d{4})", s)
    return f"{m.group(1)} {m.group(2)}" if m else s

def match_score(review_title, prod_title):
    rk = norm(review_title.split(",")[0])
    pk = norm(prod_title)
    prefix = 0
    for a, b in zip(rk, pk):
        if a == b: prefix += 1
        else: break
    sub = 12 if (len(rk) >= 10 and rk[:10] in pk) else (8 if len(rk) >= 6 and rk[:6] in pk else 0)
    return prefix + sub

def sh_get(path):
    for _ in range(4):
        r = httpx.get(f"{API}{path}", headers=HR, timeout=30)
        if r.status_code == 429:
            time.sleep(float(r.headers.get("Retry-After", 4)))
            continue
        return r
    return r

def sh_post(path, body):
    for _ in range(4):
        r = httpx.post(f"{API}{path}", headers=H, json=body, timeout=30)
        if r.status_code == 429:
            time.sleep(float(r.headers.get("Retry-After", 4)))
            continue
        return r
    return r

def sh_put(path, body):
    for _ in range(4):
        r = httpx.put(f"{API}{path}", headers=H, json=body, timeout=30)
        if r.status_code == 429:
            time.sleep(float(r.headers.get("Retry-After", 4)))
            continue
        return r
    return r

def set_metafield(pid, reviews, mfid=None):
    payload = {"metafield": {"namespace": "custom", "key": "etsy_reviews",
                             "type": "json", "value": json.dumps(reviews)}}
    if mfid:
        r = sh_put(f"/metafields/{mfid}.json", payload)
    else:
        r = sh_post(f"/products/{pid}/metafields.json", payload)
    return r.status_code

def get_existing_metafield(pid):
    r = sh_get(f"/products/{pid}/metafields.json?namespace=custom&key=etsy_reviews")
    mfs = r.json().get("metafields", [])
    if mfs:
        return json.loads(mfs[0]["value"]), mfs[0]["id"]
    return [], None


# ── Step 1: Rebuild products_uploaded.json from checkpoint + live products ────
print("="*60)
print("STEP 1: Rebuild product ID map")
print("="*60)

cp = json.load(open(CHECKPOINT, encoding="utf-8"))
old_map = json.load(open(PRODUCTS_FILE, encoding="utf-8"))

# Build title → new_shopify_id from checkpoint (only done entries)
cp_title_map = {}
for v in cp.values():
    if v.get("status") == "done" and v.get("new_shopify_id") and v.get("title"):
        t = v["title"].strip()
        nid = v["new_shopify_id"]
        # keep the first occurrence (avoid overwriting with duplicate entries)
        if t not in cp_title_map:
            cp_title_map[t] = nid

print(f"Checkpoint has {len(cp_title_map)} done entries")

# Also fetch live products as fallback (handles title mismatches)
print("Fetching live Shopify products...")
live_map = {}   # title → id
next_url = f"{API}/products.json?limit=250&fields=id,title,options"
while next_url:
    r = httpx.get(next_url, headers=HR, timeout=30)
    for p in r.json().get("products", []):
        opt_names = [o["name"] for o in p.get("options", [])]
        if opt_names == ["Color", "Size", "Fabric"]:
            live_map[p["title"].strip()] = p["id"]
    link = r.headers.get("Link", "")
    next_url = None
    for part in link.split(","):
        if 'rel="next"' in part:
            next_url = part.split("<")[1].split(">")[0]
            break

print(f"Live 3-option products: {len(live_map)}")

# Rebuild products_uploaded.json
new_map = {}
remapped = 0
missing  = 0
for title, old_id in old_map.items():
    t = title.strip()
    if t in cp_title_map:
        new_map[t] = cp_title_map[t]
        remapped += 1
    elif t in live_map:
        new_map[t] = live_map[t]
        remapped += 1
    else:
        # fuzzy match against live products
        best, best_score = None, 0
        for lt in live_map:
            s = match_score(t, lt)
            if s > best_score:
                best_score, best = s, lt
        if best and best_score >= 8:
            new_map[t] = live_map[best]
            print(f"  Fuzzy: '{t[:40]}' → '{best[:40]}' (score {best_score})")
            remapped += 1
        else:
            # Keep old ID (product may have been removed from migration)
            new_map[t] = old_id
            print(f"  NOT FOUND: '{t[:50]}' (keeping old id {old_id})")
            missing += 1

# Also add any live products not in old_map
for lt, lid in live_map.items():
    if lt not in new_map:
        new_map[lt] = lid
        print(f"  NEW: '{lt[:50]}' (not in old map, adding)")

print(f"\nRemapped: {remapped}  Missing: {missing}  Total: {len(new_map)}")

# Save updated map
with open(PRODUCTS_FILE, "w", encoding="utf-8") as f:
    json.dump(new_map, f, indent=2, ensure_ascii=False)
print(f"Saved {PRODUCTS_FILE}")


# ── Step 2: Match reviews to products and set metafields ─────────────────────
print("\n" + "="*60)
print("STEP 2: Upload matched reviews")
print("="*60)

product_titles = list(new_map.keys())

with open(REVIEWS_CSV, encoding="utf-8-sig") as f:
    reader = csv.reader(f)
    next(reader)
    raw_rows = list(reader)

print(f"Reviews CSV: {len(raw_rows)} rows")

reviews_by_product = {}
unmatched_reviews  = []

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
        "avatar":   avatar if "default_avatar" not in avatar else "",
    }

    best, best_score = None, 0
    for pt in product_titles:
        s = match_score(prod_raw, pt)
        if s > best_score:
            best_score, best = s, pt

    if best and best_score >= 8:
        reviews_by_product.setdefault(best, []).append(review)
    else:
        unmatched_reviews.append(review)

print(f"Matched: {len(reviews_by_product)} products  |  Unmatched: {len(unmatched_reviews)} reviews")

ok = fail = 0
all_flat = []
for title, reviews in reviews_by_product.items():
    pid = new_map[title]
    status = set_metafield(pid, reviews)
    if status in (200, 201):
        ok += 1
        print(f"  ✓ {title[:55]}  ({len(reviews)} review{'s' if len(reviews)>1 else ''})")
        all_flat.extend({**r, "product_title": title} for r in reviews)
    else:
        fail += 1
        print(f"  ✗ {title[:55]}  status={status}")
    time.sleep(0.4)

print(f"\nMatched reviews — set: {ok}  failed: {fail}")


# ── Step 3: Distribute unmatched reviews ─────────────────────────────────────
print("\n" + "="*60)
print("STEP 3: Distribute unmatched reviews")
print("="*60)

print(f"Unmatched to distribute: {len(unmatched_reviews)}")

rng = random.Random(SEED)
rng.shuffle(unmatched_reviews)

print("Fetching current review counts...")
product_data = {}
for title, pid in new_map.items():
    existing, mfid = get_existing_metafield(pid)
    slots = max(0, MAX_TOTAL - len(existing))
    product_data[title] = {"pid": pid, "existing": existing, "mfid": mfid, "slots": slots}
    time.sleep(0.3)

total_slots = sum(v["slots"] for v in product_data.values())
print(f"Total slots: {total_slots}  |  Unmatched pool: {len(unmatched_reviews)}")

# Round-robin distribute
additions = {t: [] for t in product_data}
i = 0
for review in unmatched_reviews:
    if i >= total_slots:
        break
    for attempt in range(len(product_titles)):
        t = product_titles[(i + attempt) % len(product_titles)]
        if t in product_data and product_data[t]["slots"] > 0:
            additions[t].append(review)
            product_data[t]["slots"] -= 1
            i += 1
            break

added_count = sum(len(v) for v in additions.values())
print(f"Reviews to distribute: {added_count}\n")

ok2 = fail2 = skipped = 0
for title, extra in additions.items():
    if not extra:
        skipped += 1
        continue
    d = product_data[title]
    merged = d["existing"] + extra
    merged.sort(key=lambda x: (x["rating"], x.get("date", "")), reverse=True)
    status = set_metafield(d["pid"], merged, d["mfid"])
    if status in (200, 201):
        ok2 += 1
        print(f"  ✓ {title[:50]}  {len(d['existing'])} → {len(merged)}")
        all_flat.extend({**r, "product_title": title} for r in extra)
    else:
        fail2 += 1
        print(f"  ✗ {title[:50]}  status={status}")
    time.sleep(0.4)

print(f"\nDistributed — updated: {ok2}  failed: {fail2}  unchanged: {skipped}")


# ── Step 4: Rebuild homepage reviews ─────────────────────────────────────────
all_flat.sort(key=lambda x: (x["rating"], x.get("date", "")), reverse=True)
top12 = all_flat[:12]
with open(HOMEPAGE_OUT, "w", encoding="utf-8") as f:
    json.dump(top12, f, indent=2, ensure_ascii=False)
print(f"\nHomepage reviews → {HOMEPAGE_OUT}  ({len(top12)} reviews)")

print("\n" + "="*60)
print(f"DONE  —  {ok+ok2} products have reviews  {fail+fail2} errors")
print("="*60)
