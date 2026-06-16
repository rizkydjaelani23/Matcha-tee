"""
Phase 6: Create an SEO-rich About page, try to set shop name + homepage SEO.
"""
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
BASE  = "https://thematchatee.com"

# ── 1. About Us page ──────────────────────────────────────────────────────────
ABOUT_HTML = f"""
<p>The Matcha Tee was founded on a simple idea: a great <a href="{BASE}/collections/t-shirts">vintage graphic tee</a> should feel personal. Not a mass-produced logo on cheap fabric, but a soft, characterful shirt featuring the icons, eras and references you actually love.</p>

<h2>What we make</h2>
<p>We design vintage-style graphic tees and <a href="{BASE}/collections/hoodies-sweatshirts">sweatshirts</a> celebrating film legends, music icons and unforgettable pop-culture moments. Every piece is printed on premium, garment-dyed cotton with a relaxed unisex fit — built to feel lived-in from the very first wear.</p>

<h2>Our promise</h2>
<ul>
  <li><strong>Quality you can feel</strong> — heavyweight, soft, garment-dyed cotton.</li>
  <li><strong>Designs with meaning</strong> — retro graphics worth wearing again and again.</li>
  <li><strong>Fast UK delivery</strong> — with hassle-free 30-day returns.</li>
  <li><strong>Real customer care</strong> — message us any time; we genuinely reply.</li>
</ul>

<h2>Why "The Matcha Tee"?</h2>
<p>Because the best things — like a perfectly made matcha or a perfectly worn-in tee — are simple, considered and made with care. That's the standard we hold ourselves to on every order.</p>

<h2>Get in touch</h2>
<p>Questions about sizing, an order, or just want to say hello? Email us at <a href="mailto:hello@thematchatee.com">hello@thematchatee.com</a> or visit our <a href="{BASE}/pages/contact">contact page</a>. Ready to browse? Explore our <a href="{BASE}/collections/best-sellers">best sellers</a> or the <a href="{BASE}/collections/new-releases">latest drops</a>.</p>
""".strip()

# create or update existing about page
pages = httpx.get(f"{API}/pages.json?limit=50", headers=RH, timeout=15).json().get("pages", [])
existing = next((p for p in pages if p["handle"] in ("about", "about-us")), None)
if existing:
    r = httpx.put(f"{API}/pages/{existing['id']}.json", headers=H,
                  json={"page": {"id": existing["id"], "body_html": ABOUT_HTML}}, timeout=30)
    page = r.json()["page"]
    print(f"Updated About page (id {page['id']})")
else:
    r = httpx.post(f"{API}/pages.json", headers=H, json={"page": {
        "title": "About Us", "handle": "about", "body_html": ABOUT_HTML, "published": True,
    }}, timeout=30)
    page = r.json()["page"]
    print(f"Created About page (id {page['id']})  /pages/{page['handle']}")

# SEO metafields for About page
MUT = """mutation set($mf: [MetafieldsSetInput!]!) {
  metafieldsSet(metafields: $mf) { metafields { id } userErrors { field message } }
}"""
oid = f"gid://shopify/Page/{page['id']}"
mf = [
  {"ownerId": oid, "namespace": "global", "key": "title_tag", "type": "single_line_text_field",
   "value": "About The Matcha Tee | Vintage Graphic Tee Brand UK"},
  {"ownerId": oid, "namespace": "global", "key": "description_tag", "type": "single_line_text_field",
   "value": "Meet The Matcha Tee — a UK vintage graphic tee brand making premium, garment-dyed retro celebrity & pop-culture shirts. Our story, values & promise."},
]
httpx.post(GQL, headers=H, json={"query": MUT, "variables": {"mf": mf}}, timeout=30)
print("About page SEO set.")

# ── 2. try to update store name -> 'The Matcha Tee' ───────────────────────────
r = httpx.put(f"{API}/shop.json", headers=H, json={"shop": {"name": "The Matcha Tee"}}, timeout=20)
print(f"\nShop name update attempt: HTTP {r.status_code} "
      f"({'OK' if r.status_code==200 else 'not writable via API — set manually'})")
