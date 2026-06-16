"""
fix_product_schema.py
=====================
Fixes GSC structured data warnings by replacing Shopify's built-in
structured_data filter (which omits hasMerchantReturnPolicy, shippingDetails,
and sometimes description) with a custom JSON-LD snippet.

Steps:
  1. Creates snippets/product-schema.liquid with full Product JSON-LD
  2. Patches sections/product-information.liquid to use the new snippet

Run:
  python fix_product_schema.py --dry   # preview, no writes
  python fix_product_schema.py         # apply
"""
import argparse, os, sys
import httpx
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

STORE    = os.environ["SHOPIFY_STORE"]
TOKEN    = os.environ["SHOPIFY_TOKEN"]
HR       = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}
API      = f"https://{STORE}/admin/api/2025-01"
THEME_ID = 143507587185


def get_asset(key):
    r = httpx.get(
        f"{API}/themes/{THEME_ID}/assets.json",
        headers=HR,
        params={"asset[key]": key},
        timeout=30
    )
    return r.json().get("asset", {}).get("value", "")


def put_asset(key, value, dry=False):
    if dry:
        print(f"  [dry] Would upload {key} ({len(value)} chars)")
        return True
    r = httpx.put(
        f"{API}/themes/{THEME_ID}/assets.json",
        headers=HR,
        json={"asset": {"key": key, "value": value}},
        timeout=60
    )
    ok = r.status_code in (200, 201)
    if not ok:
        print(f"  ! Upload failed {r.status_code}: {r.text[:200]}")
    return ok


# --------------------------------------------------------------------------
# 1. Custom product schema snippet
# --------------------------------------------------------------------------
SCHEMA_SNIPPET = """\
{%- comment -%}
  product-schema.liquid
  Full Product JSON-LD with description, hasMerchantReturnPolicy,
  and shippingDetails — fixes GSC structured data warnings.
  Usage: {%- render 'product-schema', product_resource: product -%}
{%- endcomment -%}
{%- liquid
  assign pr = product_resource | default: product
-%}
<script type="application/ld+json">
{
  "@context": "https://schema.org/",
  "@type": "Product",
  "name": {{ pr.title | json }},
  "url": "{{ request.origin }}{{ pr.url }}",
  "description": {{ pr.description | strip_html | strip | truncate: 5000 | json }},
  {% if pr.images.size > 0 -%}
  "image": [
    {%- for img in pr.images -%}
    {{ img | image_url: width: 1200 | prepend: "https:" | json }}{% unless forloop.last %},{% endunless %}
    {%- endfor -%}
  ],
  {%- endif %}
  "brand": {
    "@type": "Brand",
    "name": {{ shop.name | json }}
  },
  {%- if pr.metafields.reviews.rating.value != blank %}
  "aggregateRating": {
    "@type": "AggregateRating",
    "ratingValue": "{{ pr.metafields.reviews.rating.value }}",
    "reviewCount": "{{ pr.metafields.reviews.rating_count.value | default: 1 }}"
  },
  {%- endif %}
  "offers": [
    {%- for variant in pr.variants %}
    {
      "@type": "Offer",
      "name": {{ variant.title | json }},
      "sku": {{ variant.sku | escape | json }},
      "price": "{{ variant.price | money_without_currency | remove: ',' }}",
      "priceCurrency": {{ cart.currency.iso_code | json }},
      "availability": "{% if variant.available %}https://schema.org/InStock{% else %}https://schema.org/OutOfStock{% endif %}",
      "itemCondition": "https://schema.org/NewCondition",
      "url": "{{ request.origin }}{{ pr.url }}?variant={{ variant.id }}",
      "seller": {
        "@type": "Organization",
        "name": {{ shop.name | json }}
      },
      "hasMerchantReturnPolicy": {
        "@type": "MerchantReturnPolicy",
        "applicableCountry": "GB",
        "returnPolicyCategory": "https://schema.org/MerchantReturnFiniteReturnWindow",
        "merchantReturnDays": 30,
        "returnMethod": "https://schema.org/ReturnByMail",
        "returnFees": "https://schema.org/FreeReturn"
      },
      "shippingDetails": {
        "@type": "OfferShippingDetails",
        "shippingRate": {
          "@type": "MonetaryAmount",
          "value": "3.99",
          "currency": "GBP"
        },
        "shippingDestination": {
          "@type": "DefinedRegion",
          "addressCountry": "GB"
        },
        "deliveryTime": {
          "@type": "ShippingDeliveryTime",
          "handlingTime": {
            "@type": "QuantitativeValue",
            "minValue": 3,
            "maxValue": 7,
            "unitCode": "DAY"
          },
          "transitTime": {
            "@type": "QuantitativeValue",
            "minValue": 2,
            "maxValue": 5,
            "unitCode": "DAY"
          }
        }
      }
    }{% unless forloop.last %},{% endunless %}
    {%- endfor %}
  ]
}
</script>
"""

# The old block to replace in product-information.liquid
OLD_BLOCK = '<script type="application/ld+json">\n  {{ closest.product | structured_data }}\n  </script>'
NEW_BLOCK = "{%- render 'product-schema', product_resource: closest.product -%}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()

    mode = "DRY RUN" if args.dry else "LIVE"
    print(f"[{mode}] Fixing product structured data\n")

    # -- Step 1: upload the schema snippet --
    print("Step 1: uploading snippets/product-schema.liquid")
    ok1 = put_asset("snippets/product-schema.liquid", SCHEMA_SNIPPET, dry=args.dry)
    print(f"  {'OK' if ok1 else 'FAILED'}")

    # -- Step 2: patch product-information.liquid --
    print("\nStep 2: patching sections/product-information.liquid")
    content = get_asset("sections/product-information.liquid")
    if not content:
        print("  ! Could not fetch product-information.liquid")
        return

    if OLD_BLOCK not in content:
        # Try alternate whitespace
        alt = '<script type="application/ld+json">\n    {{ closest.product | structured_data }}\n  </script>'
        if alt in content:
            old = alt
        else:
            # Find any variant
            import re
            m = re.search(r'<script type="application/ld\+json">.*?structured_data.*?</script>', content, re.DOTALL)
            if m:
                old = m.group(0)
                print(f"  Found variant block: {repr(old[:80])}")
            else:
                print("  ! Could not locate structured_data block — already patched or different format")
                print("    Searching for 'structured_data' in content...")
                idx = content.find("structured_data")
                if idx >= 0:
                    print(f"    Context: {repr(content[max(0,idx-50):idx+100])}")
                return
    else:
        old = OLD_BLOCK

    patched = content.replace(old, NEW_BLOCK, 1)
    if patched == content:
        print("  ! Replacement had no effect — content unchanged")
        return

    print(f"  Replaced {len(old)} chars with {len(NEW_BLOCK)} chars")
    ok2 = put_asset("sections/product-information.liquid", patched, dry=args.dry)
    print(f"  {'OK' if ok2 else 'FAILED'}")

    if not args.dry:
        print("\nDone. Changes are live — verify with Google's Rich Results Test:")
        print("  https://search.google.com/test/rich-results")


if __name__ == "__main__":
    main()
