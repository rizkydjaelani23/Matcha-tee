"""
update_descriptions.py — Inject fabric guide + sizing tutorial into all Shopify products
Run after (or during) migrate_full.py — safe to run multiple times (idempotent).

Updates body_html on every active Shopify product that has our 3-option
(Color / Size / Fabric) variant structure.
"""
import os, sys, time, json, httpx
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

STORE         = os.environ["SHOPIFY_STORE"]
SHOPIFY_TOKEN = os.environ["SHOPIFY_TOKEN"]
SH  = {"X-Shopify-Access-Token": SHOPIFY_TOKEN, "Content-Type": "application/json"}
SHR = {"X-Shopify-Access-Token": SHOPIFY_TOKEN}
SAPI = f"https://{STORE}/admin/api/2025-01"

# ── The guide that gets prepended to every product description ────────────────
GUIDE = """
<div class="matcha-guide">

  <h3>🎽 Premium vs Regular — Which should I pick?</h3>

  <table>
    <thead>
      <tr>
        <th></th>
        <th>Premium — Comfort Colors® 1717</th>
        <th>Regular — Gildan 5000</th>
      </tr>
    </thead>
    <tbody>
      <tr><td><strong>Price</strong></td><td>£29.99</td><td>£25.99</td></tr>
      <tr><td><strong>Weight</strong></td><td>6.1 oz — heavyweight, substantial feel</td><td>5.3 oz — lightweight, everyday wear</td></tr>
      <tr><td><strong>Fabric</strong></td><td>100% ring-spun cotton, garment-dyed</td><td>100% pre-shrunk cotton, classic finish</td></tr>
      <tr><td><strong>Fit</strong></td><td>Relaxed / slightly oversized, boxy</td><td>Classic / true-to-size, structured</td></tr>
      <tr><td><strong>Feel</strong></td><td>Ultra-soft, worn-in vintage feel from day one</td><td>Crisp, clean, traditional tee feel</td></tr>
      <tr><td><strong>Shrinkage</strong></td><td>Wash cold — may shrink ~5% on first wash</td><td>Pre-shrunk — minimal shrinkage</td></tr>
      <tr><td><strong>Best for</strong></td><td>Streetwear, oversized fits, gifting, quality-first</td><td>Everyday wear, layering, budget-friendly</td></tr>
      <tr><td><strong>Colours</strong></td><td>9 garment-dyed colourways</td><td>Black, White, Grey (others coming soon)</td></tr>
    </tbody>
  </table>

  <p><strong>Our pick:</strong> If you want that premium, soft, vintage aesthetic — go Premium. If you want a reliable everyday tee at a lower price — go Regular.</p>

  <hr />

  <h3>📐 Size Guide</h3>

  <p>Use the chest measurement (the widest part across your chest) to find your size. All measurements are in inches.</p>

  <h4>Premium — Comfort Colors 1717 (Relaxed Fit)</h4>
  <p><em>Runs slightly large. If you are between sizes, size down. After first wash, expect ~5% shrinkage — wash cold and air dry to preserve shape.</em></p>

  <table>
    <thead>
      <tr>
        <th>Size</th>
        <th>Chest (in)</th>
        <th>Length (in)</th>
        <th>UK approx.</th>
        <th>EU approx.</th>
        <th>US approx.</th>
      </tr>
    </thead>
    <tbody>
      <tr><td>S</td><td>18"</td><td>27"</td><td>8–10</td><td>36–38</td><td>XS–S</td></tr>
      <tr><td>M</td><td>20"</td><td>28"</td><td>10–12</td><td>38–40</td><td>S–M</td></tr>
      <tr><td>L</td><td>22"</td><td>29"</td><td>12–14</td><td>40–42</td><td>M–L</td></tr>
      <tr><td>XL</td><td>24"</td><td>30"</td><td>14–16</td><td>42–44</td><td>L–XL</td></tr>
      <tr><td>2XL</td><td>26"</td><td>31"</td><td>16–18</td><td>44–46</td><td>XL–2XL</td></tr>
      <tr><td>3XL</td><td>28"</td><td>32"</td><td>18–20</td><td>46–48</td><td>2XL–3XL</td></tr>
    </tbody>
  </table>

  <h4>Regular — Gildan 5000 (Classic Fit)</h4>
  <p><em>True to size. Pre-shrunk — what you order is what you get.</em></p>

  <table>
    <thead>
      <tr>
        <th>Size</th>
        <th>Chest (in)</th>
        <th>Length (in)</th>
        <th>UK approx.</th>
        <th>EU approx.</th>
        <th>US approx.</th>
      </tr>
    </thead>
    <tbody>
      <tr><td>S</td><td>18"</td><td>28"</td><td>10–12</td><td>38–40</td><td>S</td></tr>
      <tr><td>M</td><td>20"</td><td>29"</td><td>12–14</td><td>40–42</td><td>M</td></tr>
      <tr><td>L</td><td>22"</td><td>30"</td><td>14–16</td><td>42–44</td><td>L</td></tr>
      <tr><td>XL</td><td>24"</td><td>31"</td><td>16–18</td><td>44–46</td><td>XL</td></tr>
      <tr><td>2XL</td><td>26"</td><td>32"</td><td>18–20</td><td>46–48</td><td>2XL</td></tr>
    </tbody>
  </table>

  <hr />

  <h3>🌍 Ordering by Country — What to expect</h3>

  <h4>🇬🇧 United Kingdom</h4>
  <ul>
    <li>Printed and shipped from our UK facility — fastest delivery, typically <strong>3–5 business days</strong>.</li>
    <li>UK sizing follows standard US sizing — order your usual size.</li>
    <li>Premium CC1717: if you prefer a fitted look, size down one. The relaxed cut is intentionally oversized.</li>
    <li>Free shipping — no surprises at checkout.</li>
  </ul>

  <h4>🇪🇺 Europe (EU)</h4>
  <ul>
    <li>Printed in Europe and shipped to you — typically <strong>5–8 business days</strong>.</li>
    <li>EU sizing runs smaller than US/UK. Use the size chart above — compare your chest measurement, not your usual EU label.</li>
    <li>Example: if you normally wear EU size M (40), you likely need a UK/US S or M in our shirts.</li>
    <li>Premium CC1717 has a relaxed oversized fit — EU customers who prefer a fitted look should size down.</li>
    <li>Prices shown in EUR at checkout.</li>
  </ul>

  <h4>🇺🇸 United States</h4>
  <ul>
    <li>Printed and shipped from our US facility — typically <strong>5–7 business days</strong>.</li>
    <li>US sizing is standard — order your usual US size.</li>
    <li>Note: Washed Denim colour is not available for US Premium orders (OOS) — choose another colour or go Regular.</li>
    <li>Prices shown in USD at checkout.</li>
  </ul>

  <hr />

  <h3>💬 Still unsure?</h3>
  <p>If you are between sizes or unsure which fabric is right for you, go Premium and size down — the garment-dyed Comfort Colors tee is the one our customers keep coming back for. Any questions, message us before ordering and we will help you pick.</p>

</div>
""".strip()

