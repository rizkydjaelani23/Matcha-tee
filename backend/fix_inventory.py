"""
Clean-up pass: find variants not yet at qty 10 (the 'not stocked at location'
stragglers) and inventoryActivate them — connects the item to the location AND
sets the quantity in one call.
"""
import os, sys, time, httpx
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
STORE=os.environ["SHOPIFY_STORE"]; TOKEN=os.environ["SHOPIFY_TOKEN"]
RH={"X-Shopify-Access-Token":TOKEN}
H ={"X-Shopify-Access-Token":TOKEN,"Content-Type":"application/json"}
API=f"https://{STORE}/admin/api/2025-01"
GQL=f"{API}/graphql.json"
QTY=10

def gql(q,v=None):
    for _ in range(6):
        r=httpx.post(GQL,headers=H,json={"query":q,"variables":v or {}},timeout=60)
        d=r.json()
        if d.get("errors") and any("throttled" in str(e).lower() for e in d["errors"]):
            time.sleep(2); continue
        return d
    return d

loc=httpx.get(f"{API}/shop.json",headers=RH,timeout=20).json()["shop"]["primary_location_id"]
print(f"Primary location id={loc}")

# find stragglers
url=f"{API}/products.json?limit=250&fields=id,title,variants"
todo=[]
while url:
    r=httpx.get(url,headers=RH,timeout=30)
    for p in r.json()["products"]:
        for v in p["variants"]:
            if v.get("inventory_quantity")!=QTY:
                todo.append((v["inventory_item_id"], p["title"], v["title"]))
    link=r.headers.get("Link","");url=None
    for part in link.split(","):
        if 'rel="next"' in part: url=part.strip().split(";")[0].strip("<> ")

print(f"Stragglers not at qty {QTY}: {len(todo)}\n")

ACT="""mutation($iid:ID!,$lid:ID!,$qty:Int){
  inventoryActivate(inventoryItemId:$iid, locationId:$lid, available:$qty){
    userErrors{field message}
  }
}"""

ok=0; fail=0
for i,(iid,pt,vt) in enumerate(todo,1):
    d=gql(ACT,{"iid":f"gid://shopify/InventoryItem/{iid}",
               "lid":f"gid://shopify/Location/{loc}","qty":QTY})
    errs=d.get("errors") or (d.get("data",{}).get("inventoryActivate") or {}).get("userErrors",[])
    if errs: fail+=1; print(f"  ERR {pt[:26]} / {vt}: {str(errs)[:100]}")
    else: ok+=1
    if i%50==0 or i==len(todo): print(f"  {i}/{len(todo)} (ok={ok} fail={fail})")
    time.sleep(0.2)

print(f"\nDone. activated+set={ok}, errors={fail}")
