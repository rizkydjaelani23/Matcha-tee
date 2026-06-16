import os
import sys

import httpx
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

r = httpx.get(
    f"https://{os.environ['SHOPIFY_STORE']}/admin/oauth/access_scopes.json",
    headers={"X-Shopify-Access-Token": os.environ["SHOPIFY_TOKEN"]},
    timeout=20,
)
print(r.status_code)
print(", ".join(sorted(s["handle"] for s in r.json().get("access_scopes", []))))
