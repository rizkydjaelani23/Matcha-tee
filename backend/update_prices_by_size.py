"""
Set per-variant prices based on actual COGS by size tier.
T-shirts:  S-2XL £27 | 3XL-5XL £29
Hoodies:   S-XL  £37 | 2XL £40 | 3XL £42 | 4XL+ £44
Kids:      flat  £22 (no size uplift — sizes are small, COGS unchanged)
compare_at_price = price × 1.30 (rounded to 2dp)
"""
import os, sys, re, time
import httpx
from dotenv import load_dotenv
sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
STORE = os.environ["SHOPIFY_STORE"]
TOKEN = os.environ["SHOPIFY_TOKEN"]
RH = {"X-Shopify-Access-Token": TOKEN}
H  = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}
API = f"https://{STORE}/admin/api/2025-01"

# ── size tier detection ───────────────────────────────────────────────────────
def size_tier(option_val):
    s = (option_val or "").upper().replace(" ", "").replace("-", "")
    if re.search(r'5XL|XXXXXL', s): return "5xl"
    if re.search(r'4XL|XXXXL',  s): return "4xl"
    if re.search(r'3XL|XXXL',   s): return "3xl"
    if re.search(r'2XL|XXL',    s): return "2xl"
    return "base"

# ── price tables: (price, compare_at) ────────────────────────────────────────
# compare = round(price * 1.30, 2)
PRICES = {
    "tee": {
        "base": ("27.00", "35.10"),
        "2xl":  ("27.00", "35.10"),   # same cost as S–XL for tees
        "3xl":  ("29.00", "37.70"),
        "4xl":  ("29.00", "37.70"),
        "5xl":  ("29.00", "37.70"),
    },
    "hoodie": {
        "base": ("37.00", "48.10"),
        "2xl":  ("40.00", "52.00"),
        "3xl":  ("42.00", "54.60"),
        "4xl":  ("44.00", "57.20"),
        "5xl":  ("44.00", "57.20"),
    },
    "kids": {
        "base": ("22.00", "28.60"),
        "2xl":  ("22.00", "28.60"),
        "3xl":  ("22.00", "28.60"),
        "4xl":  ("22.00", "28.60"),
        "5xl":  ("22.00", "28.60"),
    },
}

def categorize(title, ptype):
    t = title.lower(); p = (ptype or "").lower()
    if any(k in t or k in p for k in ["kid", "youth", "child", "toddler", "baby"]):
        return "kids"
    if any(k in t or k in p for k in ["hoodie", "hoody", "sweatshirt", "crewneck", "pullover"]):
        return "hoodie"
    return "tee"

# ── fetch all products ────────────────────────────────────────────────────────
products = []
url = f"{API}/products.json?limit=250"
while url:
    r = httpx.get(url, headers=RH, timeout=30)
    products.extend(r.json()["products"])
    link = r.headers.get("Link", "")
    url = None
    for part in link.split(","):
        if 'rel="next"' in part:
            url = part.strip().split(";")[0].strip("<> ")

print(f"Fetched {len(products)} products\n")

updated = 0
skipped = 0
failed = []
size_changes = {}   # tier -> count of variants changed

for p in products:
    cat = categorize(p["title"], p.get("product_type", ""))
    price_table = PRICES[cat]
    changed = False

    variants_payload = []
    for v in p["variants"]:
        tier = size_tier(v.get("option1", ""))
        price, compare = price_table[tier]

        current_price   = v.get("price", "")
        current_compare = v.get("compare_at_price", "") or ""

        if current_price != price or current_compare != compare:
            changed = True
            size_changes[tier] = size_changes.get(tier, 0) + 1

        variants_payload.append({
            "id": v["id"],
            "price": price,
            "compare_at_price": compare,
        })

    if not changed:
        skipped += 1
        continue

    r = httpx.put(
        f"{API}/products/{p['id']}.json",
        headers=H,
        json={"product": {"id": p["id"], "variants": variants_payload}},
        timeout=30,
    )
    if r.status_code not in (200, 201):
        failed.append(f"{p['title']}: HTTP {r.status_code}")
    else:
        updated += 1
        # show what changed per product
        tiers_in_product = {size_tier(v.get("option1","")) for v in p["variants"]}
        prices_shown = {tier: price_table[tier][0] for tier in sorted(tiers_in_product)}
        print(f"[{cat.upper():<6}] {p['title'][:55]}")
        print(f"         {prices_shown}")

    time.sleep(0.3)

print(f"""
══ DONE ═══════════════════════════════════════
Products updated  : {updated}
Products skipped  : {skipped} (prices already correct)
Variants changed by tier:""")
for tier in ["base", "2xl", "3xl", "4xl", "5xl"]:
    if tier in size_changes:
        print(f"  {tier:4s}: {size_changes[tier]} variants")
if failed:
    print(f"FAILED ({len(failed)}):")
    for f in failed:
        print(f"  {f}")
print("════════════════════════════════════════════")
