"""
tidy_headings.py — shrink the oversized h2/h3 headings on the 6 original
hand-written blog posts so they match the clean generator format.
Only restyles headings; does not change any wording.
"""
import os, re, sys, time, httpx
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv()
STORE = os.environ["SHOPIFY_STORE"]; TOKEN = os.environ["SHOPIFY_TOKEN"]
RH = {"X-Shopify-Access-Token": TOKEN}
H  = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}
API = f"https://{STORE}/admin/api/2025-01"
BLOG_ID = 91457585265

# These titles are the generator's — skip them (already clean)
GENERATOR_TITLES_SUBSTR = ["best ", "christmas gift ideas for tv", "napoleon bonaparte",
                           "princess diana t-shirts", "mother's day", "father's day",
                           "secret santa", "valentine", "graduation gift", "how to style a vintage celebrity",
                           "why bootleg", "what to wear to a watch", "festival fashion",
                           "men's vintage graphic", "women's fan tees", "how to care for your graphic",
                           "building a fan wardrobe"]

H2_STYLE = 'font-size:20px;font-weight:600;line-height:1.3;margin:34px 0 14px;'
H3_STYLE = 'font-size:17px;font-weight:600;line-height:1.3;margin:22px 0 8px;'

def restyle(html):
    # force a modest inline style on every h2 / h3, replacing any existing style attr
    html = re.sub(r'<h2\b[^>]*>', f'<h2 style="{H2_STYLE}">', html, flags=re.I)
    html = re.sub(r'<h3\b[^>]*>', f'<h3 style="{H3_STYLE}">', html, flags=re.I)
    return html

r = httpx.get(f"{API}/blogs/{BLOG_ID}/articles.json?limit=250&fields=id,title,body_html",
              headers=RH, timeout=30)
arts = r.json().get("articles", [])

ONLY_TITLE = "the best vintage celebrity t-shirts to wear in 2026"

for a in arts:
    tl = a["title"].lower()
    if tl != ONLY_TITLE:
        continue  # this run targets only the one originally skipped
    body = a.get("body_html") or ""
    new  = restyle(body)
    if new == body:
        print(f"  skip (no change)  {a['title']}")
        continue
    pr = httpx.put(f"{API}/blogs/{BLOG_ID}/articles/{a['id']}.json", headers=H,
                   json={"article": {"id": a["id"], "body_html": new}}, timeout=30)
    ok = pr.status_code in (200, 201)
    print(f"  {'OK ' if ok else 'ERR'}  {a['title']}")
    time.sleep(0.8)

print("\nDone tidying original-post headings.")
