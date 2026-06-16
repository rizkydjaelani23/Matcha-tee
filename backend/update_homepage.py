"""Push TeeFury-style homepage structure + footer links to the Horizon theme."""
import json
import os
import sys

import httpx
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

STORE = os.environ["SHOPIFY_STORE"]
H = {"X-Shopify-Access-Token": os.environ["SHOPIFY_TOKEN"],
     "Content-Type": "application/json"}
API = f"https://{STORE}/admin/api/2025-01"
THEME_ID = 143507587185
BASE = os.path.dirname(__file__)


def text_block(text, preset="rte", align="left", extra=None):
    s = {"text": text, "type_preset": preset, "alignment": align,
         "width": "100%", "font": "var(--font-body--family)"}
    if extra:
        s.update(extra)
    return {"type": "text", "settings": s, "blocks": {}}


def product_list_section(collection_handle, name):
    """Clone of Horizon's stock product-list structure, pointed at a collection."""
    return {
        "type": "product-list",
        "blocks": {
            "static-header": {
                "type": "_product-list-content",
                "static": True,
                "settings": {
                    "content_direction": "row",
                    "horizontal_alignment": "space-between",
                    "vertical_alignment": "flex-end",
                    "align_baseline": True,
                    "gap": 12, "width": "fill", "width_mobile": "fill",
                    "height": "fit", "inherit_color_scheme": True,
                },
                "blocks": {
                    "pl_title": {
                        "type": "_product-list-text",
                        "settings": {
                            "text": "<h3>{{ closest.collection.title }}</h3>",
                            "type_preset": "h4", "alignment": "left",
                            "width": "fit-content",
                            "font": "var(--font-body--family)",
                            "color": "var(--color-foreground)",
                        },
                        "blocks": {},
                    },
                    "pl_viewall": {
                        "type": "_product-list-button",
                        "settings": {"label": "View all", "style_class": "link",
                                     "width": "fit-content",
                                     "width_mobile": "fit-content"},
                        "blocks": {},
                    },
                },
                "block_order": ["pl_title", "pl_viewall"],
            },
            "static-product-card": {
                "type": "_product-card",
                "static": True,
                "settings": {"product_card_gap": 4, "inherit_color_scheme": True},
                "blocks": {
                    "pc_gallery": {"type": "_product-card-gallery",
                                   "settings": {"image_ratio": "adapt"},
                                   "blocks": {}},
                    "pc_title": {"type": "product-title",
                                 "settings": {"width": "100%", "type_preset": "rte",
                                              "font_size": "1rem",
                                              "padding-block-start": 4},
                                 "blocks": {}},
                    "pc_price": {"type": "price",
                                 "settings": {"show_sale_price_first": True,
                                              "type_preset": "h6", "width": "100%",
                                              "font_size": "1rem"},
                                 "blocks": {}},
                },
                "block_order": ["pc_gallery", "pc_title", "pc_price"],
            },
        },
        "name": name,
        "settings": {
            "collection": collection_handle,
            "layout_type": "grid",
            "carousel_on_mobile": True,
            "max_products": 8,
            "columns": 4,
            "mobile_columns": "2",
            "columns_gap": 8,
            "rows_gap": 24,
            "section_width": "page-width",
            "color_scheme": "scheme-1",
            "padding-block-start": 48,
            "padding-block-end": 48,
        },
    }


TRUST_HTML = """
<div style="display:flex;gap:40px;justify-content:center;flex-wrap:wrap;text-align:center;padding:12px 0;">
  <div style="min-width:200px;">
    <p style="font-size:1.05rem;"><strong>Tracked UK delivery</strong><br>
    <span style="opacity:.75;">Every order ships with tracking</span></p>
  </div>
  <div style="min-width:200px;">
    <p style="font-size:1.05rem;"><strong>Secure checkout</strong><br>
    <span style="opacity:.75;">Safe payments, every time</span></p>
  </div>
  <div style="min-width:200px;">
    <p style="font-size:1.05rem;"><strong>30-day returns</strong><br>
    <span style="opacity:.75;">Easy returns &amp; exchanges</span></p>
  </div>
</div>
"""

