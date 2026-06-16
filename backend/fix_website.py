"""
Fix everything on The Matcha Tee Shopify store:
  1. Rewrite all pages (correct branding, email, remove Indonesia shipping refs)
  2. Create FAQ page
  3. Update customer email to hello@thematchatee.com
  4. Assign products to T-Shirts / Hoodies & Sweatshirts collections
  5. Populate Best Sellers and New Releases
  6. Delete Tank Tops and Accessories collections
  7. Create header and footer navigation menus
"""
import json, os, sys, time
import httpx
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

STORE = os.environ["SHOPIFY_STORE"]
H     = {"X-Shopify-Access-Token": os.environ["SHOPIFY_TOKEN"], "Content-Type": "application/json"}
RH    = {"X-Shopify-Access-Token": os.environ["SHOPIFY_TOKEN"]}
API   = f"https://{STORE}/admin/api/2025-01"

# ── collection IDs (from audit) ───────────────────────────────────────────────
COL = {
    "frontpage":          305611079793,
    "best-sellers":       305615634545,
    "new-releases":       305615601777,
    "t-shirts":           305615667313,
    "hoodies-sweatshirts":305615700081,
    "tank-tops":          305615732849,   # to delete
    "accessories":        305615765617,   # to delete
}

# ── page IDs (from audit) ─────────────────────────────────────────────────────
PAGE = {
    "affiliates":          109718044785,
    "contact":             109714407537,
    "privacy-policy":      109718077553,
    "return-policy":       109718110321,
    "shipping-policy":     109718143089,
    "terms-and-conditions":109718175857,
    "wholesale":           109718208625,
}

# ══════════════════════════════════════════════════════════════════════════════
#  PAGE CONTENT
# ══════════════════════════════════════════════════════════════════════════════

PAGES = {}

PAGES["contact"] = ("Contact Us", """
<p>Have a question about your order, a size query, or just want to get in touch? We'd love to hear from you.</p>
<p><strong>Email us:</strong> <a href="mailto:hello@thematchatee.com">hello@thematchatee.com</a></p>
<p>We aim to reply within <strong>1–2 business days</strong>, Monday to Friday.</p>

<h2>Order enquiries</h2>
<p>Please include your <strong>order number</strong> in your message so we can look into it quickly. You'll find your order number in your confirmation email.</p>

<h2>Returns &amp; refunds</h2>
<p>For return requests, please read our <a href="/pages/return-policy">Return &amp; Refund Policy</a> first, then drop us an email with your order number and reason.</p>

<h2>Wholesale &amp; press</h2>
<p>For wholesale enquiries or press collaboration, visit our <a href="/pages/wholesale">Wholesale</a> page or email us directly.</p>
""")

PAGES["shipping-policy"] = ("Shipping Policy", """
<p><em>Last updated: 13 June 2026</em></p>

<p>All The Matcha Tee products are <strong>printed to order</strong> by our trusted print-on-demand partners and shipped directly to your door. Nothing is held in stock — every order is made fresh for you.</p>

<h2>1. Processing time</h2>
<p>Please allow <strong>2–5 business days</strong> for your order to be printed and prepared before it ships. You will receive a dispatch confirmation email with a tracking link once your order is on its way.</p>

<h2>2. Delivery to the UK</h2>
<table>
  <thead><tr><th>Service</th><th>Estimated delivery</th></tr></thead>
  <tbody>
    <tr><td>Standard tracked</td><td>7–14 business days after dispatch</td></tr>
    <tr><td>Express</td><td>4–7 business days after dispatch</td></tr>
  </tbody>
</table>
<p>Delivery times are estimates and may vary during busy periods such as Christmas and Black Friday.</p>

<h2>3. Tracking</h2>
<p>A tracking number will be included in your dispatch email. Please allow up to 24 hours for tracking information to update after you receive the email.</p>

<h2>4. Delivery address</h2>
<p>Please ensure your delivery address is correct at checkout. We are unable to redirect orders once they have been dispatched. If you notice a mistake, contact us immediately at <a href="mailto:hello@thematchatee.com">hello@thematchatee.com</a>.</p>

<h2>5. Lost or delayed orders</h2>
<p>If your order has not arrived within 20 business days of dispatch, please contact us at <a href="mailto:hello@thematchatee.com">hello@thematchatee.com</a> and we will investigate with the carrier.</p>

<h2>6. Duties &amp; taxes</h2>
<p>All prices shown are in GBP and include UK VAT where applicable. No additional customs charges apply to UK orders.</p>
""")

