"""Replace all UK-only shipping mentions with worldwide messaging across the store."""
import httpx, os, json, sys, time
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

TOKEN = os.environ["SHOPIFY_TOKEN"]
STORE = os.environ["SHOPIFY_STORE"]
THEME = 143507587185
BASE  = f"https://{STORE}/admin/api/2025-01"
H     = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}
HR    = {"X-Shopify-Access-Token": TOKEN}

def put_page(page_id, body_html):
    r = httpx.put(f"{BASE}/pages/{page_id}.json", headers=H,
        json={"page": {"id": page_id, "body_html": body_html}}, timeout=20)
    return r.status_code

def put_article(blog_id, article_id, body_html):
    r = httpx.put(f"{BASE}/blogs/{blog_id}/articles/{article_id}.json", headers=H,
        json={"article": {"id": article_id, "body_html": body_html}}, timeout=20)
    return r.status_code

def put_asset(key, value):
    r = httpx.put(f"{BASE}/themes/{THEME}/assets.json", headers=H,
        json={"asset": {"key": key, "value": value}}, timeout=20)
    return r.status_code

def apply(text, replacements):
    for old, new in replacements:
        text = text.replace(old, new)
    return text

# ── Replacements ──────────────────────────────────────────────────────────────

BLOG_SUBS = [
    # Product card subtitles
    ("Free UK shipping",    "Free worldwide shipping"),
    ("Free UK Shipping",    "Free worldwide shipping"),
    # Body: every UK order ships free
    ("every UK order ships <strong>free</strong>, usu",
     "every order ships <strong>free worldwide</strong>, usu"),
    ("every UK order ships free",    "every order ships free worldwide"),
    # Delivery time blocks
    ("UK orders ship free and arrive in 5–10 working days. We print to order, so allow a day or two for processing.",
     "We ship worldwide — orders typically arrive in 5–12 working days after dispatch."),
    ("UK orders ship free and arrive in 5–10 working days. We print to order, so allow a day or two for p",
     "We ship worldwide — orders typically arrive in 5–12 working days after dispatch."),
    # FAQ questions
    ("Do you ship outside the UK?",  "Where do you ship to?"),
    ("How long does UK delivery take?", "How long does delivery take?"),
    # FAQ answers — UK only (wrong)
    ("Currently we ship to the United Kingdom only. We hope to expand to more countries soon — follow us on social media for updates.",
     "We ship to 180+ countries worldwide — including the US \U0001f1fa\U0001f1f8, UK \U0001f1ec\U0001f1e7 and Germany \U0001f1e9\U0001f1ea. Free shipping on every order, tracked to your door."),
    # FAQ answers — already partially correct
    ("Yes — we ship worldwide. UK orders are free; international orders have a flat rate added at checkout.",
     "Yes — we ship to 180+ countries, including the US \U0001f1fa\U0001f1f8, UK \U0001f1ec\U0001f1e7 and Germany \U0001f1e9\U0001f1ea. Free shipping on every order."),
    ("Yes — UK ships free, international ships at a flat rate that varies by country.",
     "Free worldwide shipping — every order, every country."),
    # Remove stray print references
    ("We print to order, so allow a day or two for processing.",
     "Allow 2–5 business days for your order to be processed and dispatched."),
]

PAGE_SUBS = {
    "about": [
        ("<strong>Fast UK delivery</strong>",
         "<strong>Worldwide tracked delivery</strong>"),
        ("Fast UK delivery",
         "Worldwide tracked delivery"),
        ("hassle-free 30-day returns",
         "24-hour happiness guarantee"),
    ],
    "faq": [
        ("Do you ship outside the UK?",
         "Where do you ship to?"),
        ("Currently we ship to the United Kingdom only. We hope to expand to more countries soon — follow us on social media for updates.",
         "We ship to 180+ countries worldwide — including the US \U0001f1fa\U0001f1f8, UK \U0001f1ec\U0001f1e7 and Germany \U0001f1e9\U0001f1ea. Free shipping on every order, tracked to your door."),
        ("within the UK</strong>",
         "worldwide</strong>"),
        ("3–7 days within the UK",
         "5–12 business days depending on your location"),
    ],
    "shipping-policy": [
        ("Delivery to the UK",
         "Worldwide Delivery"),
        ("United Kingdom",
         "worldwide"),
        ("UK customers",
         "customers worldwide"),
        ("within the UK",
         "worldwide"),
        ("UK orders",
         "all orders"),
        ("to the UK",
         "worldwide"),
    ],
    "terms-and-conditions": [
        ("selling to customers in the United Kingdom",
         "selling to customers worldwide"),
        ("United Kingdom",
         "worldwide"),
    ],
}

# ── Fix pages ─────────────────────────────────────────────────────────────────
print("=== Fixing pages ===")
r = httpx.get(f"{BASE}/pages.json", headers=HR, params={"limit": 50}, timeout=20)
for page in r.json().get("pages", []):
    handle = page["handle"]
    if handle not in PAGE_SUBS:
        continue
    body = page.get("body_html") or ""
    new_body = apply(body, PAGE_SUBS[handle])
    if new_body != body:
        code = put_page(page["id"], new_body)
        print(f"  [{code}] {handle} (id={page['id']})")
        time.sleep(0.5)
    else:
        print(f"  [skip] {handle} — no changes needed")

# ── Fix blog articles ─────────────────────────────────────────────────────────
print("\n=== Fixing blog articles ===")
r = httpx.get(f"{BASE}/blogs.json", headers=HR, timeout=20)
blogs = r.json().get("blogs", [])
for blog in blogs:
    blog_id = blog["id"]
    page = 1
    while True:
        r2 = httpx.get(f"{BASE}/blogs/{blog_id}/articles.json", headers=HR,
            params={"limit": 50, "page": page}, timeout=20)
        articles = r2.json().get("articles", [])
        if not articles:
            break
        for art in articles:
            body = art.get("body_html") or ""
            new_body = apply(body, BLOG_SUBS)
            if new_body != body:
                code = put_article(blog_id, art["id"], new_body)
                print(f"  [{code}] {blog['handle']}/{art['handle']}")
                time.sleep(0.4)
        page += 1

# ── Fix homepage trust_badges section ────────────────────────────────────────
print("\n=== Fixing homepage trust badges ===")
r = httpx.get(f"{BASE}/themes/{THEME}/assets.json", headers=HR,
    params={"asset[key]": "templates/index.json"}, timeout=20)
raw = r.json()["asset"]["value"]
parsed = json.loads(raw)

tb = parsed["sections"].get("trust_badges", {})
for block_key, block in tb.get("blocks", {}).items():
    liq = block.get("settings", {}).get("custom_liquid", "")
    if "UK" in liq or "United Kingdom" in liq:
        new_liq = apply(liq, [
            ("UK", "worldwide"),
            ("United Kingdom", "worldwide"),
            ("Free UK", "Free worldwide"),
        ])
        parsed["sections"]["trust_badges"]["blocks"][block_key]["settings"]["custom_liquid"] = new_liq
        print(f"  Updated trust_badges block: {block_key}")

code = put_asset("templates/index.json", json.dumps(parsed, indent=2))
print(f"  [{code}] templates/index.json")

print("\nDone.")
