"""Phase 3: SEO title, meta description + intro copy for collections (GraphQL)."""
import os, sys, json, time
import httpx
from dotenv import load_dotenv
sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
STORE = os.environ["SHOPIFY_STORE"]
TOKEN = os.environ["SHOPIFY_TOKEN"]
RH    = {"X-Shopify-Access-Token": TOKEN}
H     = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}
API   = f"https://{STORE}/admin/api/2025-01"
GQL   = f"https://{STORE}/admin/api/2025-01/graphql.json"

# handle -> (seo title, seo desc, intro html)
SEO = {
  "t-shirts": (
    "Vintage Graphic T-Shirts UK | Retro Celebrity Tees | The Matcha Tee",
    "Shop vintage-style graphic t-shirts at The Matcha Tee. Retro celebrity & pop-culture tees in soft cotton. Fast UK delivery & easy 30-day returns.",
    "<p>Discover our full range of <strong>vintage graphic t-shirts</strong> at The Matcha Tee. "
    "Each retro tee is printed on premium, garment-dyed cotton with a relaxed unisex fit — "
    "from iconic celebrities and musicians to nostalgic pop-culture moments. Soft, durable and "
    "made to feel lived-in from the first wear, with fast UK delivery and hassle-free returns.</p>"
  ),
  "hoodies-sweatshirts": (
    "Vintage Sweatshirts & Hoodies UK | Retro Graphic | The Matcha Tee",
    "Cosy vintage-style sweatshirts & hoodies at The Matcha Tee. Retro graphic prints on heavyweight cotton. Fast UK delivery & easy returns.",
    "<p>Stay warm in our <strong>vintage sweatshirts and hoodies</strong> — heavyweight, "
    "garment-dyed cotton with bold retro graphics and a relaxed unisex fit. Perfect for layering, "
    "with the same soft, lived-in feel our tees are known for. Fast UK delivery and easy returns.</p>"
  ),
  "best-sellers": (
    "Best-Selling Vintage Graphic Tees UK | The Matcha Tee",
    "Our best-selling vintage graphic tees, loved by customers across the UK. Retro celebrity & pop-culture shirts in soft cotton. Fast delivery.",
    "<p>These are our <strong>best-selling vintage graphic tees</strong> — the retro celebrity "
    "and pop-culture designs our customers reach for again and again. Premium soft cotton, unisex "
    "fit and fast UK delivery. If you're not sure where to start, start here.</p>"
  ),
  "new-releases": (
    "New Vintage Graphic Tees | Latest Drops | The Matcha Tee",
    "Shop the latest vintage graphic tee drops at The Matcha Tee. Fresh retro celebrity & pop-culture designs in soft cotton. Fast UK delivery.",
    "<p>The <strong>latest additions</strong> to The Matcha Tee — fresh vintage graphic tee "
    "designs added regularly. Be first to wear our newest retro celebrity and pop-culture prints, "
    "on the same premium soft cotton with fast UK delivery.</p>"
  ),
  "frontpage": (
    "The Matcha Tee | Vintage Graphic Tees & Retro Celebrity Shirts UK",
    "The Matcha Tee — premium vintage graphic tees & retro celebrity shirts. Soft cotton, unisex fit, fast UK delivery & easy returns.",
    None
  ),
}

# Fetch collections to map handle -> id
cols = httpx.get(f"{API}/custom_collections.json", headers=RH, timeout=15).json().get("custom_collections", [])
by_handle = {c["handle"]: c for c in cols}

MUT = """mutation upd($input: CollectionInput!) {
  collectionUpdate(input: $input) {
    collection { id handle seo { title description } }
    userErrors { field message }
  }
}"""

for handle, (ttl, desc, intro) in SEO.items():
    c = by_handle.get(handle)
    if not c:
        print(f"  {handle}: NOT FOUND")
        continue
    inp = {"id": f"gid://shopify/Collection/{c['id']}", "seo": {"title": ttl, "description": desc}}
    if intro:
        inp["descriptionHtml"] = intro
    r = httpx.post(GQL, headers=H, json={"query": MUT, "variables": {"input": inp}}, timeout=30)
    body = r.json()
    errs = body.get("data", {}).get("collectionUpdate", {}).get("userErrors", [])
    if errs or not body.get("data", {}).get("collectionUpdate", {}).get("collection"):
        print(f"  {handle}: FAIL {errs or body.get('errors')}")
    else:
        print(f"  {handle}: OK  '{ttl}'")
    time.sleep(0.4)

print("\nCollections SEO done.")
