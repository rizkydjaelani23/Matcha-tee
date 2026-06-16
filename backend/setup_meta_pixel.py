"""
setup_meta_pixel.py
=====================
Installs Meta Pixel with full e-commerce event tracking in the Horizon theme.

Events tracked:
  - PageView         : every page
  - ViewContent      : product pages (title, price, sku, category)
  - AddToCart        : when customer taps Add to Cart
  - InitiateCheckout : on cart page checkout click
  - Purchase         : order confirmation page

Deploys two assets:
  1. snippets/tmt-meta-pixel.liquid  — base pixel + PageView + page-type events
  2. layout/theme.liquid             — updated to include the snippet in <head>
"""
import os, sys, httpx, re
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
STORE  = os.environ["SHOPIFY_STORE"]
TOKEN  = os.environ["SHOPIFY_TOKEN"]
PIXEL  = os.environ["META_PIXEL_ID"]
H      = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}
HR     = {"X-Shopify-Access-Token": TOKEN}
API    = f"https://{STORE}/admin/api/2025-01"
THEME  = 143507587185

# ── Pixel snippet ─────────────────────────────────────────────────────────────
PIXEL_SNIPPET = f"""{{% comment %}} Meta Pixel v2 — tmt-meta-pixel.liquid  Pixel: {PIXEL} {{% endcomment %}}
<!-- Meta Pixel Base -->
<script>
!function(f,b,e,v,n,t,s){{if(f.fbq)return;n=f.fbq=function(){{n.callMethod?
n.callMethod.apply(n,arguments):n.queue.push(arguments)}};if(!f._fbq)f._fbq=n;
n.push=n;n.loaded=!0;n.version='2.0';n.queue=[];t=b.createElement(e);t.async=!0;
t.src=v;s=b.getElementsByTagName(e)[0];s.parentNode.insertBefore(t,s)}}(window,
document,'script','https://connect.facebook.net/en_US/fbevents.js');
fbq('init', '{PIXEL}');
fbq('track', 'PageView');
</script>
<noscript><img height="1" width="1" style="display:none"
  src="https://www.facebook.com/tr?id={PIXEL}&ev=PageView&noscript=1"/></noscript>

<!-- Meta Pixel — E-commerce Events -->
<script>
(function() {{

  // ── ViewContent: product pages ─────────────────────────────────────────────
  {{% if template.name == 'product' %}}
  fbq('track', 'ViewContent', {{
    content_ids:   ['{{% raw %}}{{{{ product.id }}}}{{% endraw %}}'],
    content_name:  '{{% raw %}}{{{{ product.title | escape }}}}{{% endraw %}}',
    content_type:  'product',
    value:         parseFloat('{{% raw %}}{{{{ product.price | money_without_currency | remove: "," }}}}{{% endraw %}}') || 0,
    currency:      'GBP',
    content_category: '{{% raw %}}{{{{ product.type | escape }}}}{{% endraw %}}'
  }});
  {{% endif %}}

  // ── AddToCart: product pages ───────────────────────────────────────────────
  {{% if template.name == 'product' %}}
  document.addEventListener('DOMContentLoaded', function() {{
    function hookAtc() {{
      document.querySelectorAll('form[action*="/cart/add"]').forEach(function(form) {{
        if (form._tmtHooked) return;
        form._tmtHooked = true;
        form.addEventListener('submit', function() {{
          fbq('track', 'AddToCart', {{
            content_ids:  ['{{% raw %}}{{{{ product.id }}}}{{% endraw %}}'],
            content_name: '{{% raw %}}{{{{ product.title | escape }}}}{{% endraw %}}',
            content_type: 'product',
            value:        parseFloat('{{% raw %}}{{{{ product.selected_or_first_available_variant.price | money_without_currency | remove: "," }}}}{{% endraw %}}') || 0,
            currency:     'GBP'
          }});
        }});
      }});
    }}
    hookAtc();
    new MutationObserver(hookAtc).observe(document.body, {{childList:true,subtree:true}});
  }});
  {{% endif %}}

  // ── InitiateCheckout: cart page ────────────────────────────────────────────
  {{% if template.name == 'cart' %}}
  document.addEventListener('DOMContentLoaded', function() {{
    document.querySelectorAll('[name="checkout"],[href*="/checkout"]').forEach(function(el) {{
      el.addEventListener('click', function() {{
        fbq('track', 'InitiateCheckout', {{
          value:     parseFloat('{{% raw %}}{{{{ cart.total_price | money_without_currency | remove: "," }}}}{{% endraw %}}') || 0,
          currency:  'GBP',
          num_items: {{% raw %}}{{{{ cart.item_count }}}}{{% endraw %}}
        }});
      }});
    }});
  }});
  {{% endif %}}

  // ── Purchase: order confirmation ───────────────────────────────────────────
  {{% if first_time_accessed and checkout.order_id %}}
  fbq('track', 'Purchase', {{
    value:       parseFloat('{{% raw %}}{{{{ checkout.total_price | money_without_currency | remove: "," }}}}{{% endraw %}}') || 0,
    currency:    'GBP',
    num_items:   {{% raw %}}{{{{ checkout.line_items.size }}}}{{% endraw %}},
    order_id:    '{{% raw %}}{{{{ checkout.order_id }}}}{{% endraw %}}',
    content_ids: [{{% raw %}}{{%- for item in checkout.line_items -%}}'{{{{ item.product_id }}}}'{{%- unless forloop.last -%}},{{%- endunless -%}}{{%- endfor -%}}{{% endraw %}}],
    content_type:'product'
  }});
  {{% endif %}}

}})();
</script>"""

# ── Get current theme.liquid ──────────────────────────────────────────────────
r = httpx.get(
    f"{API}/themes/{THEME}/assets.json",
    headers=HR,
    params={"asset[key]": "layout/theme.liquid"},
    timeout=30,
)
if r.status_code != 200:
    print(f"Could not fetch theme.liquid: {r.status_code}")
    sys.exit(1)

theme_liquid = r.json()["asset"]["value"]

# ── Deploy pixel snippet ──────────────────────────────────────────────────────
r2 = httpx.put(
    f"{API}/themes/{THEME}/assets.json",
    headers=H,
    json={"asset": {"key": "snippets/tmt-meta-pixel.liquid", "value": PIXEL_SNIPPET}},
    timeout=30,
)
print(f"PUT snippets/tmt-meta-pixel.liquid: {r2.status_code}")
if r2.status_code not in (200, 201):
    print(r2.text[:300])
    sys.exit(1)

# ── Inject include into theme.liquid just before </head> ─────────────────────
INCLUDE_TAG = "{%- render 'tmt-meta-pixel' -%}"
if INCLUDE_TAG in theme_liquid:
    print("theme.liquid already includes pixel snippet — already injected.")
else:
    updated = theme_liquid.replace("</head>", f"  {INCLUDE_TAG}\n</head>", 1)
    r3 = httpx.put(
        f"{API}/themes/{THEME}/assets.json",
        headers=H,
        json={"asset": {"key": "layout/theme.liquid", "value": updated}},
        timeout=30,
    )
    print(f"PUT layout/theme.liquid: {r3.status_code}")
    if r3.status_code not in (200, 201):
        print(r3.text[:300])
    else:
        print("Pixel injected into <head>.")

print(f"\nMeta Pixel {PIXEL} deployed.")
