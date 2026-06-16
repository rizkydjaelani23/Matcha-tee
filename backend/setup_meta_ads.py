"""
setup_meta_ads.py
==================
Verifies the full Meta Ads connection for Matcha Tees and prints a summary
of the account setup.

Also provides helper functions for creating campaigns, ad sets, and ads.

Usage:
  python setup_meta_ads.py            # verify connection & show account summary
  python setup_meta_ads.py --campaign # create a starter Traffic campaign
"""
import os, sys, httpx, json, argparse
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

TOKEN    = os.environ["META_ADS_TOKEN"]
PIXEL_ID = os.environ["META_PIXEL_ID"]
AD_ACCT  = os.environ["META_AD_ACCOUNT_ID"]   # act_952259151129117
BIZ_ID   = os.environ["META_BUSINESS_ID"]
GRAPH    = "https://graph.facebook.com/v20.0"

def get(path, params=None):
    p = params or {}
    p["access_token"] = TOKEN
    r = httpx.get(f"{GRAPH}/{path}", params=p, timeout=20)
    return r.status_code, r.json()

def post(path, payload):
    payload["access_token"] = TOKEN
    r = httpx.post(f"{GRAPH}/{path}", json=payload, timeout=30)
    return r.status_code, r.json()

# ── Account Summary ───────────────────────────────────────────────────────────
def verify_connection():
    print("=" * 55)
    print("Meta Ads Connection — Matcha Tees")
    print("=" * 55)

    # Ad Account details
    code, acct = get(AD_ACCT, {
        "fields": "id,name,account_status,currency,balance,spend_cap,amount_spent,timezone_name"
    })
    print(f"\nAd Account: {code}")
    if code == 200:
        status_map = {1:"ACTIVE",2:"DISABLED",3:"UNSETTLED",7:"PENDING_RISK_REVIEW",9:"IN_GRACE_PERIOD",100:"PENDING_CLOSURE",101:"CLOSED",201:"ANY_ACTIVE",202:"ANY_CLOSED"}
        print(f"  Name:     {acct.get('name')}")
        print(f"  ID:       {acct.get('id')}")
        print(f"  Status:   {status_map.get(acct.get('account_status'), acct.get('account_status'))}")
        print(f"  Currency: {acct.get('currency')}")
        print(f"  Spent:    {acct.get('currency','GBP')} {float(acct.get('amount_spent',0))/100:.2f}")
        print(f"  Timezone: {acct.get('timezone_name')}")

    # Pixel
    code, pix = get(PIXEL_ID, {"fields": "id,name,last_fired_time"})
    print(f"\nPixel: {code}")
    if code == 200:
        print(f"  ID:         {pix.get('id')}")
        print(f"  Name:       {pix.get('name')}")
        print(f"  Last fired: {pix.get('last_fired_time','never')}")

    # Existing campaigns
    code, camps = get(f"{AD_ACCT}/campaigns", {
        "fields": "id,name,status,objective,daily_budget,lifetime_budget,spend_cap",
        "limit": "10"
    })
    print(f"\nCampaigns: {code}")
    camp_list = camps.get("data", [])
    if camp_list:
        for c in camp_list:
            budget = c.get("daily_budget") or c.get("lifetime_budget") or "0"
            print(f"  [{c.get('status')}] {c.get('name')} — {c.get('objective')} — budget={int(budget)//100}/day")
    else:
        print("  No campaigns yet.")

    # Pages linked to account
    code, pages = get("me/accounts", {"fields": "id,name,category,fan_count"})
    print(f"\nFacebook Pages: {code}")
    for p in pages.get("data", []):
        print(f"  {p.get('name')} (id={p.get('id')}, fans={p.get('fan_count',0)})")

    print("\n" + "=" * 55)
    print("Ready to create campaigns. Run with --campaign flag.")
    print("=" * 55)


# ── Create Starter Campaign ───────────────────────────────────────────────────
def create_starter_campaign():
    """
    Creates a Traffic campaign targeting UK interest in graphic tees.
    Daily budget: £5 (500 pence). Paused by default — activate in Ads Manager.
    """
    print("\nCreating starter Traffic campaign...")

    # 1. Campaign
    code, camp = post(f"{AD_ACCT}/campaigns", {
        "name":       "Matcha Tees — Traffic — UK Graphic Tees",
        "objective":  "OUTCOME_TRAFFIC",
        "status":     "PAUSED",
        "special_ad_categories": [],
    })
    print(f"  Campaign: {code} — {camp}")
    if code not in (200, 201) or "id" not in camp:
        print("  ERROR creating campaign")
        return
    campaign_id = camp["id"]

    # 2. Ad Set — UK, interest in graphic tees, 25-45 age
    code, adset = post(f"{AD_ACCT}/adsets", {
        "name":          "UK — Graphic Tee Fans — 18-45",
        "campaign_id":   campaign_id,
        "billing_event": "IMPRESSIONS",
        "optimization_goal": "LINK_CLICKS",
        "daily_budget":  500,   # £5.00 (in pence)
        "bid_strategy":  "LOWEST_COST_WITHOUT_CAP",
        "targeting": {
            "geo_locations": {
                "countries": ["GB"],
            },
            "age_min": 18,
            "age_max": 45,
            "flexible_spec": [
                {
                    "interests": [
                        {"id": "6003401247985", "name": "T-shirt"},
                        {"id": "6003148062858", "name": "Graphic design"},
                        {"id": "6003200074564", "name": "Fashion"},
                    ]
                }
            ],
        },
        "pixel_id":      PIXEL_ID,
        "status":        "PAUSED",
        "promoted_object": {
            "pixel_id":        PIXEL_ID,
            "custom_event_type": "PURCHASE",
        },
    })
    print(f"  Ad Set: {code} — {adset}")
    if code not in (200, 201):
        print("  ERROR creating ad set")
        return
    adset_id = adset["id"]

    print(f"\nCampaign created (PAUSED):")
    print(f"  Campaign ID: {campaign_id}")
    print(f"  Ad Set ID:   {adset_id}")
    print(f"\nNext steps:")
    print(f"  1. Go to Ads Manager and create the Ad creative (image + copy)")
    print(f"  2. Point it to your best-selling product URL")
    print(f"  3. Set to ACTIVE when ready to spend")
    print(f"  4. Monitor in Meta Events Manager that conversions fire correctly")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--campaign", action="store_true", help="Create starter campaign")
    args = ap.parse_args()

    verify_connection()
    if args.campaign:
        create_starter_campaign()
