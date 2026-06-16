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

r = httpx.get(f"{API}/products/{pid}/images.json", headers=HR, timeout=20)
images = r.json().get("images", [])
print(f"Total images: {len(images)}")
for img in images:
    vids = img.get("variant_ids", [])
    src = img.get("src","")
    # get color from first variant
    color = "?"
    if vids:
        rv = httpx.get(f"{API}/variants/{vids[0]}.json?fields=option1,option3", headers=HR, timeout=10)
        if rv.status_code == 200:
            v = rv.json().get("variant", {})
            color = f"{v.get('option1')} / {v.get('option3')}"
    print(f"  [{color}]  variants={len(vids)}  src=...{src[-40:]}")
