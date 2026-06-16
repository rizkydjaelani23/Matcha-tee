"""
Etsy shop scraper — scrapes public listing pages, no login, no API.
Saves progress after every product so it's fully resumable.

Usage:
    python etsy_scraper.py

Outputs:
    scraper/progress.json   — raw scraped data + resume state
    scraper/products.csv    — clean spreadsheet ready for review
    scraper/images/<slug>/  — all images per product
"""

import asyncio
import csv
import json
import os
import re
import sys
import time
import urllib.request

from playwright.async_api import async_playwright

sys.stdout.reconfigure(encoding="utf-8")

SHOP_HANDLE = "PrefectShopArt"
SHOP_URL = f"https://www.etsy.com/shop/{SHOP_HANDLE}"
BASE = os.path.dirname(os.path.abspath(__file__))
PROGRESS_FILE = os.path.join(BASE, "progress.json")
IMAGES_DIR = os.path.join(BASE, "images")
CSV_FILE = os.path.join(BASE, "products.csv")
os.makedirs(IMAGES_DIR, exist_ok=True)

# polite delay range between requests (seconds)
PAGE_DELAY = 2.5
PRODUCT_DELAY = 2.0


# ── helpers ──────────────────────────────────────────────────────────────────

def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"listing_urls": [], "scraped": {}, "listings_done": False}


def save_progress(state):
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text[:60]


def download_image(url, dest_path):
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/124.0.0.0 Safari/537.36"
        })
        with urllib.request.urlopen(req, timeout=20) as resp, \
                open(dest_path, "wb") as out:
            out.write(resp.read())
        return True
    except Exception as e:
        print(f"    image download failed: {e}")
        return False


# ── page scrapers ─────────────────────────────────────────────────────────────

async def get_all_listing_urls(page, state):
    """Walk every shop page and collect product URLs."""
    if state["listings_done"]:
        print(f"listings already collected: {len(state['listing_urls'])} URLs")
        return

    urls = []
    page_num = 1
    while True:
        url = f"{SHOP_URL}?page={page_num}"
        print(f"  scanning page {page_num}: {url}")
        await page.goto(url, wait_until="networkidle", timeout=45000)
        await asyncio.sleep(PAGE_DELAY + 1)

        # scroll down to trigger lazy loading
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
        await asyncio.sleep(1)
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(1.5)

        # try multiple selectors for Etsy listing links
        links = await page.eval_on_selector_all(
            "a[href*='/listing/']",
            "els => els.map(e => e.href)"
        )

        # deduplicate and strip query strings
        clean = []
        for l in links:
            base = l.split("?")[0]
            if "/listing/" in base and base not in urls and base not in clean:
                clean.append(base)

        if not clean:
            # debug: dump page title so we know what we got
            title = await page.title()
            print(f"  no listings on page {page_num} (page title: {title}), stopping")
            break

        urls.extend(clean)
        print(f"  found {len(clean)} listings (total so far: {len(urls)})")

        # check if there's a next page button
        next_btn = await page.query_selector(
            "[data-testid='pagination-next-page'], "
            "a[rel='next'], "
            ".wt-btn--next"
        )
        if not next_btn:
            print(f"  no next page button found, done paginating")
            break
        page_num += 1

    state["listing_urls"] = list(dict.fromkeys(urls))  # deduplicate order-preserving
    state["listings_done"] = len(urls) > 0  # only mark done if we actually got URLs
    save_progress(state)
    print(f"\nTotal listing URLs collected: {len(state['listing_urls'])}\n")


