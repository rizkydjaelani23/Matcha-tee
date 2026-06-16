"""Full Meta account health check — errors, warnings, pixel issues, policy flags."""
import os, sys, httpx, json
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

TOKEN    = os.environ["META_ADS_TOKEN"]
PIXEL_ID = os.environ["META_PIXEL_ID"]
AD_ACCT  = os.environ["META_AD_ACCOUNT_ID"]
PAGE_ID  = "1143999588800098"
GRAPH    = "https://graph.facebook.com/v20.0"

def get(path, params=None):
    p = params or {}
    p["access_token"] = TOKEN
    r = httpx.get(f"{GRAPH}/{path}", params=p, timeout=20)
    return r.status_code, r.json()

def section(title):
    print(f"\n{'='*55}")
    print(f"  {title}")
    print(f"{'='*55}")

# ── 1. Ad Account ─────────────────────────────────────────────────────────────
section("Ad Account Health")
code, acct = get(AD_ACCT, {"fields": (
    "id,name,account_status,disable_reason,currency,"
    "amount_spent,balance,min_daily_budget,funding_source_details,age"
)})
if code == 200:
    status_map = {
        1:"ACTIVE", 2:"DISABLED", 3:"UNSETTLED",
        7:"PENDING_RISK_REVIEW", 9:"IN_GRACE_PERIOD",
        100:"PENDING_CLOSURE", 101:"CLOSED"
    }
    disable_map = {
        0:"None (healthy)",
        1:"ADS_INTEGRITY_POLICY — policy violation",
        2:"ADS_IP_REVIEW — under review",
        4:"PREPAY_ACCOUNT — needs top-up",
        5:"BANK_ACCOUNT — payment issue",
        9:"FR_EMAIL_UNVERIFIED — email not verified",
        11:"PAYMENT_ACCOUNT — billing issue",
    }
    st = acct.get("account_status")
    dr = acct.get("disable_reason", 0)
    print(f"  Status:         {status_map.get(st, st)}")
    print(f"  Disable reason: {disable_map.get(dr, f'code {dr}')}")
    print(f"  Balance:        GBP {float(acct.get('balance', 0))/100:.2f}")
    print(f"  Total spent:    GBP {float(acct.get('amount_spent', 0))/100:.2f}")
    if acct.get("min_daily_budget"):
        print(f"  Min daily bgt:  GBP {float(acct['min_daily_budget'])/100:.2f}")
    fs = acct.get("funding_source_details")
    if fs:
        print(f"  Payment:        {fs.get('type','?')} — {fs.get('display_string','?')}")
    else:
        print(f"  Payment:        ⚠ NO PAYMENT METHOD ON FILE")
else:
    print(f"  ERROR {code}: {acct.get('error',{}).get('message','')}")

# ── 2. Account Quality / Policy Issues ───────────────────────────────────────
section("Account Quality")
code, quality = get(f"{AD_ACCT}/account_quality_recommendations", {})
if code == 200:
    recs = quality.get("data", [])
    if not recs:
        print("  No recommendations — account looks healthy.")
    for r in recs:
        print(f"  ⚠ {r}")
else:
    # Try ad account activity log for issues
    code2, activity = get(f"{AD_ACCT}/activities", {
        "fields": "event_type,event_time,extra_data",
        "limit": "10"
    })
    if code2 == 200:
        acts = activity.get("data", [])
        if not acts:
            print("  No recent activity found.")
        for a in acts[:5]:
            print(f"  {a.get('event_time','')} — {a.get('event_type','')} {a.get('extra_data','')}")
    else:
        print(f"  Could not fetch quality data: {quality.get('error',{}).get('message','')}")

# ── 3. Campaigns / Issues ────────────────────────────────────────────────────
section("Campaigns")
code, camps = get(f"{AD_ACCT}/campaigns", {
    "fields": "id,name,status,effective_status,objective,issues_info,configured_status",
    "limit": "25"
})
camp_list = camps.get("data", [])
if not camp_list:
    print("  No campaigns created yet.")
else:
    for c in camp_list:
        eff = c.get("effective_status", "?")
        issues = c.get("issues_info", [])
        flag = "⚠ " if issues else "  "
        print(f"  {flag}[{eff}] {c.get('name')}")
        for iss in issues:
            print(f"      ERROR {iss.get('error_code')}: {iss.get('error_message','')}")
            print(f"      FIX: {iss.get('error_summary','')}")

