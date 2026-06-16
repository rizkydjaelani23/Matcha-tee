"""Create header and footer navigation menus."""
import os, sys, time
import httpx
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

STORE = os.environ["SHOPIFY_STORE"]
H  = {"X-Shopify-Access-Token": os.environ["SHOPIFY_TOKEN"], "Content-Type": "application/json"}
RH = {"X-Shopify-Access-Token": os.environ["SHOPIFY_TOKEN"]}
API = f"https://{STORE}/admin/api/2025-01"


def req(method, path, **kwargs):
    r = httpx.request(method, f"{API}{path}", headers=H if method != "GET" else RH,
                      timeout=30, **kwargs)
    try:
        body = r.json()
    except Exception:
        body = r.text
    return r.status_code, body


def delete_existing(handle):
    status, data = req("GET", "/menus.json")
    for m in (data.get("menus", []) if isinstance(data, dict) else []):
        if m["handle"] == handle:
            s, _ = req("DELETE", f"/menus/{m['id']}.json")
            print(f"  Deleted existing '{handle}' menu (id {m['id']}): {s}")
            time.sleep(0.3)


def create_menu(title, handle, items):
    delete_existing(handle)
    time.sleep(0.3)
    status, body = req("POST", "/menus.json", json={"menu": {"title": title, "handle": handle, "items": items}})
    print(f"  POST /menus.json ({handle}): {status}")
    if status not in (200, 201):
        print(f"    Response: {body}")
        return False
    return True


# Header — Shop All with dropdown, New Releases, Best Sellers
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
    {"title": "New Releases", "url": "/collections/new-releases", "type": "http"},
    {"title": "Best Sellers", "url": "/collections/best-sellers",  "type": "http"},
]

# Footer
footer_items = [
    {"title": "FAQ",                "url": "/pages/faq",                  "type": "http"},
    {"title": "Shipping Policy",    "url": "/pages/shipping-policy",      "type": "http"},
    {"title": "Returns & Refunds",  "url": "/pages/return-policy",        "type": "http"},
    {"title": "Terms & Conditions", "url": "/pages/terms-and-conditions", "type": "http"},
    {"title": "Privacy Policy",     "url": "/pages/privacy-policy",       "type": "http"},
    {"title": "Contact Us",         "url": "/pages/contact",              "type": "http"},
    {"title": "Affiliates",         "url": "/pages/affiliates",           "type": "http"},
    {"title": "Wholesale",          "url": "/pages/wholesale",            "type": "http"},
]

print("Creating main-menu...")
ok1 = create_menu("Main Menu", "main-menu", header_items)

print("Creating footer menu...")
ok2 = create_menu("Footer", "footer", footer_items)

if ok1 and ok2:
    print("\nAll menus created successfully.")
else:
    print("\nOne or more menus failed — check output above.")

# Customer email note
print("""
Note: customer_email (406 earlier) cannot be changed via REST API.
To update it: Shopify Admin → Settings → Notifications → Sender email
""")
