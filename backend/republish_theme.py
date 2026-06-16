import os, sys, time, httpx
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
STORE=os.environ["SHOPIFY_STORE"]; TOKEN=os.environ["SHOPIFY_TOKEN"]
RH={"X-Shopify-Access-Token":TOKEN}
H ={"X-Shopify-Access-Token":TOKEN,"Content-Type":"application/json"}
API=f"https://{STORE}/admin/api/2025-01"

main=next(t for t in httpx.get(f"{API}/themes.json",headers=RH,timeout=15).json()["themes"] if t["role"]=="main")
tid=main["id"]; print(f"Re-publishing: {main['name']} ({tid})")

r=httpx.put(f"{API}/themes/{tid}.json",headers=H,timeout=30,
            json={"theme":{"id":tid,"role":"main"}})
print("publish status:", r.status_code)

time.sleep(4)
# probe homepage
cb=int(time.time())
html=httpx.get(f"https://thematchatee.com/?cb={cb}",timeout=30,
               headers={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}).text
print("size:", len(html))
for m in ["tmt-ccy-badge","get.geojs.io","tmt-de-bar"]:
    print(f"  {'FOUND  ' if m in html else 'missing'}  {m}")
