"""
Push review Liquid sections to the theme and inject them into page templates.

Run order: 3 of 3  (after upload_reviews.py)

Usage:
    python setup_reviews.py

What it does:
  1. Pushes snippets/tmt-stars.liquid
  2. Pushes sections/tmt-reviews-home.liquid   (homepage review cards)
  3. Pushes sections/tmt-reviews-product.liquid (product page reviews from metafield)
  4. Updates templates/index.json  — inserts reviews section before trust_badges
  5. Updates templates/product.json — inserts reviews section after main product block
"""
import hashlib
import json
import os
import sys
import time

import httpx
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

STORE    = os.environ["SHOPIFY_STORE"]
H        = {"X-Shopify-Access-Token": os.environ["SHOPIFY_TOKEN"], "Content-Type": "application/json"}
API      = f"https://{STORE}/admin/api/2025-01"
THEME_ID = 143507587185
BASE     = os.path.dirname(os.path.abspath(__file__))
HOMEPAGE_REVIEWS = os.path.join(BASE, "homepage_reviews.json")


# ══════════════════════════════════════════════════════════════════════════════
#  LIQUID ASSETS
# ══════════════════════════════════════════════════════════════════════════════

TMT_STARS = """\
{%- comment -%}Usage: {%- render 'tmt-stars', rating: 5 -%}{%- endcomment -%}
{%- assign r = rating | round -%}
<span class="tmt-stars" aria-label="{{ r }} out of 5 stars">
  {%- for i in (1..5) -%}
    {%- if i <= r -%}<span class="tmt-star tmt-star--on">&#9733;</span>
    {%- else -%}<span class="tmt-star tmt-star--off">&#9733;</span>
    {%- endif -%}
  {%- endfor -%}
</span>
<style>
  .tmt-stars{display:inline-flex;gap:1px;line-height:1;}
  .tmt-star{font-size:1rem;}
  .tmt-star--on{color:#E8A84C;}
  .tmt-star--off{color:#E8A84C;opacity:.22;}
</style>
"""

