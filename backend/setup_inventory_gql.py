"""
Fast inventory setup via GraphQL bulk mutations.
 - sets every variant's inventory_policy -> CONTINUE  (POD: never block a sale)
 - sets every variant's available quantity -> N (default 10) at primary location

  python setup_inventory_gql.py --test    # ONE product only, then verify
  python setup_inventory_gql.py           # ALL products
  python setup_inventory_gql.py --qty 25
"""
import os, sys, time, argparse, httpx
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
STORE=os.environ["SHOPIFY_STORE"]; TOKEN=os.environ["SHOPIFY_TOKEN"]
RH={"X-Shopify-Access-Token":TOKEN}
H ={"X-Shopify-Access-Token":TOKEN,"Content-Type":"application/json"}
API=f"https://{STORE}/admin/api/2025-01"
GQL=f"{API}/graphql.json"

def gql(q,v=None):
    for _ in range(6):
        r=httpx.post(GQL,headers=H,json={"query":q,"variables":v or {}},timeout=60)
        d=r.json()
        if d.get("errors") and any("throttled" in str(e).lower() for e in d["errors"]):
            time.sleep(2); continue
        return d
    return d

def primary_location():
    shop=httpx.get(f"{API}/shop.json",headers=RH,timeout=20).json()["shop"]
    return shop["primary_location_id"]

def fetch_products():
    prods=[]
    url=f"{API}/products.json?limit=250&fields=id,title,variants"
    while url:
        r=httpx.get(url,headers=RH,timeout=30);
        for p in r.json()["products"]:
            prods.append(p)
        link=r.headers.get("Link","");url=None
        for part in link.split(","):
            if 'rel="next"' in part: url=part.strip().split(";")[0].strip("<> ")
    return prods

POLICY_MUT="""mutation($pid:ID!,$vars:[ProductVariantsBulkInput!]!){
  productVariantsBulkUpdate(productId:$pid, variants:$vars){
    userErrors{field message}
  }
}"""

QTY_MUT="""mutation($input:InventorySetQuantitiesInput!){
  inventorySetQuantities(input:$input){
    userErrors{field message}
  }
}"""

def set_policy(pid, variant_ids):
    vars=[{"id":f"gid://shopify/ProductVariant/{vid}","inventoryPolicy":"CONTINUE"} for vid in variant_ids]
    d=gql(POLICY_MUT,{"pid":f"gid://shopify/Product/{pid}","vars":vars})
    errs=(d.get("data",{}).get("productVariantsBulkUpdate") or {}).get("userErrors",[]) if d.get("data") else d.get("errors")
    return errs

def set_quantities(loc, items, qty, name="available"):
    quantities=[{"inventoryItemId":f"gid://shopify/InventoryItem/{iid}",
                 "locationId":f"gid://shopify/Location/{loc}","quantity":qty} for iid in items]
    d=gql(QTY_MUT,{"input":{
        "name":name,"reason":"correction","ignoreCompareQuantity":True,
        "quantities":quantities}})
    if d.get("errors"): return d["errors"]
    return (d.get("data",{}).get("inventorySetQuantities") or {}).get("userErrors",[])

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--test",action="store_true")
    ap.add_argument("--qty",type=int,default=10)
    args=ap.parse_args()

    loc=primary_location(); print(f"Primary location id={loc}")
    prods=fetch_products()
    if args.test: prods=prods[:1]
    total_v=sum(len(p["variants"]) for p in prods)
    print(f"Products: {len(prods)}  Variants: {total_v}  -> qty {args.qty}, policy CONTINUE\n")

    # ---- policy: one bulk call per product ----
    print("Setting inventory_policy = CONTINUE ...")
    pfail=0
    for i,p in enumerate(prods,1):
        vids=[v["id"] for v in p["variants"]]
        # bulk update caps at 250 variants/call; batch if needed
        for j in range(0,len(vids),200):
            errs=set_policy(p["id"],vids[j:j+200])
            if errs: pfail+=1; print(f"  policy ERR {p['title'][:30]}: {str(errs)[:120]}")
        if i%20==0 or i==len(prods): print(f"  policy {i}/{len(prods)}")
        time.sleep(0.2)

    # ---- quantities: batched across all variants ----
    print("\nSetting available quantity ...")
    all_iids=[v["inventory_item_id"] for p in prods for v in p["variants"]]
    qfail=0; done=0; name="available"
    for j in range(0,len(all_iids),200):
        batch=all_iids[j:j+200]
        errs=set_quantities(loc,batch,args.qty,name)
        if errs:
            # retry once with on_hand if 'available' is rejected
            if name=="available" and any("available" in str(e).lower() or "not supported" in str(e).lower() for e in errs):
                name="on_hand"; errs=set_quantities(loc,batch,args.qty,name)
        if errs:
            qfail+=1; print(f"  qty ERR batch@{j} ({name}): {str(errs)[:140]}")
        else:
            done+=len(batch)
        print(f"  qty {min(j+200,len(all_iids))}/{len(all_iids)}  (name={name})")
        time.sleep(0.3)

    print(f"\nDONE. policy errors={pfail}, quantity set={done}/{len(all_iids)}, qty batch errors={qfail}")
    if args.test:
        print("\nTEST product variant ids:", [v["id"] for v in prods[0]["variants"]][:5], "...")

if __name__=="__main__":
    main()
