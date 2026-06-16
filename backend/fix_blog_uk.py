"""Fix UK-only shipping mentions in all blog articles."""
import httpx, os, sys, time
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

TOKEN = os.environ["SHOPIFY_TOKEN"]
STORE = os.environ["SHOPIFY_STORE"]
BASE  = f"https://{STORE}/admin/api/2025-01"
H     = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}
HR    = {"X-Shopify-Access-Token": TOKEN}

SUBS = [
    ("Free UK shipping",    "Free worldwide shipping"),
    ("Free UK Shipping",    "Free worldwide shipping"),
    ("every UK order ships <strong>free</strong>",
     "every order ships <strong>free worldwide</strong>"),
    ("every UK order ships free",    "every order ships free worldwide"),
    ("UK orders ship free and arrive in 5–10 working days. We print to order, so allow a day or two for processing.",
     "We ship worldwide — orders typically arrive in 5–12 working days after dispatch."),
    ("UK orders ship free and arrive in 5–10 working days. We print to order, so allow a day or two for p",
     "We ship worldwide — orders typically arrive in 5–12 working days after dispatch."),
    ("Do you ship outside the UK?",  "Where do you ship to?"),
    ("How long does UK delivery take?", "How long does delivery take?"),
    ("Currently we ship to the United Kingdom only. We hope to expand to more countries soon — follow us on social media for updates.",
     "We ship to 180+ countries worldwide — including the US \U0001f1fa\U0001f1f8, UK \U0001f1ec\U0001f1e7 and Germany \U0001f1e9\U0001f1ea. Free shipping on every order, tracked to your door."),
    ("Yes — we ship worldwide. UK orders are free; international orders have a flat rate added at checkout.",
     "Yes — we ship to 180+ countries, including the US \U0001f1fa\U0001f1f8, UK \U0001f1ec\U0001f1e7 and Germany \U0001f1e9\U0001f1ea. Free shipping on every order."),
    ("Yes — UK ships free, international ships at a flat rate that varies by country.",
     "Free worldwide shipping — every order, every country."),
    ("We print to order, so allow a day or two for processing.",
     "Allow 2–5 business days for your order to be processed and dispatched."),
]

def apply(text):
    for old, new in SUBS:
        text = text.replace(old, new)
    return text

# Fetch all blogs then cursor-paginate articles
r = httpx.get(f"{BASE}/blogs.json", headers=HR, timeout=20)
blogs = r.json().get("blogs", [])
print(f"Found {len(blogs)} blog(s)")

total_updated = 0

for blog in blogs:
    blog_id = blog["id"]
    url = f"{BASE}/blogs/{blog_id}/articles.json?limit=250"
    while url:
        r2 = httpx.get(url, headers=HR, timeout=30)
        articles = r2.json().get("articles", [])
        for art in articles:
            body = art.get("body_html") or ""
            new_body = apply(body)
            if new_body != body:
                code = httpx.put(
                    f"{BASE}/blogs/{blog_id}/articles/{art['id']}.json",
                    headers=H,
                    json={"article": {"id": art["id"], "body_html": new_body}},
                    timeout=20
                ).status_code
                status = "OK" if code in (200, 201) else f"ERROR {code}"
                print(f"  [{status}] {blog['handle']}/{art['handle']}")
                total_updated += 1
                time.sleep(0.4)
        # Cursor pagination via Link header
        link = r2.headers.get("Link", "")
        url = None
        for part in link.split(","):
            if 'rel="next"' in part:
                url = part.strip().split(";")[0].strip("<> ")

print(f"\nUpdated {total_updated} articles.")