# ─────────────────────────────────────────────────────────────────────────────
#  Homepage reviews section
#  Block-driven: blocks are pre-populated in templates/index.json by this script
# ─────────────────────────────────────────────────────────────────────────────
REVIEWS_HOME = """\
{%- comment -%}The Matcha Tee — homepage customer reviews{%- endcomment -%}
<section id="tmt-rh-{{ section.id }}" class="tmt-rh">
  <div class="tmt-rh__wrap page-width">

    <header class="tmt-rh__header">
      <div class="tmt-rh__agg-row">
        {%- render 'tmt-stars', rating: 5 -%}
        <span class="tmt-rh__agg">{{ section.settings.aggregate }}</span>
      </div>
      <h2 class="tmt-rh__heading">{{ section.settings.heading }}</h2>
      <p  class="tmt-rh__sub">{{ section.settings.subheading }}</p>
    </header>

    <div class="tmt-rh__grid">
      {%- for block in section.blocks -%}
        {%- if block.type == "review" -%}
          <article class="tmt-rh__card" {{ block.shopify_attributes }}>
            <div class="tmt-rh__card-stars">
              {%- render 'tmt-stars', rating: block.settings.rating -%}
            </div>
            <p class="tmt-rh__card-text">&#8220;{{ block.settings.text }}&#8221;</p>
            <footer class="tmt-rh__card-foot">
              <div class="tmt-rh__avatar" aria-hidden="true">
                {{- block.settings.name | slice: 0 | upcase -}}
              </div>
              <div class="tmt-rh__meta">
                <span class="tmt-rh__name">{{ block.settings.name }}</span>
                <span class="tmt-rh__prod">{{ block.settings.product }}</span>
              </div>
              <time class="tmt-rh__date">{{ block.settings.date }}</time>
            </footer>
          </article>
        {%- endif -%}
      {%- endfor -%}
    </div>

    {%- if section.settings.show_cta -%}
      <div class="tmt-rh__cta">
        <a href="{{ section.settings.cta_url }}" class="tmt-rh__btn">
          {{ section.settings.cta_label }}
        </a>
      </div>
    {%- endif -%}

  </div>
</section>

<style>
  #tmt-rh-{{ section.id }}{
    background:{{ section.settings.bg }};
    padding:64px 0;
  }
  .tmt-rh__wrap{max-width:1200px;margin:0 auto;padding:0 24px;}
  .tmt-rh__header{text-align:center;margin-bottom:48px;}
  .tmt-rh__agg-row{display:flex;align-items:center;justify-content:center;gap:10px;margin-bottom:14px;}
  .tmt-rh__agg{font-size:.9rem;color:{{ section.settings.text }};opacity:.7;}
  .tmt-rh__heading{
    font-size:clamp(1.5rem,3vw,2.1rem);font-weight:600;
    color:{{ section.settings.text }};margin:0 0 8px;letter-spacing:-.01em;
  }
  .tmt-rh__sub{font-size:1rem;color:{{ section.settings.text }};opacity:.72;margin:0;}

  .tmt-rh__grid{
    display:grid;
    grid-template-columns:repeat(auto-fill,minmax(272px,1fr));
    gap:20px;margin-bottom:48px;
  }
  .tmt-rh__card{
    background:{{ section.settings.card_bg }};
    border:1px solid {{ section.settings.card_border }};
    border-radius:12px;padding:22px 20px;
    display:flex;flex-direction:column;gap:14px;
  }
  .tmt-rh__card-stars{line-height:1;}
  .tmt-rh__card-text{
    font-size:.94rem;line-height:1.72;
    color:{{ section.settings.text }};margin:0;flex:1;font-style:italic;
  }
  .tmt-rh__card-foot{display:flex;align-items:center;gap:10px;margin-top:auto;}
  .tmt-rh__avatar{
    width:34px;height:34px;border-radius:50%;
    background:{{ section.settings.accent }};color:#FFF0D6;
    display:flex;align-items:center;justify-content:center;
    font-weight:700;font-size:.88rem;flex-shrink:0;
  }
  .tmt-rh__meta{display:flex;flex-direction:column;gap:2px;flex:1;min-width:0;}
  .tmt-rh__name{font-size:.84rem;font-weight:600;color:{{ section.settings.text }};}
  .tmt-rh__prod{
    font-size:.74rem;color:{{ section.settings.text }};opacity:.58;
    white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
  }
  .tmt-rh__date{font-size:.74rem;color:{{ section.settings.text }};opacity:.48;flex-shrink:0;}

  .tmt-rh__cta{text-align:center;}
  .tmt-rh__btn{
    display:inline-block;padding:14px 36px;
    background:{{ section.settings.accent }};color:#FFF0D6;
    border-radius:8px;text-decoration:none;font-size:.95rem;
    font-weight:500;letter-spacing:.01em;transition:opacity .2s ease;
  }
  .tmt-rh__btn:hover{opacity:.82;}

  @media(max-width:640px){
    #tmt-rh-{{ section.id }}{padding:44px 0;}
    .tmt-rh__grid{grid-template-columns:1fr;}
  }
</style>

{% schema %}
{
  "name": "Customer Reviews",
  "tag": "section",
  "class": "tmt-reviews-home",
  "settings": [
    {"type":"text",    "id":"heading",    "label":"Heading",          "default":"What our customers say"},
    {"type":"text",    "id":"subheading", "label":"Subheading",       "default":"Over 1,000 verified purchases on Etsy"},
    {"type":"text",    "id":"aggregate",  "label":"Aggregate label",  "default":"4.9 / 5 from 1,038 reviews"},
    {"type":"checkbox","id":"show_cta",   "label":"Show button",      "default":true},
    {"type":"text",    "id":"cta_label",  "label":"Button text",      "default":"Shop now"},
    {"type":"url",     "id":"cta_url",    "label":"Button URL"},
    {"type":"color",   "id":"bg",         "label":"Background",       "default":"#FFFFFF"},
    {"type":"color",   "id":"card_bg",    "label":"Card background",  "default":"#FAF7F4"},
    {"type":"color",   "id":"card_border","label":"Card border",      "default":"#EAE0D5"},
    {"type":"color",   "id":"text",       "label":"Text colour",      "default":"#6F5840"},
    {"type":"color",   "id":"accent",     "label":"Accent (avatar & button)","default":"#658C5E"}
  ],
  "blocks":[
    {
      "type":"review",
      "name":"Review",
      "settings":[
        {"type":"range",   "id":"rating", "label":"Stars","min":1,"max":5,"step":1,"default":5},
        {"type":"textarea","id":"text",   "label":"Review text",   "default":"Absolutely love this shirt!"},
        {"type":"text",    "id":"name",   "label":"Reviewer name", "default":"Happy Customer"},
        {"type":"text",    "id":"product","label":"Product bought","default":"Graphic Tee"},
        {"type":"text",    "id":"date",   "label":"Date",          "default":"Jun 2026"}
      ]
    }
  ],
  "presets":[{"name":"Customer Reviews"}]
}
{% endschema %}
"""

