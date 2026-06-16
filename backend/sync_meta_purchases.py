"""
sync_meta_purchases.py
=======================
Sends recent Shopify orders to Meta Conversions API (server-side Purchase events).
Run daily (or after each sale) for better attribution, especially on iOS.

Usage:
  python sync_meta_purchases.py          # sync last 24 hours
  python sync_meta_purchases.py --days 7 # sync last 7 days
  python sync_meta_purchases.py --dry    # print events without sending

Meta deduplication: event_id = "shopify_order_{order_id}" matches
the Purchase event fired by the browser pixel on the thank-you page.
"""
import os, sys, time, hashlib, json, argparse, httpx
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

STORE         = os.environ["SHOPIFY_STORE"]
SHOPIFY_TOKEN = os.environ["SHOPIFY_TOKEN"]
META_TOKEN    = os.environ["META_ACCESS_TOKEN"]
PIXEL_ID      = os.environ["META_PIXEL_ID"]
SHR           = {"X-Shopify-Access-Token": SHOPIFY_TOKEN}
SAPI          = f"https://{STORE}/admin/api/2025-01"
GRAPH         = "https://graph.facebook.com/v20.0"

def sha256(val):
    if not val:
        return None
    return hashlib.sha256(str(val).strip().lower().encode()).hexdigest()

def fetch_orders(days_back):
    """Fetch paid orders from the last N days."""
    import datetime
    since = (datetime.datetime.utcnow() - datetime.timedelta(days=days_back)).isoformat() + "Z"
    orders = []
    url = (f"{SAPI}/orders.json?status=any&financial_status=paid"
           f"&created_at_min={since}&limit=250"
           f"&fields=id,order_number,created_at,total_price,line_items,"
           f"customer,billing_address,source_name,landing_site,referring_site")
    while url:
        r = httpx.get(url, headers=SHR, timeout=30)
        data = r.json().get("orders", [])
        orders.extend(data)
        link = r.headers.get("Link", "")
        url = None
        for p in link.split(","):
            if 'rel="next"' in p:
                url = p.strip().split(";")[0].strip("<> ")
    return orders

def order_to_capi_event(order):
    """Convert a Shopify order to a Meta CAPI event payload."""
    cust     = order.get("customer") or {}
    billing  = order.get("billing_address") or {}
    email    = cust.get("email") or billing.get("email") or ""
    phone    = cust.get("phone") or billing.get("phone") or ""
    fname    = cust.get("first_name") or billing.get("first_name") or ""
    lname    = cust.get("last_name")  or billing.get("last_name")  or ""
    city     = billing.get("city") or ""
    country  = billing.get("country_code") or ""
    zip_code = billing.get("zip") or ""

    content_ids = [str(item["product_id"]) for item in order.get("line_items", []) if item.get("product_id")]
    num_items   = sum(item.get("quantity", 1) for item in order.get("line_items", []))
    value       = float(order.get("total_price", 0))

    created_ts = order.get("created_at", "")
    try:
        import datetime
        event_time = int(datetime.datetime.fromisoformat(
            created_ts.replace("Z","+00:00")).timestamp())
    except Exception:
        event_time = int(time.time())

    event = {
        "event_name":      "Purchase",
        "event_time":      event_time,
        "action_source":   "website",
        "event_source_url": f"https://thematchatee.com/",
        "event_id":        f"shopify_order_{order['id']}",
        "user_data": {
            "em":  [sha256(email)]  if email  else [],
            "ph":  [sha256(phone)]  if phone  else [],
            "fn":  [sha256(fname)]  if fname  else [],
            "ln":  [sha256(lname)]  if lname  else [],
            "ct":  [sha256(city)]   if city   else [],
            "zp":  [sha256(zip_code)] if zip_code else [],
            "country": [sha256(country)] if country else [],
        },
        "custom_data": {
            "value":        value,
            "currency":     "GBP",
            "content_ids":  content_ids,
            "content_type": "product",
            "num_items":    num_items,
            "order_id":     str(order["id"]),
            "order_number": str(order.get("order_number", "")),
        },
    }
    # Clean empty lists
    ud = event["user_data"]
    event["user_data"] = {k: v for k, v in ud.items() if v}
    return event

def send_events(events, dry_run=False):
    """Send events in batches of 1000 to Meta CAPI."""
    if dry_run:
        print(f"[DRY] Would send {len(events)} events")
        for e in events[:3]:
            print(f"  order={e['custom_data']['order_number']}  "
                  f"value=£{e['custom_data']['value']}  "
                  f"event_id={e['event_id']}")
        return

    batch_size = 1000
    total_sent = 0
    for i in range(0, len(events), batch_size):
        batch = events[i:i+batch_size]
        r = httpx.post(
            f"{GRAPH}/{PIXEL_ID}/events",
            json={"data": batch, "access_token": META_TOKEN},
            timeout=30,
        )
        if r.status_code == 200:
            result = r.json()
            received = result.get("events_received", 0)
            total_sent += received
            print(f"  Sent batch {i//batch_size + 1}: {received} events accepted")
        else:
            print(f"  ERROR batch {i//batch_size + 1}: {r.status_code} — {r.text[:200]}")

    return total_sent

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=1, help="Days back to sync (default: 1)")
    ap.add_argument("--dry", action="store_true", help="Dry run, no events sent")
    args = ap.parse_args()

    print(f"Fetching Shopify orders from last {args.days} day(s)...")
    orders = fetch_orders(args.days)
    print(f"Found {len(orders)} paid orders.")

    if not orders:
        print("No orders to sync.")
        return

    events = [order_to_capi_event(o) for o in orders]

    if args.dry:
        send_events(events, dry_run=True)
    else:
        total = send_events(events)
        print(f"\nDone. {total} purchase events sent to Meta CAPI.")
        print("Meta may deduplicate with browser pixel events (same event_id).")

if __name__ == "__main__":
    main()