# ── 4. Ad Sets ────────────────────────────────────────────────────────────────
section("Ad Sets")
code, adsets = get(f"{AD_ACCT}/adsets", {
    "fields": "id,name,status,effective_status,issues_info,daily_budget",
    "limit": "25"
})
adset_list = adsets.get("data", [])
if not adset_list:
    print("  No ad sets created yet.")
else:
    for a in adset_list:
        eff = a.get("effective_status", "?")
        issues = a.get("issues_info", [])
        flag = "⚠ " if issues else "  "
        daily = float(a.get("daily_budget", 0))/100
        print(f"  {flag}[{eff}] {a.get('name')} — £{daily:.2f}/day")
        for iss in issues:
            print(f"      ERROR {iss.get('error_code')}: {iss.get('error_message','')}")

# ── 5. Ads ────────────────────────────────────────────────────────────────────
section("Ads (Creatives)")
code, ads = get(f"{AD_ACCT}/ads", {
    "fields": "id,name,status,effective_status,issues_info,review_feedback",
    "limit": "25"
})
ads_list = ads.get("data", [])
if not ads_list:
    print("  No ads created yet.")
else:
    for a in ads_list:
        eff = a.get("effective_status", "?")
        issues = a.get("issues_info", [])
        review = a.get("review_feedback", {})
        flag = "⚠ " if (issues or review) else "  "
        print(f"  {flag}[{eff}] {a.get('name')}")
        for iss in issues:
            print(f"      ERROR {iss.get('error_code')}: {iss.get('error_message','')}")
        if review:
            for k, v in review.items():
                if v:
                    print(f"      REVIEW [{k}]: {v}")

# ── 6. Pixel Events ───────────────────────────────────────────────────────────
section("Pixel Event Health")
code, px_stats = get(f"{PIXEL_ID}/stats", {
    "aggregation": "event",
    "start_time": "1781380800",  # ~2 days ago
    "end_time":   "1781553600",  # now-ish
})
if code == 200:
    events = px_stats.get("data", [])
    if not events:
        print("  No events fired in the last 2 days.")
        print("  (Pixel may not have visitors yet — check after launch)")
    for ev in events:
        print(f"  {ev.get('event','?'):20} count={ev.get('count',0)}")
else:
    # Simpler check: just get pixel info
    code2, px = get(PIXEL_ID, {"fields": "id,name,last_fired_time,code"})
    if code2 == 200:
        print(f"  Pixel: {px.get('name')} — last fired: {px.get('last_fired_time','never')}")
        print(f"  (Detailed stats require Events Manager UI)")
    else:
        print(f"  Error: {px.get('error',{}).get('message','')}")

# ── 7. Facebook Page ─────────────────────────────────────────────────────────
section("Facebook Page")
code, page = get(PAGE_ID, {
    "fields": "id,name,verification_status,fan_count,is_published"
})
if code == 200:
    print(f"  Name:      {page.get('name')}")
    print(f"  Published: {page.get('is_published', page.get('published'))}")
    print(f"  Verified:  {page.get('verification_status','unverified')}")
    print(f"  Followers: {page.get('fan_count', 0)}")
    if not page.get("is_published"):
        print(f"  ⚠ Page is not published — ads may not run correctly")
else:
    print(f"  Error {code}: {page.get('error',{}).get('message','')}")

# ── 8. Billing / Payment Methods ─────────────────────────────────────────────
section("Billing")
code, billing = get(f"{AD_ACCT}/customaudiences", {"fields": "id,name", "limit": "3"})
# Check payment threshold
code2, thresh = get(f"{AD_ACCT}", {
    "fields": "spend_cap,balance,next_bill_date,currency"
})
if code2 == 200:
    print(f"  Currency:      {thresh.get('currency')}")
    print(f"  Balance:       {thresh.get('balance')}")
    spend_cap = thresh.get("spend_cap")
    if spend_cap and int(spend_cap) > 0:
        print(f"  Spend cap:     GBP {float(spend_cap)/100:.2f}")
    else:
        print(f"  Spend cap:     None (unlimited)")
    next_bill = thresh.get("next_bill_date")
    if next_bill:
        print(f"  Next bill:     {next_bill}")

# Saved audiences
code3, audiences = get(f"{AD_ACCT}/customaudiences", {
    "fields": "id,name,subtype,approximate_count",
    "limit": "10"
})
if code3 == 200:
    auds = audiences.get("data", [])
    print(f"\n  Custom audiences: {len(auds)}")
    for a in auds:
        print(f"    {a.get('name')} ({a.get('subtype')}) ~{a.get('approximate_count',0)} people")
else:
    print(f"\n  Custom audiences: 0 (none created yet)")

print(f"\n{'='*55}")
print("Health check complete.")
print(f"{'='*55}")
