"""
Enable live inventory tracking on every product variant and set each to 10.
POD-safe: inventory_policy = 'continue' so a 0 count never blocks a sale.

  python setup_inventory.py --dry     # count only, no changes
  python setup_inventory.py           # apply: track + set 10 on all variants
  python setup_inventory.py --qty 25  # use a different starting quantity
"""
import os, sys, time, argparse, httpx
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
STORE=os.environ["SHOPIFY_STORE"]; TOKEN=os.environ["SHOPIFY_TOKEN"]
RH={"X-Shopify-Access-Token":TOKEN}
H ={"X-Shopify-Access-Token":TOKEN,"Content-Type":"application/json"}
API=f"https://{STORE}/admin/api/2025-01"

def throttle(resp):
    # respect Shopify REST leaky bucket (40 cap). Back off as it fills.
    lim = resp.headers.get("X-Shopify-Shop-Api-Call-Limit","")
    try:
        used,_cap = (int(x) for x in lim.split("/"))
        if used >= 32: time.sleep(1.0)
    except Exception:
        pass

def req(method, path, **kw):
    url=f"{API}/{path}"
    for attempt in range(6):
        r=httpx.request(method,url,timeout=30,**kw)
        if r.status_code==429:
            wait=float(r.headers.get("Retry-After","2"))
            time.sleep(wait); continue
        throttle(r)
        return r
    return r

def get_location():
    # read_locations scope isn't granted, but shop.primary_location_id is.
    shop=req("GET","shop.json",headers=RH).json().get("shop",{})
    lid=shop.get("primary_location_id")
    if lid:
        print(f"Location: primary_location_id={lid}")
        return lid
    # fallback: derive from an existing inventory level (needs read_inventory)
    locs=req("GET","locations.json",headers=RH).json().get("locations",[])
    if locs:
        print(f"Location: {locs[0]['name']} (id={locs[0]['id']})")
        return locs[0]["id"]
    print("ERROR: could not determine a location id"); sys.exit(1)

def fetch_variants():
    variants=[]
    url=f"{API}/products.json?limit=250&fields=id,title,variants"
    while url:
        r=httpx.get(url,headers=RH,timeout=30); throttle(r)
        for p in r.json()["products"]:
            for v in p.get("variants",[]):
                variants.append({
                    "pid":p["id"],"ptitle":p["title"],
                    "vid":v["id"],"vtitle":v.get("title",""),
                    "iid":v.get("inventory_item_id"),
                    "mgmt":v.get("inventory_management"),
                    "policy":v.get("inventory_policy"),
                    "qty":v.get("inventory_quantity"),
                })
        link=r.headers.get("Link","");url=None
        for part in link.split(","):
            if 'rel="next"' in part: url=part.strip().split(";")[0].strip("<> ")
    return variants

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--dry",action="store_true")
    ap.add_argument("--qty",type=int,default=10)
    args=ap.parse_args()

    loc=get_location()
    variants=fetch_variants()
    n=len(variants)
    already=sum(1 for v in variants if v["mgmt"]=="shopify")
    from collections import Counter
    pol=Counter(v["policy"] for v in variants)
    deny_continue=sum(1 for v in variants if v["policy"]!="continue")
    qty_at_target=sum(1 for v in variants if v["qty"]==args.qty)
    print(f"Variants: {n}  (tracked: {already})")
    print(f"  policy breakdown: {dict(pol)}   (need policy fix: {deny_continue})")
    print(f"  already at qty {args.qty}: {qty_at_target}")
    print(f"  -> target: qty {args.qty}, policy=continue\n")
    if args.dry:
        print("DRY RUN — no changes made."); return

    ok=0; fail=0
    for i,v in enumerate(variants,1):
        # 1) turn on Shopify tracking + allow overselling (POD-safe)
        rv=req("PUT",f"variants/{v['vid']}.json",headers=H,json={"variant":{
            "id":v["vid"],"inventory_management":"shopify","inventory_policy":"continue"}})
        if rv.status_code not in (200,201):
            fail+=1; print(f"  [{i}/{n}] VAR ERR {rv.status_code} {v['ptitle'][:28]} / {v['vtitle']}: {rv.text[:90]}"); continue
        # 2) set the available quantity at the location
        rs=req("POST","inventory_levels/set.json",headers=H,json={
            "location_id":loc,"inventory_item_id":v["iid"],"available":args.qty})
        if rs.status_code==422 and "not stocked" in rs.text.lower():
            # connect the item to the location first, then retry
            req("POST","inventory_levels/connect.json",headers=H,json={
                "location_id":loc,"inventory_item_id":v["iid"]})
            rs=req("POST","inventory_levels/set.json",headers=H,json={
                "location_id":loc,"inventory_item_id":v["iid"],"available":args.qty})
        if rs.status_code not in (200,201):
            fail+=1; print(f"  [{i}/{n}] SET ERR {rs.status_code} {v['ptitle'][:28]} / {v['vtitle']}: {rs.text[:90]}"); continue
        ok+=1
        if i%25==0 or i==n:
            print(f"  {i}/{n} done  (ok={ok} fail={fail})")
        time.sleep(0.25)

    print(f"\nDone. {ok} variants set to {args.qty} in stock (tracked, continue-selling). {fail} errors.")

if __name__=="__main__":
    main()
