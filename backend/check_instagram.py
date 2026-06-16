"""Check Instagram account connection status for Matcha Tees Business Manager."""
import os, sys, httpx
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

TOKEN   = os.environ["META_ADS_TOKEN"]
BIZ_ID  = os.environ["META_BUSINESS_ID"]
PAGE_ID = "1143999588800098"
GRAPH   = "https://graph.facebook.com/v20.0"

def get(path, params=None):
    p = params or {}
    p["access_token"] = TOKEN
    r = httpx.get(f"{GRAPH}/{path}", params=p, timeout=20)
    return r.status_code, r.json()

# 1. Instagram accounts already claimed by the Business Manager
print("=== Instagram accounts in Business Manager ===")
code, ig_biz = get(f"{BIZ_ID}/instagram_accounts", {
    "fields": "id,username,name,profile_picture_url,followers_count,ig_id"
})
print(f"HTTP {code}")
accounts = ig_biz.get("data", [])
if not accounts:
    print("  None claimed yet.")
else:
    for a in accounts:
        print(f"  @{a.get('username')} (id={a.get('id')}, ig_id={a.get('ig_id')}, followers={a.get('followers_count',0)})")

# 2. Instagram account linked to the Facebook Page
print("\n=== Instagram linked to Facebook Page ===")
code, page_ig = get(PAGE_ID, {"fields": "id,name,instagram_business_account"})
print(f"HTTP {code}")
ig = page_ig.get("instagram_business_account")
if ig:
    print(f"  Linked IG account id: {ig.get('id')}")
    # Get details
    code2, ig_detail = get(ig["id"], {
        "fields": "id,username,name,followers_count,biography,website"
    })
    if code2 == 200:
        print(f"  @{ig_detail.get('username')} — {ig_detail.get('followers_count',0)} followers")
        print(f"  Bio: {ig_detail.get('biography','')}")
        print(f"  Website: {ig_detail.get('website','')}")
else:
    print("  No Instagram account linked to the Facebook Page.")
    print("  → You need to connect Instagram in Facebook Page Settings first.")

# 3. Check if token has Instagram permissions
print("\n=== Token Instagram permissions ===")
code, perms = get("me/permissions")
ig_perms = [p for p in perms.get("data", []) if "instagram" in p.get("permission","").lower()]
if ig_perms:
    for p in ig_perms:
        symbol = "✓" if p.get("status") == "granted" else "✗"
        print(f"  {symbol} {p['permission']}")
else:
    print("  No Instagram permissions found on this token.")
    print("  → Token may need instagram_basic + instagram_manage_accounts scopes")

# 4. Pages this token can manage (needed to link Instagram)
print("\n=== Pages accessible by this token ===")
code, pages = get("me/accounts", {"fields": "id,name,instagram_business_account,tasks"})
for p in pages.get("data", []):
    ig = p.get("instagram_business_account")
    ig_str = f" → IG: {ig['id']}" if ig else " → No IG linked"
    tasks = p.get("tasks", [])
    print(f"  {p.get('name')} (id={p.get('id')}){ig_str}")
    print(f"    Tasks: {tasks}")
