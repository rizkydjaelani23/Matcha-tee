"""Show current prices for a sample product, grouped by size."""
import json, os, httpx
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
STORE = os.environ["SHOPIFY_STORE"]
TOKEN = os.environ["SHOPIFY_TOKEN"]
HR  = {"X-Shopify-Access-Token": TOKEN}
API = f"https://{STORE}/admin/api/2025-01"

cp   = json.load(open("full_checkpoint.json", encoding="utf-8"))
# pick a product with 3XL (likely one of the Comfort Colors ones)
entry = next(v for v in cp.values() if v.get("status") == "done" and v.get("new_shopify_id"))
pid   = entry["new_shopify_id"]
title = entry["title"]

r = httpx.get(f"{API}/products/{pid}/variants.json?limit=250", headers=HR, timeout=20)
variants = r.json().get("variants", [])

print(f"Product: {title[:60]}")
print(f"{'Size':<8} {'Fabric':<25} {'Price':>8} {'Compare':>10}")
print("-" * 55)
seen = set()
for v in sorted(variants, key=lambda x: (x.get("option3",""), x.get("option2",""))):
    key = (v.get("option2"), v.get("option3"))
    if key in seen: continue
    seen.add(key)
    print(f"{v.get('option2',''):<8} {v.get('option3',''):<25} £{v.get('price',''):>7} £{v.get('compare_at_price') or '':>9}")
