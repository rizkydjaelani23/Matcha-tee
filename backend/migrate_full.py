"""
migrate_full.py — Full Matcha Tee 3-option migration
======================================================
Creates 6 Printify products + 1 Shopify product (3-option: Color × Size × Fabric)
per design across 99 products.

Provider routing:
  UK Premium  → Shirt Monkey (ID=331)      Blueprint 706 (CC1717)
  UK Regular  → Shirt Monkey (ID=331)      Blueprint 6   (Gildan 5000)
  US Premium  → Monster Digital (ID=29)    Blueprint 706 (CC1717)
  US Regular  → Monster Digital (ID=29)    Blueprint 6   (Gildan 5000)
  EU Premium  → Printify Choice (ID=99)    Blueprint 706 (CC1717)
  EU Regular  → Textildruck Europa (ID=26) Blueprint 6   (Gildan 5000)

Shopify variants: 9 colors × 6 sizes Premium + 9 colors × 5 sizes Regular = 99 total

Run:
  python migrate_full.py --dry          # preview only, no changes
  python migrate_full.py --limit 1      # test on 1 product
  python migrate_full.py                # full run (~40 min)
  python migrate_full.py --reset        # clear checkpoint and restart
"""
import os, sys, time, json, csv, argparse, httpx, re
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

STORE          = os.environ["SHOPIFY_STORE"]
SHOPIFY_TOKEN  = os.environ["SHOPIFY_TOKEN"]
PRINTIFY_TOKEN = os.environ["PRINTIFY_TOKEN"]
SHOP_ID        = 27883571

SH   = {"X-Shopify-Access-Token": SHOPIFY_TOKEN, "Content-Type": "application/json"}
SHR  = {"X-Shopify-Access-Token": SHOPIFY_TOKEN}
PH   = {"Authorization": f"Bearer {PRINTIFY_TOKEN}", "Content-Type": "application/json"}
SAPI = f"https://{STORE}/admin/api/2025-01"
PAPI = "https://api.printify.com/v1"

CHECKPOINT = os.path.join(os.path.dirname(__file__), "full_checkpoint.json")
CSV_PATH   = os.path.join(os.path.dirname(__file__), "..", "scraper", "catalogue.csv")

# ── Pricing ───────────────────────────────────────────────────────────────────
PRICE_CC = 2999  # £29.99
PRICE_GD = 2599  # £25.99

# ── Colors and sizes ──────────────────────────────────────────────────────────
COLORS   = ["Black", "White", "Pepper", "Grey", "Ivory",
            "Light Green", "Chambray", "Washed Denim", "Blossom"]
SIZES_CC = ["S", "M", "L", "XL", "2XL", "3XL"]        # Premium — 6 sizes
SIZES_GD = ["S", "M", "L", "XL", "2XL"]               # Regular  — 5 sizes (no 3XL → total 99)

# ── Provider configs ──────────────────────────────────────────────────────────
PROVIDERS = {
    "UK_CC": {"provider_id": 331, "blueprint_id": 706, "price": PRICE_CC, "label": "UK Premium CC1717"},
    "UK_GD": {"provider_id": 331, "blueprint_id": 6,   "price": PRICE_GD, "label": "UK Regular Gildan"},
    "US_CC": {"provider_id": 29,  "blueprint_id": 706, "price": PRICE_CC, "label": "US Premium CC1717"},
    "US_GD": {"provider_id": 29,  "blueprint_id": 6,   "price": PRICE_GD, "label": "US Regular Gildan"},
    "EU_CC": {"provider_id": 99,  "blueprint_id": 706, "price": PRICE_CC, "label": "EU Premium CC1717"},
    "EU_GD": {"provider_id": 26,  "blueprint_id": 6,   "price": PRICE_GD, "label": "EU Regular Gildan"},
}

