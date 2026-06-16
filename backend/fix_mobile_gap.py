"""Deploy mobile gap fix: reduces excess spacing between guarantee and reviews on mobile.

What changed:
  - tmt-guarantee.liquid: padding-bottom reduced from 56px to 24px on mobile (<= 640px)
  - tmt-reviews-home.liquid: top padding reduced from 44px to 24px on mobile (<= 640px)

Run this script once to push the fix to the live theme.
"""
import os
import sys
import time

import httpx
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

STORE = os.environ["SHOPIFY_TOKEN"] and os.environ["SHOPIFY_STORE"]
TOKEN = os.environ["SHOPIFY_TOKEN"]
THEME = 143507587185
BASE_URL = f"https://{os.environ['SHOPIFY_STORE']}/admin/api/2025-01/themes/{THEME}/assets.json"
H = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}
BASE = os.path.dirname(os.path.abspath(__file__))


def put_asset(key, value):
    r = httpx.put(BASE_URL, headers=H, json={"asset": {"key": key, "value": value}}, timeout=30)
    if r.status_code not in (200, 201):
        raise Exception(f"PUT {key} failed {r.status_code}: {r.text[:300]}")
    print(f"  ✓ {key}")


# 1. Push updated guarantee snippet (reduced mobile bottom padding)
snippet_path = os.path.join(BASE, "snippets", "tmt-guarantee.liquid")
print("Pushing snippets/tmt-guarantee.liquid...")
with open(snippet_path, encoding="utf-8") as f:
    put_asset("snippets/tmt-guarantee.liquid", f.read())
time.sleep(0.5)

# 2. Push updated reviews home section (reduced mobile top padding)
print("Pushing sections/tmt-reviews-home.liquid...")
from setup_reviews import REVIEWS_HOME
put_asset("sections/tmt-reviews-home.liquid", REVIEWS_HOME)

print("\n✓ Mobile gap fix deployed. Refresh the homepage on mobile to verify.")
