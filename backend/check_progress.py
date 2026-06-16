import json, sys
sys.stdout.reconfigure(encoding="utf-8")
data = json.load(open("C:/Users/rizky/matcha-tees/backend/sync_checkpoint.json"))

done         = [k for k,v in data.items() if v.get("status") == "done"]
real_errors  = [k for k,v in data.items() if v.get("status") == "publish_error"]
in_progress  = [k for k,v in data.items() if v.get("printify_id") and not v.get("status")]
no_image     = [k for k,v in data.items() if v.get("status") == "no_image"]
touched      = len(done) + len(real_errors) + len(in_progress) + len(no_image)
remaining    = max(0, 99 - touched)

print(f"Done:        {len(done)}/99")
print(f"In-progress: {len(in_progress)}")
print(f"Errors:      {len(real_errors)}  (will retry on next run)")
print(f"No image:    {len(no_image)}")
print(f"Remaining:   {remaining}")
print(f"Last 5 done:")
for k in done[-5:]:
    v = data[k]
    print(f"  {v.get('new_shopify_id','')}  pid={str(v.get('printify_id',''))[:10]}...")
if real_errors:
    print(f"Real errors (need retry):")
    for k in real_errors:
        print(f"  shopify_id={k}  printify_id={data[k].get('printify_id','?')}")
