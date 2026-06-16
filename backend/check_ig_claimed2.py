"""Check Business Managers via the user access token (not system user)."""
import os, sys, httpx
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

USER_TOKEN = os.environ["META_ACCESS_TOKEN"]  # user token, not system user
BIZ_ID     = os.environ["META_BUSINESS_ID"]
GRAPH      = "https://graph.facebook.com/v20.0"

def get(path, params=None, token=None):
    p = params or {}
    p["access_token"] = token or USER_TOKEN
    r = httpx.get(f"{GRAPH}/{path}", params=p, timeout=20)
    return r.status_code, r.json()

# All Business Managers the personal user has access to
print("=== Business Managers (via user token) ===")
code, bizs = get("me/businesses", {
    "fields": "id,name,instagram_accounts{id,username,name}"
})
print(f"HTTP {code}")
biz_list = bizs.get("data", [])
if not biz_list:
    err = bizs.get("error", {})
    print(f"  None found. {err.get('message','')}")
else:
    for b in biz_list:
        print(f"\n  BM: {b.get('name')} (id={b.get('id')})")
        ig_accounts = b.get("instagram_accounts", {}).get("data", [])
        if ig_accounts:
            for ig in ig_accounts:
                print(f"    ✓ IG claimed here: @{ig.get('username')} (id={ig.get('id')})")
        else:
            print(f"    No Instagram claimed here")

# Check if your IG is already connected to the Facebook Page via user token
print("\n=== Page Instagram link (via user token) ===")
code2, page = get("1143999588800098", {
    "fields": "instagram_business_account,connected_instagram_account"
})
print(f"HTTP {code2}  →  {page}")
