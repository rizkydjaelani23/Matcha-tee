"""
Audit all active products — show collection membership, type, published scope.
"""
import os, sys, time, httpx
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

STORE = os.environ["SHOPIFY_STORE"]
TOKEN = os.environ["SHOPIFY_TOKEN"]
HR = {"X-Shopify-Access-Token": TOKEN}
H  = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}
API = f"https://{STORE}/admin/api/2025-01"

COLL_HOMEPAGE = 305611079793
COLL_TSHIRTS  = 305615667313
COLL_HOODIES  = 305615700081
COLL_NEWREL   = 305615601777
COLL_BEST     = 305615634545

COLL_NAMES = {
    COLL_HOMEPAGE: "Homepage",
    COLL_TSHIRTS:  "T-Shirts",
    COLL_HOODIES:  "Hoodies",
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

# Fetch ALL active products
print("Fetching all active products...")
products = []
next_url = f"{API}/products.json?limit=250&fields=id,title,options,status,published_scope,published_at"
while next_url:
    r = sh_get(next_url)
    batch = r.json().get("products", [])
    products.extend(batch)
    link = r.headers.get("Link", "")
    next_url = None
    for part in link.split(","):
        if 'rel="next"' in part:
            next_url = part.split("<")[1].split(">")[0]
            break

print(f"Total active products: {len(products)}\n")

# Check collection membership for each
no_homepage = []
no_type_coll = []
no_colls_at_all = []
unpublished = []
wrong_scope = []

for p in products:
    pid   = p["id"]
    title = p["title"]
    opts  = [o["name"] for o in p.get("options", [])]
    is_3opt = opts == ["Color", "Size", "Fabric"]
    is_hoodie = "sweatshirt" in title.lower() or "hoodie" in title.lower()
    expected_type = COLL_HOODIES if is_hoodie else COLL_TSHIRTS

    r = sh_get(f"{API}/products/{pid}/collects.json")
    cids = set()
    if r.status_code == 200:
        cids = {c["collection_id"] for c in r.json().get("collects", [])}
    time.sleep(0.25)

    if p.get("status") != "active":
        unpublished.append((pid, title, p.get("status")))
    if p.get("published_scope") != "global":
        wrong_scope.append((pid, title, p.get("published_scope")))
    if not cids:
        no_colls_at_all.append((pid, title, is_3opt))
    else:
        if COLL_HOMEPAGE not in cids:
            no_homepage.append((pid, title, cids))
        if is_3opt and expected_type not in cids:
            no_type_coll.append((pid, title, expected_type, cids))

print(f"Not active       : {len(unpublished)}")
print(f"Scope != global  : {len(wrong_scope)}")
print(f"No collections   : {len(no_colls_at_all)}")
print(f"Missing Homepage : {len(no_homepage)}")
print(f"Missing type coll: {len(no_type_coll)}")

if no_colls_at_all:
    print("\nProducts with NO collections:")
    for pid, title, is3 in no_colls_at_all:
        print(f"  [{pid}] {title[:60]}  3opt={is3}")

if wrong_scope:
    print("\nWrong scope:")
    for pid, title, scope in wrong_scope:
        print(f"  [{pid}] {title[:60]}  scope={scope}")