# ─────────────────────────────────────────────────────────────────────────────
#  Product page reviews section
#  Reads from product.metafields.custom.etsy_reviews (type: json)
# ─────────────────────────────────────────────────────────────────────────────
REVIEWS_PRODUCT = """\
{%- comment -%}The Matcha Tee — product page reviews from custom.etsy_reviews metafield{%- endcomment -%}
{%- assign reviews = product.metafields.custom.etsy_reviews.value -%}
{%- if reviews and reviews.size > 0 -%}

<section id="tmt-rp-{{ section.id }}" class="tmt-rp">
  <div class="page-width tmt-rp__inner">

    <header class="tmt-rp__header">
      <h3 class="tmt-rp__heading">Customer Reviews</h3>
      {%- assign total = reviews.size -%}
      {%- assign sum = 0 -%}
      {%- for rv in reviews -%}{%- assign sum = sum | plus: rv.rating -%}{%- endfor -%}
      {%- assign avg = sum | times: 1.0 | divided_by: total | round -%}
      <div class="tmt-rp__agg">
        {%- render 'tmt-stars', rating: avg -%}
        <span class="tmt-rp__agg-text">
          {{ avg }}.0 out of 5 &nbsp;&middot;&nbsp;
          {{ total }} review{%- if total != 1 -%}s{%- endif -%}
          &nbsp;&middot;&nbsp; Verified Etsy purchases
        </span>
      </div>
    </header>

    <ol class="tmt-rp__list">
      {%- for rv in reviews -%}
        <li class="tmt-rp__item">
          <div class="tmt-rp__item-top">
            {%- render 'tmt-stars', rating: rv.rating -%}
            <time class="tmt-rp__item-date">{{ rv.date }}</time>
          </div>
          <p class="tmt-rp__item-text">{{ rv.text }}</p>
          <div class="tmt-rp__item-reviewer">
            <span class="tmt-rp__item-avatar" aria-hidden="true">
              {{- rv.reviewer | slice: 0 | upcase -}}
            </span>
            <span class="tmt-rp__item-name">{{ rv.reviewer }}</span>
            <span class="tmt-rp__item-badge">&#10003; Verified purchase</span>
          </div>
        </li>
      {%- endfor -%}
    </ol>

  </div>
</section>

<style>
  .tmt-rp{
    background:#FFFFFF;
    border-top:1px solid #EAE0D5;
    padding:48px 0;
  }
  .tmt-rp__inner{max-width:860px;margin:0 auto;padding:0 24px;}
  .tmt-rp__header{margin-bottom:32px;}
  .tmt-rp__heading{
    font-size:1.3rem;font-weight:600;color:#6F5840;margin:0 0 12px;
  }
  .tmt-rp__agg{display:flex;align-items:center;gap:10px;flex-wrap:wrap;}
  .tmt-rp__agg-text{font-size:.88rem;color:#6F5840;opacity:.72;}

  .tmt-rp__list{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:0;}
  .tmt-rp__item{
    padding:24px 0;
    border-bottom:1px solid #EAE0D5;
  }
  .tmt-rp__item:last-child{border-bottom:none;padding-bottom:0;}
  .tmt-rp__item-top{display:flex;align-items:center;gap:12px;margin-bottom:10px;}
  .tmt-rp__item-date{font-size:.78rem;color:#6F5840;opacity:.5;margin-left:auto;}
  .tmt-rp__item-text{
    font-size:.96rem;line-height:1.72;color:#6F5840;margin:0 0 14px;
  }
  .tmt-rp__item-reviewer{display:flex;align-items:center;gap:8px;}
  .tmt-rp__item-avatar{
    width:30px;height:30px;border-radius:50%;
    background:#658C5E;color:#FFF0D6;
    display:flex;align-items:center;justify-content:center;
    font-size:.8rem;font-weight:700;flex-shrink:0;
  }
  .tmt-rp__item-name{font-size:.85rem;font-weight:600;color:#6F5840;}
  .tmt-rp__item-badge{
    font-size:.72rem;background:#EAF3DE;color:#3B6D11;
    padding:2px 8px;border-radius:4px;margin-left:4px;
  }

  @media(max-width:640px){
    .tmt-rp{padding:36px 0;}
    .tmt-rp__agg-text{font-size:.8rem;}
  }
</style>

{%- endif -%}

{% schema %}
{
  "name": "Product Reviews",
  "tag": "section",
  "class": "tmt-product-reviews",
  "settings": [],
  "presets": [{ "name": "Product Reviews" }]
}
{% endschema %}
"""