MARKER = "<!-- matcha-guide -->"

def sh_req(method, path, body=None):
    for _ in range(4):
        fn  = getattr(httpx, method)
        kw  = {"headers": SH if body else SHR, "timeout": 30}
        if body:
            kw["json"] = body
        r = fn(f"{SAPI}{path}", **kw)
        if r.status_code == 429:
            time.sleep(float(r.headers.get("Retry-After", 4)))
            continue
        return r
    return r

def get_all_products():
    products = []
    url = f"{SAPI}/products.json?limit=250&fields=id,title,body_html,options,status"
    while url:
        r = httpx.get(url, headers=SHR, timeout=30)
        products.extend(r.json().get("products", []))
        link = r.headers.get("Link", "")
        url  = None
        for part in link.split(","):
            if 'rel="next"' in part:
                url = part.strip().split(";")[0].strip("<> ")
    return products

def has_3_options(product):
    options = product.get("options", [])
    names   = [o["name"].lower() for o in options]
    return "fabric" in names and "color" in names and "size" in names

def main():
    print("Fetching Shopify products...")
    products = get_all_products()
    targets  = [p for p in products if p.get("status") == "active" and has_3_options(p)]
    print(f"Found {len(targets)} products with 3-option (Color/Size/Fabric) structure\n")

    ok = skip = fail = 0

    for i, p in enumerate(targets, 1):
        pid   = p["id"]
        title = p["title"]
        body  = p.get("body_html") or ""

        print(f"[{i}/{len(targets)}] {title[:60]}")

        # Already has the guide
        if MARKER in body:
            print("  SKIP (guide already present)")
            skip += 1
            continue

        # Strip old FABRIC_DESC block if present (the short version from migrate_full.py)
        if "<div class=\"matcha-guide\">" not in body and "Choose your style:" in body:
            # Remove the old short fabric desc
            import re
            body = re.sub(r"<p><strong>Choose your style.*?</ul>\s*", "", body, flags=re.DOTALL)

        new_body = f"{MARKER}\n{GUIDE}\n<!-- /matcha-guide -->\n\n{body.strip()}"

        r = sh_req("put", f"/products/{pid}.json",
                   {"product": {"id": pid, "body_html": new_body}})
        if r.status_code == 200:
            print("  ✓ Updated")
            ok += 1
        else:
            print(f"  ERROR {r.status_code}: {r.text[:150]}")
            fail += 1

        time.sleep(0.5)

    print(f"\nDone: {ok} updated, {skip} skipped, {fail} errors")

if __name__ == "__main__":
    main()
