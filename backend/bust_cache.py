import os, sys, re, httpx
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
STORE=os.environ["SHOPIFY_STORE"]; TOKEN=os.environ["SHOPIFY_TOKEN"]
RH={"X-Shopify-Access-Token":TOKEN}
H ={"X-Shopify-Access-Token":TOKEN,"Content-Type":"application/json"}
API=f"https://{STORE}/admin/api/2025-01"

main=next(t for t in httpx.get(f"{API}/themes.json",headers=RH,timeout=15).json()["themes"] if t["role"]=="main")
tid=main["id"]; print(f"Theme: {main['name']} ({tid})")

key="layout/theme.liquid"
lay=httpx.get(f"{API}/themes/{tid}/assets.json",headers=RH,params={"asset[key]":key},timeout=15).json()["asset"]["value"]

# bump/insert a harmless cache-bust marker comment (no render impact)
marker_re = re.compile(r"<!-- tmt-cb \d+ -->")
stamp = "<!-- tmt-cb 2 -->"
if marker_re.search(lay):
    lay = marker_re.sub(stamp, lay)
else:
    lay = lay.replace("</body>", f"  {stamp}\n</body>", 1)

r=httpx.put(f"{API}/themes/{tid}/assets.json",headers=H,timeout=30,
            json={"asset":{"key":key,"value":lay}})
print("theme.liquid touch:", r.status_code)

# also touch the index template to invalidate the homepage's own cache entry
idx_key="templates/index.json"
ir=httpx.get(f"{API}/themes/{tid}/assets.json",headers=RH,params={"asset[key]":idx_key},timeout=15)
if ir.status_code==200 and ir.json().get("asset",{}).get("value"):
    idx=ir.json()["asset"]["value"]
    pr=httpx.put(f"{API}/themes/{tid}/assets.json",headers=H,timeout=30,
                 json={"asset":{"key":idx_key,"value":idx}})
    print("index.json touch:", pr.status_code)
else:
    print("index.json: not found / not editable")