# ── Variant maps (from get_all_variant_ids.py) ────────────────────────────────
# Empty dict = OOS on this provider (size/color combo doesn't exist)
VARIANT_MAPS = {
    "UK_CC": {
        "Black":       {"S":73196,"M":73200,"L":73204,"XL":73208,"2XL":73212,"3XL":79114},
        "White":       {"S":73199,"M":73203,"2XL":73215,"3XL":79169},
        "Pepper":      {"M":79047,"3XL":79155},
        "Grey":        {"S":78971,"M":78972,"L":78973,"XL":78974,"2XL":78975,"3XL":79137},
        "Ivory":       {"3XL":79142},
        "Light Green": {"S":79006,"M":79007,"L":79008,"XL":79009,"2XL":79010,"3XL":79146},
        "Chambray":    {"S":78921,"M":78922,"L":78923,"XL":78924,"2XL":78925,"3XL":79124},
        "Washed Denim":{"S":79096,"M":79097,"L":79098,"XL":79099,"2XL":79100,"3XL":79167},
        "Blossom":     {"S":78886,"M":78887,"L":78888,"XL":78889,"2XL":78890,"3XL":79115},
    },
    "UK_GD": {
        "Black":       {"S":12126,"M":12125,"L":12124,"XL":12127,"2XL":12128,"3XL":12129},
        "White":       {"S":12102,"M":12101,"L":12100,"XL":12103,"2XL":12104,"3XL":12105},
        "Grey":        {"S":12072,"M":12071,"L":12070,"XL":12073,"2XL":12074,"3XL":12075},
        "Pepper":{}, "Ivory":{}, "Light Green":{}, "Chambray":{}, "Washed Denim":{}, "Blossom":{},
    },
    "US_CC": {
        "Black":       {"S":73196,"M":73200,"L":73204,"XL":73208,"2XL":73212,"3XL":79114},
        "White":       {"S":73199,"M":73203,"L":73207,"XL":73211,"2XL":73215,"3XL":79169},
        "Pepper":      {"S":79046,"M":79047,"L":79048,"XL":79049,"2XL":79050,"3XL":79155},
        "Grey":        {"S":78971,"M":78972,"L":78973,"XL":78974,"2XL":78975,"3XL":79137},
        "Ivory":       {"S":78991,"M":78992,"L":78993,"XL":78994,"2XL":78995,"3XL":79142},
        "Light Green": {"S":79006,"M":79007,"L":79008,"XL":79009,"2XL":79010,"3XL":79146},
        "Chambray":    {"S":78921,"M":78922,"L":78923,"XL":78924,"2XL":78925,"3XL":79124},
        "Washed Denim":{},
        "Blossom":     {"S":78886,"M":78887,"L":78888,"XL":78889,"2XL":78890,"3XL":79115},
    },
    "US_GD": {
        "Black":       {"S":12126,"M":12125,"L":12124,"XL":12127,"2XL":12128,"3XL":12129},
        "White":       {"S":12102,"M":12101,"L":12100,"XL":12103,"2XL":12104,"3XL":12105},
        "Grey":        {"S":12072,"M":12071,"L":12070,"XL":12073,"2XL":12074,"3XL":12075},
        "Pepper":{}, "Ivory":{}, "Light Green":{}, "Chambray":{}, "Washed Denim":{}, "Blossom":{},
    },
    "EU_CC": {
        "Black":       {"S":73196,"M":73200,"L":73204,"XL":73208,"2XL":73212,"3XL":79114},
        "White":       {"S":73199,"M":73203,"L":73207,"XL":73211,"2XL":73215,"3XL":79169},
        "Pepper":      {"S":79046,"M":79047,"L":79048,"XL":79049,"2XL":79050,"3XL":79155},
        "Grey":        {"S":78971,"M":78972,"L":78973,"XL":78974,"2XL":78975,"3XL":79137},
        "Ivory":       {"S":78991,"M":78992,"L":78993,"XL":78994,"2XL":78995,"3XL":79142},
        "Light Green": {"S":79006,"M":79007,"L":79008,"XL":79009,"2XL":79010,"3XL":79146},
        "Chambray":    {"S":78921,"M":78922,"L":78923,"XL":78924,"2XL":78925,"3XL":79124},
        "Washed Denim":{"S":79096,"M":79097,"L":79098,"XL":79099,"2XL":79100,"3XL":79167},
        "Blossom":     {"S":78886,"M":78887,"L":78888,"XL":78889,"2XL":78890,"3XL":79115},
    },
    "EU_GD": {
        "Black":       {"S":12126,"M":12125,"L":12124,"XL":12127,"2XL":12128,"3XL":12129},
        "White":       {"S":12102,"M":12101,"L":12100,"XL":12103,"2XL":12104,"3XL":12105},
        "Grey":        {"S":12072,"M":12071,"L":12070,"XL":12073,"2XL":12074,"3XL":12075},
        "Pepper":{}, "Ivory":{}, "Light Green":{}, "Chambray":{}, "Washed Denim":{}, "Blossom":{},
    },
}

