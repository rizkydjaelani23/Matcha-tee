"""
Phase 2: Set descriptive alt text on every product image (REST).
Improves Google Images ranking + accessibility.
"""
import os, sys, time, re
import httpx
from dotenv import load_dotenv
sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
STORE = os.environ["SHOPIFY_STORE"]
TOKEN = os.environ["SHOPIFY_TOKEN"]
RH    = {"X-Shopify-Access-Token": TOKEN}
H     = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}
API   = f"https://{STORE}/admin/api/2025-01"

ACRONYMS = {"ii","iii","iv","tv","uk","us","ai","dj","mtv"}
def tc(s):
    return " ".join(w.upper() if w.lower().strip(".,|-") in ACRONYMS
                     else (w[:1].upper()+w[1:].lower() if w else w)
                     for w in s.split())
def clean_title(raw):
    t = raw.strip()
    for sep in (" | ", " - "):
        if sep in t:
            left = t.split(sep)[0].strip()
            if len(left) >= 8:
                t = left
    return tc(t)
def type_noun(ptype, tl):
    p=(ptype or "").lower(); t=tl.lower()
    if "sweat" in p or "sweat" in t: return "vintage sweatshirt"
    if "hoodie" in p or "hoodie" in t: return "vintage hoodie"
    if "kid" in p or "kid" in t: return "kids graphic tee"
    return "vintage graphic tee"

def fetch_all():
    out=[]; url=f"{API}/products.json?limit=250&fields=id,title,product_type,images"
    while url:
        r=httpx.get(url,headers=RH,timeout=30)
        out.extend(r.json().get("products",[]))
        nxt=None
        for part in r.headers.get("Link","").split(","):
            if 'rel="next"' in part: nxt=part[part.find("<")+1:part.find(">")]
        url=nxt
    return out

products=fetch_all()
print(f"{len(products)} products\n")
imgs_done=0; prod_done=0; fail=0
for p in products:
    name=clean_title(p["title"]); noun=type_noun(p.get("product_type"),p["title"])
    images=p.get("images",[])
    for idx,img in enumerate(images):
        if idx==0:
            alt=f"{name} {noun} – The Matcha Tee"
        else:
            alt=f"{name} {noun} – view {idx+1}"
        alt=alt[:512]
        r=httpx.put(f"{API}/products/{p['id']}/images/{img['id']}.json",
                    headers=H, json={"image":{"id":img["id"],"alt":alt}}, timeout=30)
        if r.status_code in (200,201):
            imgs_done+=1
        else:
            fail+=1
        time.sleep(0.3)
    prod_done+=1
    if prod_done%20==0 or prod_done<=3:
        print(f"  {prod_done}/{len(products)}  {name}: {len(images)} imgs")

print(f"\nDone. {prod_done} products, {imgs_done} images alt-tagged. Failed: {fail}")
