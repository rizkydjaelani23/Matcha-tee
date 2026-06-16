import json, sys
sys.stdout.reconfigure(encoding="utf-8")
cp = json.load(open("sync_checkpoint.json", encoding="utf-8"))
errors = {k: v for k, v in cp.items() if v.get("status") == "publish_error"}
print(f"Error products: {len(errors)}")
for k, v in errors.items():
    pid = v.get("printify_id")
    nsid = v.get("new_shopify_id")
    err = v.get("error", "")[:80]
    title = v.get("title", "?")
    print(f"  old_shopify_id={k}  printify_id={pid}  new_shopify_id={nsid}")
    print(f"    title={title}")
    print(f"    error={err}")