# ── Description insert ────────────────────────────────────────────────────────
FABRIC_DESC = """<!-- matcha-guide -->
<div class="matcha-guide">

  <h3>🎽 Premium vs Regular — Which should I pick?</h3>

  <table>
    <thead>
      <tr><th></th><th>Premium — Comfort Colors® 1717</th><th>Regular — Gildan 5000</th></tr>
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
      <tr><th>Size</th><th>Chest (in)</th><th>Length (in)</th><th>UK approx.</th><th>EU approx.</th><th>US approx.</th></tr>
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
      <tr><th>Size</th><th>Chest (in)</th><th>Length (in)</th><th>UK approx.</th><th>EU approx.</th><th>US approx.</th></tr>
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
    <li>Note: Washed Denim colour is not available for US Premium orders — choose another colour or go Regular.</li>
    <li>Prices shown in USD at checkout.</li>
  </ul>

  <hr />

  <h3>💬 Still unsure?</h3>
  <p>If you are between sizes or unsure which fabric is right for you, go Premium and size down — the garment-dyed Comfort Colors tee is the one our customers keep coming back for. Message us before ordering and we will help you pick.</p>

</div>
<!-- /matcha-guide -->"""

# ── Checkpoint ────────────────────────────────────────────────────────────────
def load_cp():
    if os.path.exists(CHECKPOINT):
        return json.load(open(CHECKPOINT, encoding="utf-8"))
    return {}

