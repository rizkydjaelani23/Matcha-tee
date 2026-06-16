import os, sys, json, time, httpx
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

STORE = os.environ["SHOPIFY_STORE"]
SHOPIFY_TOKEN = os.environ["SHOPIFY_TOKEN"]
SHR  = {"X-Shopify-Access-Token": SHOPIFY_TOKEN}
SAPI = f"https://{STORE}/admin/api/2025-01"

cp = json.load(open("full_checkpoint.json", encoding="utf-8"))

all_new_ids = {str(v["new_shopify_id"]) for v in cp.values() if v.get("new_shopify_id")}
retry_keys  = {k for k in cp if k in all_new_ids}
print(f"Duplicates to remove: {len(retry_keys)}")

deleted = 0
for k in list(retry_keys):
    v        = cp[k]
    dupe_sid = v.get("new_shopify_id")
    title    = v.get("title", "?")
    if dupe_sid:
        r = httpx.delete(f"{SAPI}/products/{dupe_sid}.json", headers=SHR, timeout=20)
        if r.status_code in (200, 404):
            print(f"  Deleted dupe: {title[:55]}")
            deleted += 1
        else:
            print(f"  Failed {r.status_code}: {title[:55]}")
        time.sleep(0.4)
    del cp[k]

with open("full_checkpoint.json", "w", encoding="utf-8") as f:
    json.dump(cp, f, indent=2)

done   = sum(1 for v in cp.values() if v.get("status") == "done")
errors = sum(1 for v in cp.values() if v.get("status") == "error")
print(f"\nDeleted {deleted} dupe Shopify products.")
print(f"Checkpoint: {len(cp)} entries — Done: {done}  Errors: {errors}  Remaining: {99-done-errors}")
