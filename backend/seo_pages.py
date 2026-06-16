"""Phase 4: SEO title_tag + description_tag for all pages via metafieldsSet (upsert)."""
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

SEO = {
  "contact": ("Contact Us | The Matcha Tee",
    "Get in touch with The Matcha Tee. Questions about your vintage graphic tee order, sizing or returns? Email hello@thematchatee.com — we reply fast."),
  "faq": ("FAQ – Shipping, Sizing & Returns | The Matcha Tee",
    "Common questions about The Matcha Tee — UK delivery times, sizing, returns, payment and more. Everything you need to know before you order."),
  "shipping-policy": ("Shipping Policy | UK Delivery | The Matcha Tee",
    "The Matcha Tee shipping policy — delivery times, costs and tracking for your vintage graphic tee order. Fast, reliable worldwide shipping."),
  "return-policy": ("Returns & Refunds | 30-Day Policy | The Matcha Tee",
    "Our returns & refund policy. Easy 30-day returns on vintage graphic tees. Learn how to return or exchange your order hassle-free at The Matcha Tee."),
  "privacy-policy": ("Privacy Policy | The Matcha Tee",
    "How The Matcha Tee collects, uses and protects your personal data. Read our privacy policy for full details on your information and your rights."),
  "terms-and-conditions": ("Terms & Conditions | The Matcha Tee",
    "The terms & conditions for shopping with The Matcha Tee. Please read our store policies before purchasing your vintage graphic tees."),
  "affiliates": ("Affiliate Programme | Earn With Us | The Matcha Tee",
    "Join The Matcha Tee affiliate programme and earn commission promoting vintage graphic tees. Sign up and start earning today."),
  "wholesale": ("Wholesale Enquiries | Bulk Orders | The Matcha Tee",
    "Want to stock The Matcha Tee vintage graphic tees? Get in touch about wholesale pricing and bulk orders for your business."),
}

pages = httpx.get(f"{API}/pages.json?limit=50", headers=RH, timeout=15).json().get("pages", [])
by_handle = {p["handle"]: p for p in pages}

metafields = []
for handle, (ttl, desc) in SEO.items():
    p = by_handle.get(handle)
    if not p:
        print(f"  {handle}: NOT FOUND")
        continue
    oid = f"gid://shopify/Page/{p['id']}"
    metafields.append({"ownerId": oid, "namespace": "global", "key": "title_tag",
                       "type": "single_line_text_field", "value": ttl})
    metafields.append({"ownerId": oid, "namespace": "global", "key": "description_tag",
                       "type": "single_line_text_field", "value": desc})

MUT = """mutation set($mf: [MetafieldsSetInput!]!) {
  metafieldsSet(metafields: $mf) {
    metafields { id key }
    userErrors { field message }
  }
}"""

# metafieldsSet allows up to 25 per call
for i in range(0, len(metafields), 24):
    chunk = metafields[i:i+24]
    r = httpx.post(GQL, headers=H, json={"query": MUT, "variables": {"mf": chunk}}, timeout=30)
    body = r.json()
    errs = body.get("data", {}).get("metafieldsSet", {}).get("userErrors", [])
    n = len(body.get("data", {}).get("metafieldsSet", {}).get("metafields", []))
    print(f"  chunk {i//24+1}: set {n} metafields  errors={errs}")
    time.sleep(0.4)

print("\nPages SEO done.")
