"""Check if Instagram is already claimed by another Business Manager."""
import os, sys, httpx
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

TOKEN  = os.environ["META_ADS_TOKEN"]
BIZ_ID = os.environ["META_BUSINESS_ID"]
GRAPH  = "https://graph.facebook.com/v20.0"

def get(path, params=None):
    p = params or {}
    p["access_token"] = TOKEN
    r = httpx.get(f"{GRAPH}/{path}", params=p, timeout=20)
    return r.status_code, r.json()

# All Business Managers this token/user has access to
print("=== All Business Managers you have access to ===")
code, bizs = get("me/businesses", {
    "fields": "id,name,created_time,instagram_accounts{id,username}"
})
print(f"HTTP {code}")
for b in bizs.get("data", []):
    print(f"\n  BM: {b.get('name')} (id={b.get('id')})")
    ig_accounts = b.get("instagram_accounts", {}).get("data", [])
    if ig_accounts:
        for ig in ig_accounts:
            print(f"    IG claimed: @{ig.get('username')} (id={ig.get('id')})")
    else:
        print(f"    No Instagram accounts claimed here")

# Also check the client businesses
print("\n=== Client businesses (if any) ===")
code2, clients = get(f"{BIZ_ID}/client_businesses", {"fields": "id,name"})
if code2 == 200:
    for c in clients.get("data", []):
        print(f"  {c.get('name')} (id={c.get('id')})")
    if not clients.get("data"):
        print("  None")
else:
    print(f"  {clients.get('error',{}).get('message','')}")
