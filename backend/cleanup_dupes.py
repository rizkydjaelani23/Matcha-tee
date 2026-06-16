"""
cleanup_dupes.py
Finds Shopify products created by the botched retry run and deletes them.
Identifies duplicates as: any checkpoint entry whose KEY is itself
another entry's new_shopify_id (meaning it was a migrated product that
got treated as a source and re-migrated again).
"""
import os, sys, json, time, httpx
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

STORE         = os.environ["SHOPIFY_STORE"]
SHOPIFY_TOKEN = os.environ["SHOPIFY_TOKEN"]
SHR  = {"X-Shopify-Access-Token": SHOPIFY_TOKEN}
SH   = {"X-Shopify-Access-Token": SHOPIFY_TOKEN, "Content-Type": "application/json"}
SAPI = f"https://{STORE}/admin/api/2025-01"

cp = json.load(open("full_checkpoint.json", encoding="utf-8"))

# Build set of all new_shopify_ids from the ORIGINAL run
# (these are the correctly migrated products)
original_new_ids = {str(v["new_shopify_id"]) for v in cp.values()
                    if v.get("new_shopify_id") and str(v.get("new_shopify_id")) not in cp}

# Find retry-run entries: checkpoint keys that ARE in original_new_ids
# These are products that were re-processed during the botched retry
retry_entries = {k: v for k, v in cp.items() if k in original_new_ids}

print(f"Original run entries:  {len(cp) - len(retry_entries)}")
print(f"Botched retry entries: {len(retry_entries)}")
print()

dupes_to_delete = []
for k, v in retry_entries.items():
    dupe_sid = v.get("new_shopify_id")
    title    = v.get("title", "?")
    if dupe_sid:
        dupes_to_delete.append((title, str(dupe_sid), k))
        print(f"  DUPE: {title[:55]}")
        print(f"    Keep: {k}  |  Delete: {dupe_sid}")

print(f"\n{len(dupes_to_delete)} duplicate Shopify products to delete")
inp = input("Type YES to delete them: ").strip()
if inp != "YES":
    print("Aborted.")
    sys.exit(0)

deleted = 0
for title, dupe_sid, good_sid in dupes_to_delete:
    for _ in range(3):
        r = httpx.delete(f"{SAPI}/products/{dupe_sid}.json", headers=SHR, timeout=20)
        if r.status_code == 429:
            time.sleep(float(r.headers.get("Retry-After", 4)))
            continue
        break
    if r.status_code in (200, 404):
        print(f"  ✓ Deleted dupe for '{title[:50]}'")
        deleted += 1
        # Remove the retry entry from checkpoint
        del cp[good_sid]
    else:
        print(f"  ✗ Failed {r.status_code} for '{title[:50]}'")
    time.sleep(0.4)

# Save cleaned checkpoint
with open("full_checkpoint.json", "w", encoding="utf-8") as f:
    json.dump(cp, f, indent=2)

print(f"\nDeleted {deleted} duplicates. Checkpoint cleaned.")
print(f"Checkpoint now has {len(cp)} entries.")
