import json

cp = json.load(open("full_checkpoint.json", encoding="utf-8"))

all_new_ids = {str(v["new_shopify_id"]) for v in cp.values() if v.get("new_shopify_id")}
retry_keys  = {k for k in cp if k in all_new_ids}

print(f"Total checkpoint entries : {len(cp)}")
print(f"Retry (duplicate) entries: {len(retry_keys)}")
print()
for k in sorted(retry_keys)[:5]:
    v = cp[k]
    print(f"  key={k}")
    print(f"  title={v.get('title','?')[:50]}")
    print(f"  dupe_new_sid={v.get('new_shopify_id')}")
    print()

done   = sum(1 for v in cp.values() if v.get("status") == "done")
errors = sum(1 for v in cp.values() if v.get("status") == "error")
print(f"Done: {done}  Errors: {errors}")
