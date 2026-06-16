"""Check all products for missing images and inspect a specific product."""
import httpx, os, sys
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

TOKEN = os.environ["SHOPIFY_TOKEN"]
STORE = os.environ["SHOPIFY_STORE"]
BASE  = f"https://{STORE}/admin/api/2025-01"
HR    = {"X-Shopify-Access-Token": TOKEN}

# ── 1. Check specific product ─────────────────────────────────────────────────
print("=== Jenna Marbles product ===")
r = httpx.get(f"{BASE}/products.json", headers=HR,
    params={"handle": "jenna-marbles-retro-t-shirt-jenna-marbles-homage-tees", "fields": "id,title,handle,images,status"}, timeout=20)
prods = r.json().get("products", [])
if prods:
    p = prods[0]
    print(f"  id={p['id']}  title={p['title']}")
    print(f"  status={p.get('status')}  images={len(p.get('images', []))}")
    for img in p.get("images", []):
        print(f"    src={img['src'][:100]}")
else:
    print("  Not found by handle, searching by title...")
    r2 = httpx.get(f"{BASE}/products.json", headers=HR,
        params={"title": "jenna marbles", "fields": "id,title,handle,images,status"}, timeout=20)
    for p in r2.json().get("products", []):
        print(f"  id={p['id']}  handle={p['handle']}  images={len(p.get('images',[]))}")

# ── 2. Scan ALL products for image issues ─────────────────────────────────────
print("\n=== All products image audit ===")
no_image   = []
one_image  = []
url = f"{BASE}/products.json?limit=250&fields=id,title,handle,images,status"
while url:
    r = httpx.get(url, headers=HR, timeout=30)
    for p in r.json().get("products", []):
        imgs = p.get("images", [])
        if len(imgs) == 0:
            no_image.append(p)
        elif len(imgs) == 1:
            one_image.append(p)
    link = r.headers.get("Link", "")
    url = None
    for part in link.split(","):
        if 'rel="next"' in part:
            url = part.strip().split(";")[0].strip("<> ")

print(f"\nNo images ({len(no_image)} products):")
for p in no_image:
    print(f"  [{p['status']}] {p['title'][:60]}  handle={p['handle']}")

print(f"\nOnly 1 image ({len(one_image)} products — showing first 10):")
for p in one_image[:10]:
    img_src = p['images'][0]['src'] if p.get('images') else 'none'
    print(f"  {p['title'][:55]}  img={img_src[img_src.rfind('/')+1:img_src.rfind('/')+50]}")
