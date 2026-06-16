import json, os, httpx
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
STORE = os.environ["SHOPIFY_STORE"]
TOKEN = os.environ["SHOPIFY_TOKEN"]
HR = {"X-Shopify-Access-Token": TOKEN}
API = f"https://{STORE}/admin/api/2025-01"

cp = json.load(open("full_checkpoint.json", encoding="utf-8"))
entry = next(v for v in cp.values() if "addison rae" in (v.get("title","") or "").lower())
pid = entry["new_shopify_id"]
print("Shopify PID:", pid)

r = httpx.get(f"{API}/products/{pid}.json", headers=HR, timeout=20)
print("Status:", r.status_code)
if r.status_code == 200:
    p = r.json()
    print("Keys:", list(p.keys()))
    prod = list(p.values())[0]
    print("Title:", prod.get("title"))
    variants = prod.get("variants", [])
    print("Variants:", len(variants))
    if variants:
        v = variants[0]
        print("Sample:", v.get("id"), v.get("option1"), v.get("option2"), v.get("option3"))
else:
    print(r.text[:400])
