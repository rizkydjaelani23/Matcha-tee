import os, sys, httpx
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv()
STORE=os.environ["SHOPIFY_STORE"]; TOKEN=os.environ["SHOPIFY_TOKEN"]
RH={"X-Shopify-Access-Token":TOKEN}
API=f"https://{STORE}/admin/api/2025-01"

r=httpx.get(f"{API}/themes.json",headers=RH,timeout=15)
for t in r.json()["themes"]:
    print(f"  role={t['role']:12} id={t['id']}  {t['name']}")
main=next(t for t in r.json()["themes"] if t["role"]=="main")
print(f"\nMAIN theme: {main['name']} ({main['id']})\n")

lay=httpx.get(f"{API}/themes/{main['id']}/assets.json",headers=RH,
              params={"asset[key]":"layout/theme.liquid"},timeout=15).json()["asset"]["value"]
print(f"theme.liquid length: {len(lay)} chars")
print("render tmt-currency present:", "{% render 'tmt-currency' %}" in lay)
print("render tmt-de-popup present:", "{% render 'tmt-de-popup' %}" in lay)
print("</body> count:", lay.count("</body>"))
print("\n──── last 600 chars of theme.liquid ────")
print(lay[-600:])