index_template = {
    "sections": {
        "hero_main": {
            "type": "hero",
            "blocks": {
                "hero_heading": text_block(
                    "<h1>Statement tees, made to order</h1>", "h1", "center",
                    {"width": "fit-content",
                     "color": "var(--color-foreground-heading)"}),
                "hero_sub": text_block(
                    "<p>Original designs, printed on premium cotton and shipped "
                    "tracked to your door.</p>", "rte", "center",
                    {"width": "fit-content"}),
                "hero_btn_new": {
                    "type": "button",
                    "settings": {"label": "Shop New Releases",
                                 "link": "shopify://collections/new-releases",
                                 "style_class": "button-secondary",
                                 "width": "fit-content",
                                 "width_mobile": "fit-content"},
                    "blocks": {},
                },
                "hero_btn_best": {
                    "type": "button",
                    "settings": {"label": "Best Sellers",
                                 "link": "shopify://collections/best-sellers",
                                 "style_class": "button-secondary",
                                 "width": "fit-content",
                                 "width_mobile": "fit-content"},
                    "blocks": {},
                },
            },
            "block_order": ["hero_heading", "hero_sub",
                            "hero_btn_new", "hero_btn_best"],
            "name": "Hero",
            "settings": {
                "media_type_1": "image",
                "media_type_2": "image",
                "content_direction": "column",
                "vertical_on_mobile": True,
                "horizontal_alignment_flex_direction_column": "center",
                "vertical_alignment_flex_direction_column": "center",
                "gap": 16,
                "section_width": "full-width",
                "section_height": "medium",
                "color_scheme": "scheme-6",
                "toggle_overlay": True,
                "overlay_color": "#12121266",
                "overlay_style": "solid",
                "padding-block-start": 96,
                "padding-block-end": 96,
            },
        },
        "marquee_strip": {
            "type": "marquee",
            "blocks": {
                "marquee_text": {
                    "type": "text",
                    "settings": {
                        "text": "<p>New designs weekly &nbsp;•&nbsp; Tracked shipping "
                                "to the UK &nbsp;•&nbsp; Printed to order &nbsp;•&nbsp; "
                                "Easy 30-day returns &nbsp;•&nbsp;</p>",
                        "type_preset": "custom",
                        "font": "var(--font-body--family)",
                        "font_size": "var(--font-size--h4)",
                        "line_height": "tight",
                        "wrap": "nowrap",
                        "width": "fit-content",
                    },
                    "blocks": {},
                }
            },
            "block_order": ["marquee_text"],
            "name": "Marquee",
            "settings": {"movement_direction": "normal",
                         "color_scheme": "scheme-4",
                         "padding-block-start": 16, "padding-block-end": 16,
                         "gap_between_elements": 24},
        },
        "new_releases": product_list_section("new-releases", "New Releases"),
        "shop_by_category": {
            "type": "collection-list",
            "blocks": {
                "cat_header": {
                    "type": "group",
                    "settings": {"content_direction": "column", "gap": 16,
                                 "width": "fill", "width_mobile": "fill",
                                 "height": "fit", "inherit_color_scheme": True},
                    "blocks": {
                        "cat_heading": text_block("<h3>Shop by category</h3>",
                                                  "h4", "left",
                                                  {"width": "fit-content",
                                                   "padding-block-end": 16}),
                    },
                    "block_order": ["cat_heading"],
                },
                "static-collection-card": {
                    "type": "_collection-card",
                    "static": True,
                    "settings": {"horizontal_alignment": "flex-start",
                                 "vertical_alignment": "flex-end",
                                 "placement": "on_image",
                                 "inherit_color_scheme": True},
                    "blocks": {
                        "collection-card-image": {
                            "type": "_collection-card-image",
                            "static": True,
                            "settings": {"image_ratio": "adapt"},
                        },
                        "collection-title": {
                            "type": "collection-title",
                            "settings": {"type_preset": "rte",
                                         "width": "fit-content",
                                         "alignment": "left",
                                         "background": True,
                                         "background_color": "#ffffff",
                                         "padding-block-start": 4,
                                         "padding-block-end": 4,
                                         "padding-inline-start": 8,
                                         "padding-inline-end": 8},
                        },
                    },
                },
            },
            "block_order": ["cat_header"],
            "name": "Shop by category",
            "settings": {
                "collection_list": ["t-shirts", "hoodies-sweatshirts",
                                    "tank-tops", "accessories"],
                "layout_type": "grid",
                "columns": 4,
                "mobile_columns": "2",
                "columns_gap": 8,
                "rows_gap": 8,
                "section_width": "page-width",
                "padding-block-start": 24,
                "padding-block-end": 24,
            },
        },
        "best_sellers": product_list_section("best-sellers", "Best Sellers"),
        "trust_badges": {
            "type": "custom-liquid",
            "name": "Trust badges",
            "settings": {"custom_liquid": TRUST_HTML,
                         "color_scheme": "scheme-2",
                         "section_width": "full-width",
                         "padding-block-start": 32,
                         "padding-block-end": 32},
        },
    },
    "order": ["hero_main", "marquee_strip", "new_releases",
              "shop_by_category", "best_sellers", "trust_badges"],
}


