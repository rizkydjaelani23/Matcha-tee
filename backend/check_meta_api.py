"""Verify Meta access token and fetch Ad Account ID."""
import os, sys, httpx, json
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
TOKEN    = os.environ["META_ACCESS_TOKEN"]
APP_ID   = os.environ["META_APP_ID"]
PIXEL_ID = os.environ["META_PIXEL_ID"]
BIZ_ID   = os.environ["META_BUSINESS_ID"]
GRAPH    = "https://graph.facebook.com/v20.0"
H = {"Authorization": f"Bearer {TOKEN}"}

# 1. Verify token / get user info
r = httpx.get(f"{GRAPH}/me", params={"fields": "id,name", "access_token": TOKEN}, timeout=15)
print(f"Token check: {r.status_code}")
if r.status_code == 200:
    me = r.json()
    print(f"  Authenticated as: {me.get('name')} (id={me.get('id')})")
else:
    print(f"  Error: {r.text[:200]}")

# 2. Get Ad Accounts linked to this user/business
r2 = httpx.get(
    f"{GRAPH}/me/adaccounts",
    params={"fields": "id,name,account_status,currency", "access_token": TOKEN},
    timeout=15,
)
print(f"\nAd Accounts: {r2.status_code}")
ad_accounts = r2.json().get("data", [])
for acc in ad_accounts:
    print(f"  id={acc['id']}  name={acc.get('name')}  currency={acc.get('currency')}  status={acc.get('account_status')}")

# 3. Check the Pixel
r3 = httpx.get(
    f"{GRAPH}/{PIXEL_ID}",
    params={"fields": "id,name,code,creation_time,last_fired_time", "access_token": TOKEN},
    timeout=15,
)
print(f"\nPixel {PIXEL_ID}: {r3.status_code}")
if r3.status_code == 200:
    px = r3.json()
    print(f"  name={px.get('name')}  last_fired={px.get('last_fired_time','never')}")
else:
    print(f"  {r3.text[:200]}")

# 4. Check Business Manager
r4 = httpx.get(
    f"{GRAPH}/{BIZ_ID}",
    params={"fields": "id,name,primary_page", "access_token": TOKEN},
    timeout=15,
)
print(f"\nBusiness {BIZ_ID}: {r4.status_code}")
if r4.status_code == 200:
    biz = r4.json()
    print(f"  name={biz.get('name')}")
else:
    print(f"  {r4.text[:200]}")
