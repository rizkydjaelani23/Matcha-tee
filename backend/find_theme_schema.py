import json, os, httpx
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
STORE = os.environ["SHOPIFY_STORE"]
TOKEN = os.environ["SHOPIFY_TOKEN"]
HR = {"X-Shopify-Access-Token": TOKEN}
API = f"https://{STORE}/admin/api/2025-01"

r = httpx.get(f"{API}/themes.json", headers=HR, timeout=20)
themes = r.json().get("themes", [])
active = next((t for t in themes if t.get("role") == "main"), None)
print(f"Active theme: {active['name']} id={active['id']}")

r2 = httpx.get(f"{API}/themes/{active['id']}/assets.json", headers=HR, timeout=30)
assets = r2.json().get("assets", [])
kws = ["schema", "structured", "seo", "ld-json", "rich", "product"]
hits = [a["key"] for a in assets if any(k in a["key"].lower() for k in kws)]
print("Candidate files:")
for f in sorted(hits):
    print(f"  {f}")