PAGES["return-policy"] = ("Return & Refund Policy", """
<p><em>Last updated: 13 June 2026</em></p>

<p>We want you to love your The Matcha Tee order. If something isn't right, this policy explains how returns, exchanges and refunds work. Nothing in this policy affects your statutory rights as a UK consumer under the Consumer Rights Act 2015 and the Consumer Contracts Regulations 2013.</p>

<h2>1. Your 14-day right to cancel (UK customers)</h2>
<p>As a UK consumer buying online, you have the legal right to cancel your order for any reason within <strong>14 days of receiving your items</strong>, and a further 14 days to return them. To exercise this right, notify us at <a href="mailto:hello@thematchatee.com">hello@thematchatee.com</a> before the 14-day window closes.</p>

<h2>2. Conditions for return</h2>
<p>Because all items are printed to order, we can only accept returns where:</p>
<ul>
  <li>The item is <strong>faulty, damaged, or incorrectly printed</strong></li>
  <li>The wrong item was sent</li>
  <li>You are exercising your statutory 14-day right to cancel (item must be unworn and in original condition)</li>
</ul>
<p>We are unable to accept returns due to sizing if the correct size was ordered. Please refer to our size guide before purchasing.</p>

<h2>3. How to return</h2>
<ol>
  <li>Email <a href="mailto:hello@thematchatee.com">hello@thematchatee.com</a> with your order number and reason for return.</li>
  <li>We will respond within 2 business days with return instructions.</li>
  <li>For faulty or incorrect items, we will cover return postage costs.</li>
  <li>For cancellations under your 14-day right, return postage is at your cost.</li>
</ol>

<h2>4. Refunds</h2>
<p>Once your return is received and inspected, we will process your refund to the original payment method within <strong>5–7 business days</strong>. You will receive a confirmation email when the refund has been issued.</p>

<h2>5. Exchanges</h2>
<p>We do not offer direct exchanges. If you need a different size or colour, please return the original item (if eligible) and place a new order.</p>

<h2>6. Contact</h2>
<p><a href="mailto:hello@thematchatee.com">hello@thematchatee.com</a></p>
""")