async def scrape_product(page, url, state):
    """Scrape a single product page and download its images."""
    if url in state["scraped"]:
        return  # already done

    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
    await asyncio.sleep(PRODUCT_DELAY)

    product = {"url": url, "title": "", "price": "", "description": "",
               "sizes": [], "colors": [], "images": [], "tags": []}

    # title
    try:
        product["title"] = (await page.inner_text("h1")).strip()
    except Exception:
        pass

    # price
    try:
        price_el = await page.query_selector("[data-testid='price-only'] .currency-value,"
                                             " .wt-text-title-larger")
        if price_el:
            product["price"] = (await price_el.inner_text()).strip()
    except Exception:
        pass

    # description
    try:
        desc_el = await page.query_selector("[data-product-details-description-text-content],"
                                            " .wt-content-toggle__body p,"
                                            " #product-details-desc p")
        if desc_el:
            product["description"] = (await desc_el.inner_text()).strip()
        if not product["description"]:
            # fallback: grab all paragraphs in description region
            paras = await page.eval_on_selector_all(
                "p[data-product-details-description-text-content],"
                " [class*='description'] p",
                "els => els.map(e => e.innerText.trim()).filter(Boolean)"
            )
            product["description"] = "\n".join(paras)
    except Exception:
        pass

    # variations (sizes / colors)
    try:
        selects = await page.query_selector_all("select[id*='variation']")
        for sel in selects:
            label_id = await sel.get_attribute("aria-labelledby")
            label_text = ""
            if label_id:
                try:
                    lel = await page.query_selector(f"#{label_id}")
                    if lel:
                        label_text = (await lel.inner_text()).strip().lower()
                except Exception:
                    pass
            opts = await sel.eval_on_selector_all(
                "option:not([value=''])",
                "els => els.map(e => e.innerText.trim()).filter(Boolean)"
            )
            if "size" in label_text or "size" in str(opts).lower():
                product["sizes"] = opts
            elif "color" in label_text or "colour" in label_text:
                product["colors"] = opts
            else:
                if not product["sizes"]:
                    product["sizes"] = opts
    except Exception:
        pass

    # tags
    try:
        tags = await page.eval_on_selector_all(
            "a[href*='/search?q=']",
            "els => els.map(e => e.innerText.trim()).filter(Boolean)"
        )
        product["tags"] = list(dict.fromkeys(tags))[:13]
    except Exception:
        pass

    # images — collect full-size URLs from the listing gallery
    try:
        img_urls = await page.eval_on_selector_all(
            "ul[data-wt-component='listing-page-image-carousel-component'] img,"
            " img[data-src*='il_fullxfull'],"
            " img[src*='il_fullxfull'],"
            " [data-testid='listing-image'] img",
            "els => [...new Set(els.map(e => (e.dataset.src || e.src || '').split('?')[0])))"
            ".filter(u => u && !u.includes('avatar') && !u.includes('shop_icon'))"
        )
        # upgrade to largest available size
        big = []
        for u in img_urls:
            u = re.sub(r"/il_\d+xN\.", "/il_fullxfull.", u)
            u = re.sub(r"/il_\d+x\d+\.", "/il_fullxfull.", u)
            if u and u not in big:
                big.append(u)
        product["images"] = big[:10]
    except Exception:
        pass

    # download images
    if product["title"]:
        slug = slugify(product["title"])
        img_folder = os.path.join(IMAGES_DIR, slug)
        os.makedirs(img_folder, exist_ok=True)
        saved = []
        for i, img_url in enumerate(product["images"]):
            ext = ".jpg"
            dest = os.path.join(img_folder, f"{slug}_{i+1}{ext}")
            if not os.path.exists(dest):
                download_image(img_url, dest)
            if os.path.exists(dest):
                saved.append(dest)
        product["local_images"] = saved
    else:
        product["local_images"] = []

    state["scraped"][url] = product
    save_progress(state)
    return product


# ── CSV export ────────────────────────────────────────────────────────────────

def export_csv(state):
    products = list(state["scraped"].values())
    if not products:
        print("Nothing to export yet.")
        return

    with open(CSV_FILE, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([
            "include_on_shopify",  # fill YES/NO to filter
            "title", "price_gbp", "description",
            "sizes", "colors", "tags",
            "etsy_url", "image_folder",
            "image_1", "image_2", "image_3"
        ])
        for p in products:
            imgs = p.get("local_images", [])
            writer.writerow([
                "YES",
                p["title"],
                p["price"],
                p["description"].replace("\n", " "),
                ", ".join(p["sizes"]),
                ", ".join(p["colors"]),
                ", ".join(p["tags"]),
                p["url"],
                os.path.join(IMAGES_DIR, slugify(p["title"])) if p["title"] else "",
                imgs[0] if len(imgs) > 0 else "",
                imgs[1] if len(imgs) > 1 else "",
                imgs[2] if len(imgs) > 2 else "",
            ])

    print(f"\nCSV exported: {CSV_FILE} ({len(products)} products)")


# ── main ──────────────────────────────────────────────────────────────────────

async def main():
    state = load_progress()
    already_done = len(state["scraped"])
    print(f"Resuming — {already_done} products already scraped\n")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=False,  # visible browser bypasses Cloudflare/bot checks
            args=["--disable-blink-features=AutomationControlled",
                  "--start-maximized"],
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 900},
            locale="en-GB",
            java_script_enabled=True,
        )
        # hide webdriver fingerprint
        await context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        page = await context.new_page()

        # step 1 — collect all listing URLs
        print("=== Step 1: collecting listing URLs ===")
        await get_all_listing_urls(page, state)

        # step 2 — scrape each product
        total = len(state["listing_urls"])
        remaining = [u for u in state["listing_urls"] if u not in state["scraped"]]
        print(f"=== Step 2: scraping {len(remaining)} remaining products "
              f"(of {total} total) ===\n")

        for i, url in enumerate(remaining, 1):
            pct = ((already_done + i) / total) * 100
            print(f"[{already_done + i}/{total}] {pct:.1f}% — {url}")
            try:
                await scrape_product(page, url, state)
                title = state["scraped"].get(url, {}).get("title", "?")
                imgs = len(state["scraped"].get(url, {}).get("local_images", []))
                print(f"  ✓ {title} ({imgs} images)")
            except Exception as e:
                print(f"  ✗ ERROR: {e}")
                state["scraped"][url] = {"url": url, "error": str(e),
                                         "title": "", "price": "",
                                         "description": "", "sizes": [],
                                         "colors": [], "images": [],
                                         "local_images": [], "tags": []}
                save_progress(state)

            # export CSV every 50 products so you can check progress
            if i % 50 == 0:
                export_csv(state)

        await browser.close()

    # final export
    export_csv(state)
    ok = sum(1 for p in state["scraped"].values() if p.get("title"))
    err = sum(1 for p in state["scraped"].values() if p.get("error"))
    print(f"\nDone. {ok} successful, {err} errors.")
    print(f"Spreadsheet: {CSV_FILE}")
    print(f"Images: {IMAGES_DIR}")


if __name__ == "__main__":
    asyncio.run(main())