def put_asset(key, value):
    r = httpx.put(f"{API}/themes/{THEME_ID}/assets.json", headers=H, timeout=60,
                  json={"asset": {"key": key, "value": value}})
    print(f"PUT {key}: {r.status_code}", "" if r.status_code == 200 else r.text[:500])
    return r.status_code == 200


def update_footer():
    with open(os.path.join(BASE, "sections_footer-group.json"), encoding="utf-8") as f:
        footer = json.load(f)
    fsec = footer["sections"]["footer_m9NzUG"]
    links = [
        ("Shipping Policy", "/pages/shipping-policy"),
        ("Return & Refund Policy", "/pages/return-policy"),
        ("Wholesale", "/pages/wholesale"),
        ("Affiliates", "/pages/affiliates"),
        ("Privacy Policy", "/pages/privacy-policy"),
        ("Terms & Conditions", "/pages/terms-and-conditions"),
    ]
    link_blocks = {
        "links_heading": text_block("<h4>Help &amp; info</h4>", "h6", "left",
                                    {"width": "fit-content"})
    }
    order = ["links_heading"]
    for i, (label, url) in enumerate(links):
        key = f"link_{i}"
        link_blocks[key] = text_block(
            f'<p><a href="{url}">{label}</a></p>', "rte", "left",
            {"width": "fit-content"})
        order.append(key)
    fsec["blocks"]["group_links"] = {
        "type": "group",
        "settings": {"content_direction": "column", "gap": 8,
                     "width": "fill", "width_mobile": "fill",
                     "height": "fit", "inherit_color_scheme": True},
        "blocks": link_blocks,
        "block_order": order,
    }
    fsec["block_order"] = ["group_H6VpwJ", "group_links", "email_signup_crihX7"]
    put_asset("sections/footer-group.json", json.dumps(footer, indent=2))


def try_update_main_menu():
    gql = f"https://{STORE}/admin/api/2025-01/graphql.json"
    q = {"query": "{ menus(first: 10) { nodes { id handle title items { id title url } } } }"}
    r = httpx.post(gql, headers=H, json=q, timeout=30)
    data = r.json()
    if "errors" in data or not data.get("data"):
        print("menus query failed:", json.dumps(data)[:400])
        return
    menus = data["data"]["menus"]["nodes"]
    main = next((m for m in menus if m["handle"] == "main-menu"), None)
    print("menus found:", [(m["handle"], m["title"]) for m in menus])
    if not main:
        return
    items = [
        {"title": "New Releases", "type": "COLLECTION",
         "resourceId": None, "url": "/collections/new-releases"},
        {"title": "Best Sellers", "type": "HTTP", "url": "/collections/best-sellers"},
        {"title": "T-Shirts", "type": "HTTP", "url": "/collections/t-shirts"},
        {"title": "Hoodies", "type": "HTTP", "url": "/collections/hoodies-sweatshirts"},
        {"title": "Tank Tops", "type": "HTTP", "url": "/collections/tank-tops"},
        {"title": "Accessories", "type": "HTTP", "url": "/collections/accessories"},
        {"title": "Wholesale", "type": "HTTP", "url": "/pages/wholesale"},
        {"title": "Affiliates", "type": "HTTP", "url": "/pages/affiliates"},
    ]
    items = [{k: v for k, v in it.items() if v is not None} for it in items]
    mut = {
        "query": """
        mutation menuUpdate($id: ID!, $title: String!, $handle: String!, $items: [MenuItemUpdateInput!]!) {
          menuUpdate(id: $id, title: $title, handle: $handle, items: $items) {
            menu { id }
            userErrors { field message }
          }
        }""",
        "variables": {"id": main["id"], "title": "Main menu",
                      "handle": "main-menu", "items": items},
    }
    r = httpx.post(gql, headers=H, json=mut, timeout=30)
    print("menuUpdate:", json.dumps(r.json())[:500])


if __name__ == "__main__":
    put_asset("templates/index.json", json.dumps(index_template, indent=2))
    update_footer()
    try_update_main_menu()