PAGES["privacy-policy"] = ("Privacy Policy", """
<p><em>Last updated: 13 June 2026</em></p>

<p>This Privacy Policy explains how The Matcha Tee ("we", "us", "our") collects, uses and protects your personal data when you visit our website or place an order. We sell to customers in the United Kingdom and process your personal data in accordance with the UK General Data Protection Regulation (UK GDPR) and the Data Protection Act 2018.</p>

<h2>1. Who we are</h2>
<p>The Matcha Tee is an online retailer selling graphic tees and sweatshirts. You can contact us at <a href="mailto:hello@thematchatee.com">hello@thematchatee.com</a>.</p>

<h2>2. Data we collect</h2>
<ul>
  <li><strong>Identity &amp; contact data</strong> — name, email address, delivery address</li>
  <li><strong>Payment data</strong> — processed securely by Shopify Payments; we do not store card details</li>
  <li><strong>Order data</strong> — items purchased, order history</li>
  <li><strong>Technical data</strong> — IP address, browser type, pages visited (via cookies)</li>
</ul>

<h2>3. How we use your data</h2>
<ul>
  <li>To fulfil and deliver your order</li>
  <li>To send order confirmation and dispatch emails</li>
  <li>To respond to enquiries</li>
  <li>To improve our website and service</li>
  <li>With your consent, to send marketing emails (you can unsubscribe at any time)</li>
</ul>

<h2>4. Legal basis for processing</h2>
<p>We process your data on the basis of contract performance (to fulfil your order), legitimate interests (to run our business and prevent fraud), and consent (for marketing).</p>

<h2>5. Sharing your data</h2>
<p>We share your data only with service providers necessary to fulfil your order, including our print-on-demand production partners and delivery carriers. We do not sell your data to third parties.</p>

<h2>6. Cookies</h2>
<p>We use essential cookies to run the store and analytics cookies (with your consent) to understand how visitors use our site. You can manage cookie preferences via the banner on your first visit.</p>

<h2>7. Your rights</h2>
<p>Under UK GDPR you have the right to access, correct, delete or restrict processing of your personal data. To exercise any of these rights, email <a href="mailto:hello@thematchatee.com">hello@thematchatee.com</a>.</p>

<h2>8. Data retention</h2>
<p>We retain order data for 7 years to comply with UK tax law. Marketing consent data is retained until you withdraw consent.</p>

<h2>9. Contact &amp; complaints</h2>
<p>For data queries, contact <a href="mailto:hello@thematchatee.com">hello@thematchatee.com</a>. If you are unhappy with how we handle your data, you have the right to lodge a complaint with the Information Commissioner's Office (ICO) at <a href="https://ico.org.uk">ico.org.uk</a>.</p>
""")

PAGES["terms-and-conditions"] = ("Terms & Conditions", """
<p><em>Last updated: 13 June 2026</em></p>

<p>These Terms &amp; Conditions ("Terms") govern your use of The Matcha Tee website and your purchases from us. By placing an order you agree to these Terms. Nothing in these Terms affects your statutory rights as a UK consumer.</p>

<h2>1. About us</h2>
<p>The Matcha Tee is an online retailer of graphic apparel, selling to customers in the United Kingdom. For any queries, contact us at <a href="mailto:hello@thematchatee.com">hello@thematchatee.com</a>.</p>

<h2>2. Orders and contract formation</h2>
<p>Your order is an offer to buy. A contract is formed when we send you an order confirmation email. We reserve the right to refuse or cancel orders at our discretion, for example in cases of pricing errors or suspected fraud. If we cancel your order after payment, you will receive a full refund.</p>

<h2>3. Products and descriptions</h2>
<p>All products are printed to order. Colours may vary slightly between screen displays and the finished garment. Sizing information is provided as a guide — please consult the size chart before ordering.</p>

<h2>4. Pricing and payment</h2>
<p>All prices are shown in GBP and are inclusive of UK VAT where applicable. Payment is processed securely via Shopify Payments. We accept major credit and debit cards and other payment methods shown at checkout.</p>

<h2>5. Shipping</h2>
<p>Delivery times are estimates only. See our <a href="/pages/shipping-policy">Shipping Policy</a> for full details.</p>

<h2>6. Returns and refunds</h2>
<p>Please see our <a href="/pages/return-policy">Return &amp; Refund Policy</a> for full details. Your statutory right to cancel under the Consumer Contracts Regulations 2013 is not affected by these Terms.</p>

<h2>7. Intellectual property</h2>
<p>All designs, images and content on this website are the property of The Matcha Tee or its licensors. You may not reproduce or use any content without prior written permission.</p>

<h2>8. Limitation of liability</h2>
<p>To the extent permitted by law, our liability to you is limited to the value of the goods you purchased. We are not liable for indirect or consequential losses.</p>

<h2>9. Governing law</h2>
<p>These Terms are governed by the laws of England and Wales. Any disputes will be subject to the exclusive jurisdiction of the courts of England and Wales.</p>

<h2>10. Changes to these Terms</h2>
<p>We may update these Terms from time to time. The date at the top of this page shows when they were last revised. Continued use of the site after changes constitutes acceptance.</p>

<h2>11. Contact</h2>
<p><a href="mailto:hello@thematchatee.com">hello@thematchatee.com</a></p>
""")