def save_cp(data):
    with open(CHECKPOINT, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

# ── Shopify API ───────────────────────────────────────────────────────────────
def sh_req(method, path, body=None, params=None):
    for attempt in range(4):
        fn = getattr(httpx, method)
        kw = {"headers": SH if body is not None else SHR, "timeout": 30}
        if body is not None:
            kw["json"] = body
        if params:
            kw["params"] = params
        r = fn(f"{SAPI}{path}", **kw)
        if r.status_code == 429:
            wait = float(r.headers.get("Retry-After", 4))
            print(f"    [429] waiting {wait:.0f}s...")
            time.sleep(wait)
            continue
        return r
    return r

def sh_get_all_products():
    products = []
    url = (f"{SAPI}/products.json?limit=250"
           "&fields=id,title,body_html,handle,images,variants,tags,status,product_type")
    while url:
        r = httpx.get(url, headers=SHR, timeout=30)
        products.extend([p for p in r.json().get("products", []) if p.get("status") == "active"])
        link = r.headers.get("Link", "")
        url  = None
        for part in link.split(","):
            if 'rel="next"' in part:
                url = part.strip().split(";")[0].strip("<> ")
    return products

# ── Printify API ──────────────────────────────────────────────────────────────
def p_post(path, body):
    for attempt in range(5):
        r = httpx.post(f"{PAPI}{path}", headers=PH, json=body, timeout=60)
        if r.status_code == 429:
            wait = 30 + attempt * 20
            print(f"    [P429] waiting {wait}s...")
            time.sleep(wait)
            continue
        return r
    return r

def p_get(path):
    for _ in range(3):
        r = httpx.get(f"{PAPI}{path}", headers=PH, timeout=30)
        if r.status_code == 429:
            time.sleep(15)
            continue
        return r
    return r

# ── Upload image to Printify ──────────────────────────────────────────────────
def upload_image(img_url, fname):
    r = p_post("/uploads/images.json", {"file_name": fname, "url": img_url})
    if r.status_code not in (200, 201):
        raise Exception(f"Image upload failed {r.status_code}: {r.text[:200]}")
    return r.json()["id"]

# ── Create one Printify product (draft, not published) ────────────────────────
def create_printify_product(title, desc, image_id, pkey):
    cfg = PROVIDERS[pkey]
    vmap = VARIANT_MAPS[pkey]
    sizes = SIZES_CC if pkey.endswith("_CC") else SIZES_GD

    # Collect all variant IDs and build variant payload
    all_vid  = []
    variants = []
    for color in COLORS:
        for size in sizes:
            vid = vmap.get(color, {}).get(size)
            if vid:
                all_vid.append(vid)
                variants.append({"id": vid, "price": cfg["price"], "is_enabled": True})

    if not all_vid:
        raise Exception(f"No variants available for {pkey}")

    body = {
        "title": f"{title} [{cfg['label']}]",
        "description": desc or "",
        "blueprint_id": cfg["blueprint_id"],
        "print_provider_id": cfg["provider_id"],
        "variants": variants,
        "print_areas": [{
            "variant_ids": all_vid,
            "placeholders": [{
                "position": "front",
                "images": [{"id": image_id, "x": 0.5, "y": 0.5, "scale": 1.0, "angle": 0}]
            }]
        }],
    }
    r = p_post(f"/shops/{SHOP_ID}/products.json", body)
    if r.status_code not in (200, 201):
        raise Exception(f"Printify create failed {r.status_code}: {r.text[:300]}")
    return r.json()["id"]

# ── Build Shopify product payload ─────────────────────────────────────────────
def build_shopify_product(title, body_html, tags, image_url, printify_ids):
    variants = []

    # Premium CC: 9 × 6 = 54 variants
    for color in COLORS:
        for size in SIZES_CC:
            in_stock = any(
                VARIANT_MAPS[k].get(color, {}).get(size)
                for k in ["UK_CC", "US_CC", "EU_CC"]
            )
            sku = f"{re.sub('[^A-Z]','',color.upper()[:3])}-{size}-CC"
            v = {
                "option1": color,
                "option2": size,
                "option3": "Premium Comfort Colors",
                "price": f"{PRICE_CC/100:.2f}",
                "sku": sku,
                "requires_shipping": True,
                "taxable": True,
            }
            if in_stock:
                v["inventory_management"] = None
                v["inventory_policy"]     = "continue"
            else:
                v["inventory_management"] = "shopify"
                v["inventory_policy"]     = "deny"
                v["inventory_quantity"]   = 0
            variants.append(v)

    # Regular GD: 9 × 5 = 45 variants (no 3XL → total = 99)
    for color in COLORS:
        for size in SIZES_GD:
            in_stock = any(
                VARIANT_MAPS[k].get(color, {}).get(size)
                for k in ["UK_GD", "US_GD", "EU_GD"]
            )
            sku = f"{re.sub('[^A-Z]','',color.upper()[:3])}-{size}-GD"
            v = {
                "option1": color,
                "option2": size,
                "option3": "Regular Gildan",
                "price": f"{PRICE_GD/100:.2f}",
                "sku": sku,
                "requires_shipping": True,
                "taxable": True,
            }
            if in_stock:
                v["inventory_management"] = None
                v["inventory_policy"]     = "continue"
            else:
                v["inventory_management"] = "shopify"
                v["inventory_policy"]     = "deny"
                v["inventory_quantity"]   = 0
            variants.append(v)

    # Embed printify IDs in metafields for the order router
    metafields = [{
        "namespace": "matcha",
        "key":       "printify_ids",
        "value":     json.dumps(printify_ids),
        "type":      "json",
    }]

    body_html = FABRIC_DESC + "\n" + (body_html or "")
    payload = {
        "product": {
            "title":        title,
            "body_html":    body_html,
            "vendor":       "The Matcha Tee",
            "product_type": "T-Shirt",
            "tags":         tags,
            "status":       "active",
            "options": [
                {"name": "Color",  "values": COLORS},
                {"name": "Size",   "values": ["S","M","L","XL","2XL","3XL"]},
                {"name": "Fabric", "values": ["Premium Comfort Colors","Regular Gildan"]},
            ],
            "variants":   variants,
            "images":     [{"src": image_url}] if image_url else [],
            "metafields": metafields,
        }
    }
    return payload

# ── Shopify helpers ───────────────────────────────────────────────────────────
def get_collections(sid):
    r = sh_req("get", f"/products/{sid}/collects.json")
    if r.status_code != 200:
        return []
    return [c["collection_id"] for c in r.json().get("collects", [])]

def add_to_collections(new_sid, cids):
    for cid in cids:
        sh_req("post", "/collects.json",
               {"collect": {"product_id": int(new_sid), "collection_id": cid}})
        time.sleep(0.3)

def swap_handles_and_delete(old_handle, new_sid, old_sid):
    sh_req("put", f"/products/{old_sid}.json",
           {"product": {"id": old_sid, "handle": f"{old_handle}-v1"}})
    time.sleep(0.5)
    sh_req("put", f"/products/{int(new_sid)}.json",
           {"product": {"id": int(new_sid), "handle": old_handle}})
    time.sleep(0.5)
    sh_req("post", "/redirects.json", {"redirect": {
        "path": f"/products/{old_handle}-v1",
        "target": f"/products/{old_handle}",
    }})
    time.sleep(0.3)
    sh_req("delete", f"/products/{old_sid}.json")

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry",   action="store_true", help="Preview only")
    ap.add_argument("--limit", type=int, default=0, help="Process N products")
    ap.add_argument("--reset", action="store_true", help="Clear checkpoint")
    args = ap.parse_args()

    if args.reset and os.path.exists(CHECKPOINT):
        os.remove(CHECKPOINT)
        print("Checkpoint cleared.\n")

    cp = load_cp()

    # Load design images from CSV
    catalogue = {}
    try:
        with open(CSV_PATH, encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                img = row.get("IMAGE1_URL", "").strip()
                if not img:
                    continue
                title = row.get("TITLE", "").split(",")[0].strip()
                if title:
                    catalogue[title.lower()] = img
        print(f"Loaded {len(catalogue)} images from catalogue.csv")
    except FileNotFoundError:
        print("WARNING: catalogue.csv not found — will use Shopify product images")

    print("Fetching Shopify products...")
    products = sh_get_all_products()
    print(f"Found {len(products)} active products")

    # Deduplicate by title
    seen, deduped = {}, []
    for p in products:
        t = p["title"].strip().lower()
        if t not in seen:
            seen[t] = p["id"]
            deduped.append(p)
        else:
            print(f"  [DEDUP] Skip: {p['title']} (keeping id={seen[t]})")
    products = deduped
    print(f"After dedup: {len(products)} unique products\n")

    if args.limit:
        products = products[:args.limit]

    if args.dry:
        print("[DRY RUN] Would process:")
        for p in products:
            sid    = str(p["id"])
            status = cp.get(sid, {}).get("status", "pending")
            img    = catalogue.get(p["title"].strip().lower(), p.get("images",[{}])[0].get("src","none"))
            print(f"  [{status:8s}] {p['title'][:50]}")
            print(f"             img={'CSV' if p['title'].strip().lower() in catalogue else 'Shopify'}")
        total_variants = len(COLORS)*len(SIZES_CC) + len(COLORS)*len(SIZES_GD)
        print(f"\nVariants per product: {total_variants} "
              f"({len(COLORS)}×{len(SIZES_CC)} Premium + {len(COLORS)}×{len(SIZES_GD)} Regular)")
        return

    total = len(products)
    ok = fail = skip = 0

    # Build title-based lookup so retries work even after old IDs are deleted
    cp_by_title = {}
    for v in cp.values():
        t = (v.get("title") or "").strip().lower()
        if t:
            cp_by_title[t] = v

    for i, product in enumerate(products, 1):
        sid    = str(product["id"])
        title  = product["title"].strip()
        handle = product["handle"]
        desc   = product.get("body_html", "") or ""
        tags   = product.get("tags", "")

        print(f"\n[{i}/{total}] {title[:60]}")

        # Check by title first (handles retries after old IDs are gone)
        title_key = title.lower()
        existing  = cp_by_title.get(title_key) or cp.get(sid, {})
        if existing.get("status") == "done":
            print("  SKIP (already done)")
            skip += 1
            continue
        # Merge any partial progress found by title into the sid entry
        if existing and sid not in cp:
            cp[sid] = existing

        # Find design image
        img_url  = catalogue.get(title.lower())
        img_src  = "csv"
        if not img_url:
            imgs = product.get("images", [])
            img_url = imgs[0]["src"] if imgs else None
            img_src = "shopify"
        if not img_url:
            print("  SKIP — no image")
            cp[sid] = {"status": "no_image", "title": title}
            save_cp(cp)
            skip += 1
            continue
        print(f"  Image: {img_src}")

        img_name = img_url.split("/")[-1].split("?")[0] or "design.jpg"
        if not img_name.lower().endswith((".jpg",".jpeg",".png")):
            img_name += ".jpg"

        try:
            entry = cp.get(sid, {})

            # ── Step 1: Upload image ──────────────────────────────────────────
            image_id = entry.get("image_id")
            if not image_id:
                print("  Uploading image to Printify...")
                image_id = upload_image(img_url, img_name)
                entry = {**entry, "image_id": image_id, "title": title}
                cp[sid] = entry
                save_cp(cp)
                print(f"  image_id={image_id}")
            else:
                print(f"  Image cached: {image_id}")

            # ── Step 2: Create 6 Printify products ───────────────────────────
            printify_ids = entry.get("printify_ids", {})
            for pkey in PROVIDERS:
                if pkey in printify_ids:
                    print(f"  {pkey}: cached {printify_ids[pkey]}")
                    continue
                print(f"  Creating {PROVIDERS[pkey]['label']}...")
                pid = create_printify_product(title, "", image_id, pkey)
                printify_ids[pkey] = pid
                cp[sid] = {**entry, "printify_ids": printify_ids}
                save_cp(cp)
                print(f"    → {pid}")
                time.sleep(1)

            entry["printify_ids"] = printify_ids

            # ── Step 3: Create Shopify product ───────────────────────────────
            new_sid = entry.get("new_shopify_id")
            if not new_sid:
                print("  Creating Shopify product (99 variants)...")
                payload = build_shopify_product(
                    title, desc, tags, img_url, printify_ids)
                r = sh_req("post", "/products.json", payload)
                if r.status_code not in (200, 201):
                    raise Exception(f"Shopify create failed {r.status_code}: {r.text[:300]}")
                new_sid = str(r.json()["product"]["id"])
                entry["new_shopify_id"] = new_sid
                cp[sid] = entry
                save_cp(cp)
                print(f"  New Shopify ID: {new_sid}")
            else:
                print(f"  Shopify product cached: {new_sid}")

            # ── Step 4: Copy collections ──────────────────────────────────────
            if not entry.get("collections_done"):
                cids = get_collections(sid)
                if cids:
                    add_to_collections(new_sid, cids)
                    print(f"  Copied {len(cids)} collections")
                entry["collections_done"] = True
                cp[sid] = entry
                save_cp(cp)

            # ── Step 5: Swap handle + delete old product ──────────────────────
            if not entry.get("handle_done"):
                swap_handles_and_delete(handle, new_sid, int(sid))
                entry["handle_done"] = True
                print(f"  Handle '{handle}' transferred, old product deleted")

            cp[sid] = {**entry, "status": "done"}
            save_cp(cp)
            print("  DONE ✓")
            ok += 1

        except Exception as e:
            print(f"  ERROR: {e}")
            cp[sid] = {**cp.get(sid,{}), "status":"error", "error":str(e)[:300], "title":title}
            save_cp(cp)
            fail += 1

        if i < total:
            time.sleep(3)

    print(f"\n{'='*50}")
    print(f"Complete: {ok} done, {skip} skipped, {fail} errors")
    if fail:
        print("Re-run the script — checkpoint will resume from errors")

if __name__ == "__main__":
    main()
