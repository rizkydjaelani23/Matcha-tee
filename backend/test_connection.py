import os
import sys

import httpx
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

STORE = os.environ["SHOPIFY_STORE"]
H = {"X-Shopify-Access-Token": os.environ["SHOPIFY_TOKEN"]}
API = f"https://{STORE}/admin/api/2025-01"


def main():
    shop = httpx.get(f"{API}/shop.json", headers=H, timeout=15).json()["shop"]
    print(f"Connected: {shop['name']} ({shop['myshopify_domain']}) "
          f"{shop['currency']} {shop['plan_display_name']}")

    for resource, params in [("products/count", {}), ("orders/count", {"status": "any"}),
                             ("customers/count", {})]:
        r = httpx.get(f"{API}/{resource}.json", headers=H, params=params, timeout=15)
        print(f"{resource}: {r.json().get('count')}")

    for t in httpx.get(f"{API}/themes.json", headers=H, timeout=15).json()["themes"]:
        print(f"theme {t['id']} role={t['role']} name={t['name']}")


if __name__ == "__main__":
    main()