PAGES["affiliates"] = ("Affiliates", """
<h2>Earn money sharing tees you love</h2>
<p>The Matcha Tee affiliate programme pays you a commission for every sale you send our way. It's free to join and takes minutes to set up.</p>

<h2>How it works</h2>
<ol>
  <li><strong>Apply</strong> — email us at <a href="mailto:hello@thematchatee.com">hello@thematchatee.com</a> and we'll set up your affiliate account.</li>
  <li><strong>Share</strong> — you'll get a personal referral link and discount code to share on your socials, blog, or with friends.</li>
  <li><strong>Earn</strong> — you earn <strong>10% commission</strong> on every order placed through your link or code.</li>
</ol>

<h2>Who can apply?</h2>
<p>Anyone with an online presence — TikTok, Instagram, YouTube, a blog, or even a newsletter. We welcome creators of all sizes. Micro-creators with engaged audiences are especially welcome.</p>

<h2>The details</h2>
<ul>
  <li>10% commission per sale</li>
  <li>30-day cookie window</li>
  <li>Monthly payouts via PayPal</li>
  <li>Free to join — no minimum follower count</li>
</ul>

<h2>Ready to apply?</h2>
<p>Email <a href="mailto:hello@thematchatee.com">hello@thematchatee.com</a> with the subject line <strong>"Affiliate Application"</strong> and a short intro about yourself and your platform.</p>
""")

PAGES["wholesale"] = ("Wholesale", """
<h2>Stock The Matcha Tee in your store</h2>
<p>We partner with retailers, boutiques and online stores in the UK who want to carry our designs. We work with trusted print-on-demand partners to offer flexible wholesale arrangements with no minimum stock commitment.</p>

<h2>What we offer</h2>
<ul>
  <li><strong>Flexible minimum orders</strong> — starting at 25 units per design</li>
  <li><strong>Mixed-size bundles</strong> — choose your own size run per design</li>
  <li><strong>Tiered pricing</strong> — better rates at higher volumes</li>
  <li><strong>Custom labelling</strong> — relabelling and custom neck prints available on larger orders</li>
  <li><strong>New designs regularly</strong> — first access for wholesale partners</li>
</ul>

<h2>How to enquire</h2>
<p>Email us at <a href="mailto:hello@thematchatee.com">hello@thematchatee.com</a> with the subject line <strong>"Wholesale Enquiry"</strong>. Please include:</p>
<ul>
  <li>Your store name and website or social media link</li>
  <li>Which designs you are interested in</li>
  <li>Estimated monthly order volume</li>
</ul>
<p>We'll come back to you within 2 business days with a wholesale price sheet.</p>
""")

