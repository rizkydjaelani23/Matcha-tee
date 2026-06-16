"""Verify the first 2 synced products look correct."""
import os, httpx, sys
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
STORE = os.environ["SHOPIFY_STORE"]
SHOPIFY_TOKEN = os.environ["SHOPIFY_TOKEN"]
SHR = {"X-Shopify-Access-Token": SHOPIFY_TOKEN}
SAPI = f"https://{STORE}/admin/api/2025-01"

# Check the two new products
for pid in ["7697276174449", "7697278566513"]:
    r = httpx.get(f"{SAPI}/products/{pid}.json?fields=id,title,handle,status,variants", headers=SHR, timeout=20)
    p = r.json().get("product", {})
    print(f"\n=== Product {pid} ===")
    print(f"  title:  {p.get('title')}")
    print(f"  handle: {p.get('handle')}")
    print(f"  status: {p.get('status')}")
    print(f"  variants: {len(p.get('variants',[]))}")
    for v in p.get("variants", [])[:3]:
        print(f"    {v.get('option1')}/{v.get('option2')}  fulfillment={v.get('fulfillment_service')}  price={v.get('price')}")

# Check that old products are gone
print("\n\n=== Checking original products are deleted ===")
for pid in ["7690142679153", "7690131538033"]:
    r = httpx.get(f"{SAPI}/products/{pid}.json?fields=id,title", headers=SHR, timeout=20)
    print(f"  Product {pid}: status={r.status_code}  title={r.json().get('product',{}).get('title','(not found)')}")

# Check total product count
r2 = httpx.get(f"{SAPI}/products/count.json", headers=SHR, timeout=20)
print(f"\n  Total products on Shopify: {r2.json().get('count')}")

# Verify no 404 on the old handles (they should redirect)
print("\n=== Checking URL redirects ===")
for handle in ["addison-rae-vintage-retro-shirt", "al-pacino-retro-t-shirt-al-pacino-vintage-tee"]:
    r3 = httpx.get(
        f"{SAPI}/redirects.json?path=%2Fproducts%2F{handle}-printify-old",
        headers=SHR, timeout=20
    )
    redirects = r3.json().get("redirects", [])
    print(f"  Handle {handle[:40]}: {len(redirects)} redirect(s)")
    for rd in redirects:
        print(f"    {rd.get('path')} -> {rd.get('target')}")
