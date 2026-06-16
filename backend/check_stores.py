import os, httpx, sys
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
SHOPIFY_TOKEN = os.environ["SHOPIFY_TOKEN"]
SHR = {"X-Shopify-Access-Token": SHOPIFY_TOKEN}

# Check our configured store
for domain in ["matcha-tees.myshopify.com", "eucbiq-ck.myshopify.com"]:
    r = httpx.get(
        f"https://{domain}/admin/api/2025-01/shop.json",
        headers=SHR, timeout=15
    )
    print(f"Store {domain}: status={r.status_code}")
    if r.status_code == 200:
        s = r.json().get("shop", {})
        print(f"  myshopify_domain={s.get('myshopify_domain')}")
        print(f"  name={s.get('name')}")
        print(f"  domain={s.get('domain')}")
    else:
        print(f"  Response: {r.text[:100]}")
    print()