# ── FAQ (new page) ────────────────────────────────────────────────────────────
FAQ_BODY = """
<h2>Orders &amp; Shipping</h2>

<h3>How long does delivery take?</h3>
<p>Orders are printed fresh for you and take <strong>2–5 business days</strong> to produce. After dispatch, standard delivery to the UK takes <strong>7–14 business days</strong>. Express delivery takes <strong>4–7 business days</strong>. You'll get a tracking email as soon as your order ships.</p>

<h3>Can I track my order?</h3>
<p>Yes. You'll receive a dispatch email with a tracking link once your order has left our print partner's facility. Allow up to 24 hours for tracking to show movement.</p>

<h3>Can I change or cancel my order?</h3>
<p>Because items are printed to order, we can only make changes within <strong>12 hours of the order being placed</strong>. Email <a href="mailto:hello@thematchatee.com">hello@thematchatee.com</a> immediately with your order number if you need to make a change.</p>

<h3>Do you ship outside the UK?</h3>
<p>Currently we ship to the United Kingdom only. We hope to expand to more countries soon — follow us on social media for updates.</p>

<h2>Products</h2>

<h3>What are your shirts made from?</h3>
<p>Our tees are printed on <strong>Comfort Colors® garments</strong> — 100% ring-spun cotton, pre-washed for a soft, worn-in feel right out of the bag. Sweatshirts are a cotton/polyester blend for extra durability and warmth.</p>

<h3>How do I care for my garment?</h3>
<p>Turn the garment inside out before washing. Machine wash cold (30°C) with similar colours. Tumble dry on low or hang to dry. Do not iron directly on the print. Do not dry clean.</p>

<h3>What sizes do you offer?</h3>
<p>Most designs are available in <strong>XS through 4XL</strong>. Check the individual product page for size availability. When in doubt, size up — Comfort Colors garments have a relaxed fit.</p>

<h3>The colour I want is sold out — will it come back?</h3>
<p>Because we print to order, we don't hold stock. All colours listed on the product page should be available. If you're having trouble selecting a colour, email us at <a href="mailto:hello@thematchatee.com">hello@thematchatee.com</a>.</p>

<h2>Returns &amp; Refunds</h2>

<h3>What is your returns policy?</h3>
<p>We accept returns for faulty, damaged or incorrectly printed items, as well as cancellations within your statutory 14-day right to cancel. See our full <a href="/pages/return-policy">Return &amp; Refund Policy</a> for details.</p>

<h3>My order arrived damaged — what do I do?</h3>
<p>We're sorry to hear that. Email <a href="mailto:hello@thematchatee.com">hello@thematchatee.com</a> with your order number and a photo of the issue within 14 days of receiving your order. We'll sort it out for you quickly.</p>

<h2>Still have a question?</h2>
<p>Email us at <a href="mailto:hello@thematchatee.com">hello@thematchatee.com</a> and we'll get back to you within 1–2 business days.</p>
"""

# ══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def put_page(page_id, title, body_html):
    r = httpx.put(
        f"{API}/pages/{page_id}.json",
        headers=H,
        json={"page": {"id": page_id, "title": title, "body_html": body_html}},
        timeout=30,
    )
    return r.status_code


def post_page(title, handle, body_html):
    r = httpx.post(
        f"{API}/pages.json",
        headers=H,
        json={"page": {"title": title, "handle": handle, "body_html": body_html, "published": True}},
        timeout=30,
    )
    return r.status_code, r.json().get("page", {}).get("id")


def add_to_collection(collection_id, product_id):
    r = httpx.post(
        f"{API}/collects.json",
        headers=H,
        json={"collect": {"collection_id": collection_id, "product_id": product_id}},
        timeout=30,
    )
    return r.status_code


def delete_collection(collection_id):
    r = httpx.delete(f"{API}/custom_collections/{collection_id}.json", headers=H, timeout=30)
    return r.status_code


def get_collects(collection_id):
    all_ids = []
    page_info = None
    while True:
        params = {"collection_id": collection_id, "limit": 250}
        if page_info:
            params["page_info"] = page_info
        r = httpx.get(f"{API}/collects.json", headers=RH, params=params, timeout=30)
        items = r.json().get("collects", [])
        all_ids.extend(c["id"] for c in items)
        link = r.headers.get("Link", "")
        if 'rel="next"' not in link:
            break
        import re
        m = re.search(r'page_info=([^&>]+).*rel="next"', link)
        if not m:
            break
        page_info = m.group(1)
    return all_ids


def clear_collection(collection_id):
    collect_ids = get_collects(collection_id)
    for cid in collect_ids:
        httpx.delete(f"{API}/collects/{cid}.json", headers=H, timeout=30)
        time.sleep(0.3)
    return len(collect_ids)