# ══════════════════════════════════════════════════════════════════════════════
#  THEME API HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def push_asset(key, value):
    r = httpx.put(
        f"{API}/themes/{THEME_ID}/assets.json",
        headers=H,
        json={"asset": {"key": key, "value": value}},
        timeout=60,
    )
    ok = r.status_code == 200
    print(f"  {'✓' if ok else '✗'} PUT {key}: {r.status_code}")
    return ok


def get_template(key):
    r = httpx.get(
        f"{API}/themes/{THEME_ID}/assets.json",
        headers=H,
        params={"asset[key]": key},
        timeout=30,
    )
    if r.status_code == 200:
        return json.loads(r.json()["asset"]["value"])
    print(f"  ERROR downloading {key}: {r.status_code}")
    return None


def put_template(key, data):
    value = json.dumps(data, indent=2)
    r = httpx.put(
        f"{API}/themes/{THEME_ID}/assets.json",
        headers=H,
        json={"asset": {"key": key, "value": value}},
        timeout=60,
    )
    ok = r.status_code == 200
    print(f"  {'✓' if ok else '✗'} PUT {key}: {r.status_code}")
    # Save local backup
    local = os.path.join(BASE, key.replace("/", "_") + ".updated.json")
    with open(local, "w", encoding="utf-8") as f:
        f.write(value)
    return ok


# ══════════════════════════════════════════════════════════════════════════════
#  BUILD REVIEW SECTION BLOCKS
# ══════════════════════════════════════════════════════════════════════════════

def block_id(i, text):
    h = hashlib.md5(f"{i}:{text[:20]}".encode()).hexdigest()[:7]
    return f"rv_{h}"


