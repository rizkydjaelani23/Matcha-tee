"""Create policy pages + starter collections, and dump theme asset list."""
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

PAGES_DIR = os.path.join(os.path.dirname(__file__), "pages")


def create_pages():
    existing = httpx.get(f"{API}/pages.json", headers=H, timeout=20).json()["pages"]
    existing_handles = {p["handle"] for p in existing}
    for fname in sorted(os.listdir(PAGES_DIR)):
        if not fname.endswith(".html"):
            continue
        handle = fname[:-5]
        title = handle.replace("-", " ").title().replace("And", "and") \
            .replace("Faq", "FAQ")
        with open(os.path.join(PAGES_DIR, fname), encoding="utf-8") as f:
            body = f.read()
        # first line may override the title: <!--title: ... -->
        if body.startswith("<!--title:"):
            first, body = body.split("\n", 1)
            title = first.replace("<!--title:", "").replace("-->", "").strip()
        if handle in existing_handles:
            pid = next(p["id"] for p in existing if p["handle"] == handle)
            r = httpx.put(f"{API}/pages/{pid}.json", headers=H, timeout=20,
                          json={"page": {"id": pid, "title": title, "body_html": body}})
            print(f"updated page {handle}: {r.status_code}")
        else:
            r = httpx.post(f"{API}/pages.json", headers=H, timeout=20,
                           json={"page": {"title": title, "handle": handle,
                                          "body_html": body, "published": True}})
            print(f"created page {handle}: {r.status_code}",
                  "" if r.status_code == 201 else r.text[:300])


def create_collections():
    wanted = [
        ("New Releases", "new-releases", "The latest tees to drop. Fresh designs, added regularly."),
        ("Best Sellers", "best-sellers", "Our most-loved designs, as picked by you."),
        ("T-Shirts", "t-shirts", "Every tee in the store."),
        ("Hoodies & Sweatshirts", "hoodies-sweatshirts", "Cosy layers for colder days."),
        ("Tank Tops", "tank-tops", "Sleeveless staples."),
        ("Accessories", "accessories", "Stickers, mugs, totes and more."),
    ]
    existing = httpx.get(f"{API}/custom_collections.json", headers=H, timeout=20) \
        .json()["custom_collections"]
    existing_handles = {c["handle"] for c in existing}
    for title, handle, desc in wanted:
        if handle in existing_handles:
            print(f"collection {handle}: already exists")
            continue
        r = httpx.post(f"{API}/custom_collections.json", headers=H, timeout=20,
                       json={"custom_collection": {
                           "title": title, "handle": handle,
                           "body_html": f"<p>{desc}</p>", "published": True}})
        print(f"created collection {handle}: {r.status_code}",
              "" if r.status_code == 201 else r.text[:300])


def dump_theme_assets():
    r = httpx.get(f"{API}/themes/{THEME_ID}/assets.json", headers=H, timeout=30)
    assets = [a["key"] for a in r.json()["assets"]]
    out = os.path.join(os.path.dirname(__file__), "theme_assets.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(assets, f, indent=1)
    print(f"theme assets: {len(assets)} keys -> {out}")
    for key in ["templates/index.json", "config/settings_data.json",
                "sections/header-group.json", "sections/footer-group.json"]:
        if key in assets:
            rr = httpx.get(f"{API}/themes/{THEME_ID}/assets.json",
                           headers=H, params={"asset[key]": key}, timeout=30)
            val = rr.json()["asset"].get("value", "")
            fn = key.replace("/", "_")
            with open(os.path.join(os.path.dirname(__file__), fn), "w",
                      encoding="utf-8") as f:
                f.write(val)
            print(f"downloaded {key} ({len(val)} bytes)")


if __name__ == "__main__":
    create_pages()
    create_collections()
    dump_theme_assets()
