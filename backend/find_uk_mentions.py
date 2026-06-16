"""Find every mention of UK / Free UK shipping across the entire store."""
import httpx, os, json, sys, re
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

TOKEN = os.environ["SHOPIFY_TOKEN"]
STORE = os.environ["SHOPIFY_STORE"]
THEME = 143507587185
H     = {"X-Shopify-Access-Token": TOKEN}
BASE  = f"https://{STORE}/admin/api/2025-01"

PATTERN = re.compile(r'(free\s+uk|uk\s+shipping|united\s+kingdom|ship.*uk|uk.*ship|deliver.*uk|uk.*deliver)', re.IGNORECASE)

results = {}

# 1. Theme assets
print("Scanning theme assets...")
r = httpx.get(f"{BASE}/themes/{THEME}/assets.json", headers=H, timeout=30)
assets = [a for a in r.json().get("assets", []) if a["key"].endswith((".liquid",".json",".css",".js"))]
for a in assets:
    key = a["key"]
    r2 = httpx.get(f"{BASE}/themes/{THEME}/assets.json", headers=H, params={"asset[key]": key}, timeout=20)
    val = r2.json().get("asset", {}).get("value", "")
    matches = []
    for i, line in enumerate(val.splitlines(), 1):
        if PATTERN.search(line):
            matches.append((i, line.strip()[:120]))
    if matches:
        results[f"[THEME] {key}"] = matches

# 2. Pages
print("Scanning pages...")
r = httpx.get(f"{BASE}/pages.json", headers=H, params={"limit": 50}, timeout=20)
for page in r.json().get("pages", []):
    body = page.get("body_html", "") or ""
    matches = []
    for i, line in enumerate(body.splitlines(), 1):
        if PATTERN.search(line):
            matches.append((i, line.strip()[:120]))
    if matches:
        results[f"[PAGE] {page['handle']} (id={page['id']})"] = matches

# 3. Blog articles
print("Scanning blog articles...")
r = httpx.get(f"{BASE}/blogs.json", headers=H, timeout=20)
for blog in r.json().get("blogs", []):
    r2 = httpx.get(f"{BASE}/blogs/{blog['id']}/articles.json", headers=H, params={"limit": 50}, timeout=20)
    for art in r2.json().get("articles", []):
        body = (art.get("body_html") or "") + " " + (art.get("title") or "")
        matches = []
        for i, line in enumerate(body.splitlines(), 1):
            if PATTERN.search(line):
                matches.append((i, line.strip()[:120]))
        if matches:
            results[f"[BLOG] {blog['handle']}/{art['handle']} (id={art['id']})"] = matches

# Print summary
print(f"\n{'='*60}")
print(f"Found UK mentions in {len(results)} places:")
print(f"{'='*60}\n")
for loc, matches in results.items():
    print(f"{loc}")
    for lineno, text in matches:
        print(f"  line {lineno}: {text}")
    print()