def build_home_section_entry(reviews):
    """Create the JSON entry for templates/index.json."""
    blocks = {}
    block_order = []

    for i, rv in enumerate(reviews):
        bid = block_id(i, rv.get("text", ""))
        # Product title: first segment only
        prod = rv.get("product_title", "Graphic Tee")
        prod = prod.split(",")[0].strip()[:55]

        blocks[bid] = {
            "type": "review",
            "settings": {
                "rating":  rv.get("rating", 5),
                "text":    rv.get("text", "")[:280],
                "name":    rv.get("reviewer", "Verified Buyer")[:40],
                "product": prod,
                "date":    rv.get("date", "2026"),
            }
        }
        block_order.append(bid)

    return {
        "type": "tmt-reviews-home",
        "blocks": blocks,
        "block_order": block_order,
        "settings": {
            "heading":    "What our customers say",
            "subheading": "Over 1,000 verified purchases on Etsy",
            "aggregate":  "4.9 / 5 from 1,038 reviews",
            "show_cta":   True,
            "cta_label":  "Shop now",
            "cta_url":    "/collections/all",
            "bg":         "#FFFFFF",
            "card_bg":    "#FAF7F4",
            "card_border":"#EAE0D5",
            "text":       "#6F5840",
            "accent":     "#658C5E",
        }
    }


# ══════════════════════════════════════════════════════════════════════════════
#  TEMPLATE UPDATES
# ══════════════════════════════════════════════════════════════════════════════

def update_index_json(reviews):
    print("\n4. Updating templates/index.json …")
    data = get_template("templates/index.json")
    if data is None:
        return False

    if "tmt_reviews_home" in data.get("sections", {}):
        print("  Already has tmt_reviews_home — skipping")
        return True

    data["sections"]["tmt_reviews_home"] = build_home_section_entry(reviews)

    order = data.get("order", [])
    try:
        pos = order.index("trust_badges")
    except ValueError:
        pos = len(order)
    order.insert(pos, "tmt_reviews_home")
    data["order"] = order

    return put_template("templates/index.json", data)


def update_product_json():
    print("\n5. Updating templates/product.json …")
    data = get_template("templates/product.json")
    if data is None:
        return False

    if "tmt_reviews_product" in data.get("sections", {}):
        print("  Already has tmt_reviews_product — skipping")
        return True

    data["sections"]["tmt_reviews_product"] = {
        "type": "tmt-reviews-product",
        "blocks": {},
        "settings": {}
    }

    order = data.get("order", [])
    try:
        pos = order.index("main") + 1
    except ValueError:
        pos = 1
    order.insert(pos, "tmt_reviews_product")
    data["order"] = order

    return put_template("templates/product.json", data)


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    if os.path.exists(HOMEPAGE_REVIEWS):
        with open(HOMEPAGE_REVIEWS, encoding="utf-8") as f:
            reviews = json.load(f)
        print(f"Loaded {len(reviews)} homepage reviews from {HOMEPAGE_REVIEWS}")
    else:
        print(f"WARNING: {HOMEPAGE_REVIEWS} not found — running without review blocks")
        print("Run upload_reviews.py first for full review blocks on homepage\n")
        reviews = []

    print("\n1. Pushing snippets/tmt-stars.liquid")
    push_asset("snippets/tmt-stars.liquid", TMT_STARS)
    time.sleep(0.5)

    print("\n2. Pushing sections/tmt-reviews-home.liquid")
    push_asset("sections/tmt-reviews-home.liquid", REVIEWS_HOME)
    time.sleep(0.5)

    print("\n3. Pushing sections/tmt-reviews-product.liquid")
    push_asset("sections/tmt-reviews-product.liquid", REVIEWS_PRODUCT)
    time.sleep(0.5)

    update_index_json(reviews)
    time.sleep(0.5)

    update_product_json()

    print(f"\n✓ All done.")
    print(f"  Homepage reviews: https://{os.environ['SHOPIFY_STORE']}/")
    print(f"  Product reviews:  open any product page that has reviews")


if __name__ == "__main__":
    main()
