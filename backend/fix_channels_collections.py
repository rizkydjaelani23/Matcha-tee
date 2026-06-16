"""
fix_channels_collections.py
1. Shows count of products in each collection (from the collection side)
2. Publishes any products with scope != 'global' to all channels
3. Ensures every active product is in Homepage + correct type collection
4. Adds products to New Releases collection (all new migrated products)

Uses collection-side lookup (more reliable than product-side collects endpoint).
"""
import os, sys, time, httpx
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

STORE = os.environ["SHOPIFY_STORE"]
TOKEN = os.environ["SHOPIFY_TOKEN"]
H   = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}
HR  = {"X-Shopify-Access-Token": TOKEN}
API = f"https://{STORE}/admin/api/2025-01"

COLL_HOMEPAGE = 305611079793
COLL_TSHIRTS  = 305615667313
COLL_HOODIES  = 305615700081
COLL_NEWREL   = 305615601777
COLL_BEST     = 305615634545

COLL_NAMES = {
    COLL_HOMEPAGE: "Homepage",
    COLL_TSHIRTS:  "T-Shirts",
    COLL_HOODIES:  "Hoodies & Sweatshirts",
    COLL_NEWREL:   "New Releases",
    COLL_BEST:     "Best Sellers",
}

def sh_get(url):
    for _ in range(4):
        r = httpx.get(url, headers=HR, timeout=30)
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

def get_all_pages(url):
    items = []
    next_url = url
    while next_url:
        r = sh_get(next_url)
        data = r.json()
        # detect key name from URL
        if "products" in next_url:
            items.extend(data.get("products", []))
        elif "collects" in next_url:
            items.extend(data.get("collects", []))
        link = r.headers.get("Link", "")
        next_url = None
        for part in link.split(","):
            if 'rel="next"' in part:
                next_url = part.split("<")[1].split(">")[0]
                break
    return items

# ── Step 1: Build set of products already in each collection ──────────────────
print("Building collection membership map from collection side...\n")
coll_members = {}   # collection_id → set of product_ids
for cid, name in COLL_NAMES.items():
    collects = get_all_pages(f"{API}/collects.json?collection_id={cid}&limit=250")
    pids = {c["product_id"] for c in collects}
    coll_members[cid] = pids
    print(f"  {name}: {len(pids)} products")

# ── Step 2: Fetch all active products ─────────────────────────────────────────
print("\nFetching all active products...")
all_prods = get_all_pages(f"{API}/products.json?limit=250&status=active&fields=id,title,options,published_scope")
# only 3-option (Color/Size/Fabric) products are our migrated ones
migrated = [p for p in all_prods
            if [o["name"] for o in p.get("options", [])] == ["Color", "Size", "Fabric"]]
print(f"Total active: {len(all_prods)}  |  3-option migrated: {len(migrated)}\n")

# ── Step 3: Fix published_scope for any not on 'global' ──────────────────────
print("Checking published scope...")
scope_fixed = 0
for p in all_prods:
    if p.get("published_scope") != "global":
        r = sh_put(f"/products/{p['id']}.json",
                   {"product": {"id": p["id"], "published_scope": "global"}})
        if r.status_code == 200:
            print(f"  ✓ Fixed scope: {p['title'][:60]}")
            scope_fixed += 1
        else:
            print(f"  ! Failed scope fix {r.status_code}: {p['title'][:60]}")
        time.sleep(0.3)
if scope_fixed == 0:
    print("  All products already on global scope")

# ── Step 4: Ensure every migrated product is in correct collections ───────────
print("\nChecking and fixing collection assignments...")

added_homepage  = 0
added_type      = 0
added_newrel    = 0
already_ok      = 0
errors          = 0

def add_to_coll(pid, cid):
    if pid in coll_members.get(cid, set()):
        return "exists"
    r = sh_post("/collects.json", {"collect": {"product_id": pid, "collection_id": cid}})
    if r.status_code in (200, 201):
        coll_members.setdefault(cid, set()).add(pid)
        return "added"
    if r.status_code == 422 and "already exists" in r.text:
        coll_members.setdefault(cid, set()).add(pid)
        return "exists"
    return f"error:{r.status_code}"

for p in migrated:
    pid   = p["id"]
    title = p["title"]
    is_hoodie  = "sweatshirt" in title.lower() or "hoodie" in title.lower()
    type_coll  = COLL_HOODIES if is_hoodie else COLL_TSHIRTS
    type_label = "Hoodies" if is_hoodie else "T-Shirts"

    actions = []
    for cid, label, counter_attr in [
        (COLL_HOMEPAGE, "Homepage",      "homepage"),
        (type_coll,     type_label,      "type"),
        (COLL_NEWREL,   "New Releases",  "newrel"),
    ]:
        result = add_to_coll(pid, cid)
        if result == "added":
            actions.append(f"+{label}")
            if counter_attr == "homepage": added_homepage += 1
            elif counter_attr == "type":   added_type += 1
            else:                          added_newrel += 1
        elif result == "exists":
            pass
        else:
            actions.append(f"!{label}({result})")
            errors += 1
        time.sleep(0.2)

    if actions:
        print(f"  [{pid}] {title[:55]}  →  {', '.join(actions)}")
    else:
        already_ok += 1

print(f"\n{'='*60}")
print(f"Scope fixed        : {scope_fixed}")
print(f"Already correct    : {already_ok}")
print(f"Added to Homepage  : {added_homepage}")
print(f"Added to type coll : {added_type}")
print(f"Added to New Rel.  : {added_newrel}")
print(f"Errors             : {errors}")

# ── Step 5: Final count per collection ────────────────────────────────────────
print("\nFinal collection counts:")
for cid, name in COLL_NAMES.items():
    collects = get_all_pages(f"{API}/collects.json?collection_id={cid}&limit=250")
    print(f"  {name}: {len(collects)} products")
