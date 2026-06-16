import os, httpx, json, sys
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

STORE = os.environ["SHOPIFY_STORE"]
H = {"X-Shopify-Access-Token": os.environ["SHOPIFY_TOKEN"]}
API = f"https://{STORE}/admin/api/2025-01"

pages = httpx.get(f"{API}/pages.json", headers=H, params={"limit": 50}, timeout=30).json().get("pages", [])
out = {}
for p in pages:
    out[p["handle"]] = {"id": p["id"], "title": p["title"], "body_html": p.get("body_html") or ""}

with open("_pages_raw.json", "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2, ensure_ascii=False)

print(f"Fetched {len(out)} pages → _pages_raw.json")
for h, d in out.items():
    print(f"\n{'='*60}")
    print(f"HANDLE: {h}  |  ID: {d['id']}")
    print(d["body_html"][:600])
