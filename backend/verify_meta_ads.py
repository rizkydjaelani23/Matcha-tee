"""Verify Meta Ads token and fetch all account details."""
import os, sys, httpx, json
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
ADS_TOKEN = os.environ["META_ADS_TOKEN"]
PIXEL_ID  = os.environ["META_PIXEL_ID"]
BIZ_ID    = os.environ["META_BUSINESS_ID"]
GRAPH     = "https://graph.facebook.com/v20.0"

def get(path, params=None):
    p = params or {}
    p["access_token"] = ADS_TOKEN
    r = httpx.get(f"{GRAPH}/{path}", params=p, timeout=20)
    return r.status_code, r.json()

# 1. Token identity
code, me = get("me", {"fields": "id,name,email"})
print(f"=== Token Identity ({code}) ===")
print(f"  {me}")

# 2. Token permissions
code, perms = get("me/permissions")
print(f"\n=== Permissions ({code}) ===")
for p in perms.get("data", []):
    status = "✓" if p.get("status") == "granted" else "✗"
    print(f"  {status} {p.get('permission')}")

# 3. Ad Accounts
code, accts = get("me/adaccounts", {"fields": "id,name,account_status,currency,balance,amount_spent"})
print(f"\n=== Ad Accounts ({code}) ===")
ad_account_id = None
for a in accts.get("data", []):
    print(f"  id={a['id']}  name={a.get('name')}  currency={a.get('currency')}  status={a.get('account_status')}")
    if not ad_account_id:
        ad_account_id = a["id"]

# 4. Business accounts
code, biz = get(f"{BIZ_ID}", {"fields": "id,name,primary_page,ad_account{id,name}"})
print(f"\n=== Business Manager ({code}) ===")
print(f"  {biz.get('name')} — {biz.get('id')}")

# 5. Pixel access
code, pixel = get(f"{PIXEL_ID}", {"fields": "id,name,last_fired_time,is_created_by_business"})
print(f"\n=== Pixel ({code}) ===")
print(f"  {pixel}")

# 6. Print the ad account ID to add to .env
if ad_account_id:
    print(f"\n=== ADD TO .env ===")
    print(f"META_AD_ACCOUNT_ID={ad_account_id}")
