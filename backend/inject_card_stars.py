"""Inject star ratings into the product card snippet."""
import os, httpx, json
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

STORE    = os.environ["SHOPIFY_STORE"]
H        = {"X-Shopify-Access-Token": os.environ["SHOPIFY_TOKEN"], "Content-Type": "application/json"}
API      = f"https://{STORE}/admin/api/2025-01"
THEME_ID = 143507587185

# ── fetch ──────────────────────────────────────────────────────────────────────
r = httpx.get(
    f"{API}/themes/{THEME_ID}/assets.json",
    headers={k: v for k, v in H.items() if k != "Content-Type"},
    params={"asset[key]": "snippets/product-card.liquid"},
    timeout=30,
)
src = r.json()["asset"]["value"]

# ── injection 1: stars block after {{ children }} ─────────────────────────────
STARS_BLOCK = """\
    {%- unless onboarding -%}
      {%- assign tmt_rv = product.metafields.custom.etsy_reviews.value -%}
      {%- if tmt_rv and tmt_rv.size > 0 -%}
        {%- assign tmt_n = tmt_rv.size -%}
        {%- assign tmt_s = 0 -%}
        {%- for rv in tmt_rv -%}{%- assign tmt_s = tmt_s | plus: rv.rating -%}{%- endfor -%}
        {%- assign tmt_a = tmt_s | divided_by: tmt_n | round -%}
        <div class="tmt-card-rating">
          {%- render 'tmt-stars', rating: tmt_a -%}
          <span class="tmt-card-rating__count">({{ tmt_n }})</span>
        </div>
      {%- endif -%}
    {%- endunless -%}"""

OLD_CHILDREN = "    {{ children }}\n  </div>"
NEW_CHILDREN = "    {{ children }}\n" + STARS_BLOCK + "\n  </div>"

if OLD_CHILDREN not in src:
    print("ERROR: injection point '{{ children }}' not found")
    idx = src.find("{{ children }}")
    print(repr(src[max(0,idx-10):idx+50]))
    exit(1)

src = src.replace(OLD_CHILDREN, NEW_CHILDREN, 1)
print("Injection 1 OK — stars block added after {{ children }}")

# ── injection 2: card CSS into {% stylesheet %} ───────────────────────────────
CARD_CSS = """
  .tmt-card-rating {
    display: flex;
    align-items: center;
    gap: 5px;
    padding: 2px 0 2px;
    line-height: 1;
  }
  .tmt-card-rating .tmt-stars { gap: 0; }
  .tmt-card-rating .tmt-star  { font-size: .72rem; }
  .tmt-card-rating__count {
    font-size: .72rem;
    opacity: .6;
    color: currentColor;
  }"""

if "{% stylesheet %}" in src:
    src = src.replace("{% stylesheet %}", "{% stylesheet %}" + CARD_CSS, 1)
    print("Injection 2 OK — CSS added to stylesheet block")
else:
    print("WARNING: no {% stylesheet %} block found — CSS skipped")

# ── push ───────────────────────────────────────────────────────────────────────
payload = {"asset": {"key": "snippets/product-card.liquid", "value": src}}
r2 = httpx.put(f"{API}/themes/{THEME_ID}/assets.json", headers=H, json=payload, timeout=30)
print(f"PUT snippets/product-card.liquid: {r2.status_code}")
if r2.status_code not in (200, 201):
    print(r2.text[:400])
else:
    print("Done — star ratings will now show on all collection cards that have reviews")