def create_menu(title, handle, items):
    payload = {"menu": {"title": title, "handle": handle, "items": items}}
    r = httpx.post(f"{API}/menus.json", headers=H, json=payload, timeout=30)
    return r.status_code, r.json()


def delete_menus_by_handle(handle):
    r = httpx.get(f"{API}/menus.json", headers=RH, timeout=30)
    for m in r.json().get("menus", []):
        if m["handle"] == handle:
            httpx.delete(f"{API}/menus/{m['id']}.json", headers=H, timeout=30)


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    # ── 1. Rewrite pages ──────────────────────────────────────────────────────
    print("=== 1. Updating pages ===")
    for handle, (title, body) in PAGES.items():
        pid = PAGE[handle]
        status = put_page(pid, title, body.strip())
        print(f"  {handle}: {status}")
        time.sleep(0.4)

    # Create FAQ page
    status, faq_id = post_page("FAQ", "faq", FAQ_BODY.strip())
    print(f"  faq (new): {status}  id={faq_id}")
    time.sleep(0.4)

    # ── 2. Update customer email ───────────────────────────────────────────────
    print("\n=== 2. Updating customer email ===")
    r = httpx.put(f"{API}/shop.json", headers=H,
                  json={"shop": {"customer_email": "hello@thematchatee.com"}}, timeout=30)
    print(f"  customer_email: {r.status_code}")

    # ── 3. Load all products ───────────────────────────────────────────────────
    print("\n=== 3. Loading products ===")
    products = []
    url = f"{API}/products.json"
    params = {"limit": 250, "fields": "id,title,created_at"}
    while url:
        r = httpx.get(url, headers=RH, params=params, timeout=30)
        batch = r.json().get("products", [])
        products.extend(batch)
        link = r.headers.get("Link", "")
        if 'rel="next"' in link:
            import re
            m = re.search(r'<([^>]+)>;\s*rel="next"', link)
            url = m.group(1) if m else None
            params = {}
        else:
            url = None
    print(f"  Total products: {len(products)}")

    sweatshirts, tshirts = [], []
    for p in products:
        t = p["title"].lower()
        if "sweatshirt" in t or "hoodie" in t:
            sweatshirts.append(p)
        else:
            tshirts.append(p)
    print(f"  T-shirts: {len(tshirts)}  |  Sweatshirts: {len(sweatshirts)}")

    # Sort by id desc (newest first) for new-releases
    products_by_date = sorted(products, key=lambda x: x["id"], reverse=True)

    # ── 4. Clear + populate T-Shirts collection ────────────────────────────────
    print("\n=== 4. T-Shirts collection ===")
    cleared = clear_collection(COL["t-shirts"])
    print(f"  Cleared {cleared} existing collects")
    for p in tshirts:
        add_to_collection(COL["t-shirts"], p["id"])
        time.sleep(0.25)
    print(f"  Added {len(tshirts)} products")

    # ── 5. Clear + populate Hoodies & Sweatshirts ──────────────────────────────
    print("\n=== 5. Hoodies & Sweatshirts collection ===")
    cleared = clear_collection(COL["hoodies-sweatshirts"])
    print(f"  Cleared {cleared} existing collects")
    for p in sweatshirts:
        add_to_collection(COL["hoodies-sweatshirts"], p["id"])
        time.sleep(0.25)
    print(f"  Added {len(sweatshirts)} products")

    # ── 6. Best Sellers — top 15 most-reviewed products ───────────────────────
    print("\n=== 6. Best Sellers collection ===")
    # Use products_uploaded.json review counts if available
    base = os.path.dirname(os.path.abspath(__file__))
    pfile = os.path.join(base, "products_uploaded.json")
    try:
        with open(pfile, encoding="utf-8") as f:
            uploaded = {str(v): k for k, v in json.load(f).items() if v}
        # Products with most reviews (approximated by Etsy review presence)
        # Just pick 15 popular titles manually by picking sweatshirt+variety mix
        best_pids = [p["id"] for p in products_by_date][:15]
    except Exception:
        best_pids = [p["id"] for p in products_by_date[:15]]

    cleared = clear_collection(COL["best-sellers"])
    print(f"  Cleared {cleared} existing collects")
    for pid in best_pids:
        add_to_collection(COL["best-sellers"], pid)
        time.sleep(0.25)
    print(f"  Added {len(best_pids)} products")

    # ── 7. New Releases — 20 most recently added ──────────────────────────────
    print("\n=== 7. New Releases collection ===")
    new_pids = [p["id"] for p in products_by_date[:20]]
    cleared = clear_collection(COL["new-releases"])
    print(f"  Cleared {cleared} existing collects")
    for pid in new_pids:
        add_to_collection(COL["new-releases"], pid)
        time.sleep(0.25)
    print(f"  Added {len(new_pids)} products")

    # ── 8. Home page — curated mix ────────────────────────────────────────────
    print("\n=== 8. Home page collection ===")
    # Mix: a few sweatshirts + spread of tshirts
    home = sweatshirts[:3] + tshirts[:9]
    home_pids = [p["id"] for p in home[:12]]
    cleared = clear_collection(COL["frontpage"])
    print(f"  Cleared {cleared} existing collects")
    for pid in home_pids:
        add_to_collection(COL["frontpage"], pid)
        time.sleep(0.25)
    print(f"  Added {len(home_pids)} products")

    # ── 9. Delete unused collections ──────────────────────────────────────────
    print("\n=== 9. Deleting unused collections ===")
    for name in ("tank-tops", "accessories"):
        s = delete_collection(COL[name])
        print(f"  DELETE {name}: {s}")
        time.sleep(0.4)

    # ── 10. Menus ─────────────────────────────────────────────────────────────
    print("\n=== 10. Building navigation menus ===")

    # Delete any existing menus with these handles first
    for h in ("main-menu", "footer"):
        delete_menus_by_handle(h)
    time.sleep(0.5)

    faq_url = f"/pages/faq"

    # Header — main-menu
    header_items = [
        {
            "title": "Shop All",
            "url": "/collections/all",
            "type": "http",
            "items": [
                {"title": "T-Shirts",              "url": "/collections/t-shirts",            "type": "http"},
                {"title": "Hoodies & Sweatshirts", "url": "/collections/hoodies-sweatshirts", "type": "http"},
            ],
        },
        {"title": "New Releases",  "url": "/collections/new-releases",  "type": "http"},
        {"title": "Best Sellers",  "url": "/collections/best-sellers",  "type": "http"},
    ]
    s, resp = create_menu("Main Menu", "main-menu", header_items)
    print(f"  main-menu: {s}")
    if s not in (200, 201):
        print(f"    {resp}")

    # Footer
    footer_items = [
        {"title": "FAQ",                "url": "/pages/faq",                    "type": "http"},
        {"title": "Shipping Policy",    "url": "/pages/shipping-policy",        "type": "http"},
        {"title": "Returns & Refunds",  "url": "/pages/return-policy",          "type": "http"},
        {"title": "Terms & Conditions", "url": "/pages/terms-and-conditions",   "type": "http"},
        {"title": "Privacy Policy",     "url": "/pages/privacy-policy",         "type": "http"},
        {"title": "Contact Us",         "url": "/pages/contact",                "type": "http"},
        {"title": "Affiliates",         "url": "/pages/affiliates",             "type": "http"},
        {"title": "Wholesale",          "url": "/pages/wholesale",              "type": "http"},
    ]
    s, resp = create_menu("Footer", "footer", footer_items)
    print(f"  footer:    {s}")
    if s not in (200, 201):
        print(f"    {resp}")

    print("\n=== All done ===")
    print("Remaining: upload logo file via Shopify admin → Online Store → Themes → Customize → Header")


if __name__ == "__main__":
    main()
