"""
auto_router.py — Matcha Tee automatic order router (no hosting required)
=========================================================================
Polls Shopify every 5 minutes for new paid orders and creates the correct
Printify order based on customer country + fabric variant chosen.

Run manually:       python auto_router.py
Run once (no loop): python auto_router.py --once
Check status:       python auto_router.py --status

Set up as a Windows scheduled task to run automatically:
  - Open Task Scheduler → Create Basic Task
  - Trigger: Daily, repeat every 5 minutes
  - Action: Start a program → python.exe
  - Arguments: C:\Users\rizky\matcha-tees\backend\auto_router.py --once
"""
import os, sys, json, time, httpx, argparse
from datetime import datetime, timezone, timedelta
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

STORE          = os.environ["SHOPIFY_STORE"]
SHOPIFY_TOKEN  = os.environ["SHOPIFY_TOKEN"]
PRINTIFY_TOKEN = os.environ["PRINTIFY_TOKEN"]
SHOP_ID        = 27883571

SHR  = {"X-Shopify-Access-Token": SHOPIFY_TOKEN}
SH   = {"X-Shopify-Access-Token": SHOPIFY_TOKEN, "Content-Type": "application/json"}
PH   = {"Authorization": f"Bearer {PRINTIFY_TOKEN}", "Content-Type": "application/json"}
SAPI = f"https://{STORE}/admin/api/2025-01"
PAPI = "https://api.printify.com/v1"

CHECKPOINT_PATH  = os.path.join(os.path.dirname(__file__), "full_checkpoint.json")
ROUTED_LOG_PATH  = os.path.join(os.path.dirname(__file__), "routed_orders.json")
POLL_INTERVAL    = 10800  # seconds (3 hours)

EU_COUNTRIES = {
    "AT","BE","BG","CY","CZ","DE","DK","EE","ES","FI","FR","GR","HR",
    "HU","IE","IT","LT","LU","LV","MT","NL","PL","PT","RO","SE","SI","SK",
}

# ── Variant maps ──────────────────────────────────────────────────────────────
VARIANT_MAPS = {
    "UK_CC": {
        "Black":       {"S":73196,"M":73200,"L":73204,"XL":73208,"2XL":73212,"3XL":79114},
        "White":       {"S":73199,"M":73203,"2XL":73215,"3XL":79169},
        "Pepper":      {"M":79047,"3XL":79155},
        "Grey":        {"S":78971,"M":78972,"L":78973,"XL":78974,"2XL":78975,"3XL":79137},
        "Ivory":       {"3XL":79142},
        "Light Green": {"S":79006,"M":79007,"L":79008,"XL":79009,"2XL":79010,"3XL":79146},
        "Chambray":    {"S":78921,"M":78922,"L":78923,"XL":78924,"2XL":78925,"3XL":79124},
        "Washed Denim":{"S":79096,"M":79097,"L":79098,"XL":79099,"2XL":79100,"3XL":79167},
        "Blossom":     {"S":78886,"M":78887,"L":78888,"XL":78889,"2XL":78890,"3XL":79115},
    },
    "UK_GD": {
        "Black":{"S":12126,"M":12125,"L":12124,"XL":12127,"2XL":12128,"3XL":12129},
        "White":{"S":12102,"M":12101,"L":12100,"XL":12103,"2XL":12104,"3XL":12105},
        "Grey": {"S":12072,"M":12071,"L":12070,"XL":12073,"2XL":12074,"3XL":12075},
    },
    "US_CC": {
        "Black":       {"S":73196,"M":73200,"L":73204,"XL":73208,"2XL":73212,"3XL":79114},
        "White":       {"S":73199,"M":73203,"L":73207,"XL":73211,"2XL":73215,"3XL":79169},
        "Pepper":      {"S":79046,"M":79047,"L":79048,"XL":79049,"2XL":79050,"3XL":79155},
        "Grey":        {"S":78971,"M":78972,"L":78973,"XL":78974,"2XL":78975,"3XL":79137},
        "Ivory":       {"S":78991,"M":78992,"L":78993,"XL":78994,"2XL":78995,"3XL":79142},
        "Light Green": {"S":79006,"M":79007,"L":79008,"XL":79009,"2XL":79010,"3XL":79146},
        "Chambray":    {"S":78921,"M":78922,"L":78923,"XL":78924,"2XL":78925,"3XL":79124},
        "Blossom":     {"S":78886,"M":78887,"L":78888,"XL":78889,"2XL":78890,"3XL":79115},
    },
    "US_GD": {
        "Black":{"S":12126,"M":12125,"L":12124,"XL":12127,"2XL":12128,"3XL":12129},
        "White":{"S":12102,"M":12101,"L":12100,"XL":12103,"2XL":12104,"3XL":12105},
        "Grey": {"S":12072,"M":12071,"L":12070,"XL":12073,"2XL":12074,"3XL":12075},
    },
    "EU_CC": {
        "Black":       {"S":73196,"M":73200,"L":73204,"XL":73208,"2XL":73212,"3XL":79114},
        "White":       {"S":73199,"M":73203,"L":73207,"XL":73211,"2XL":73215,"3XL":79169},
        "Pepper":      {"S":79046,"M":79047,"L":79048,"XL":79049,"2XL":79050,"3XL":79155},
        "Grey":        {"S":78971,"M":78972,"L":78973,"XL":78974,"2XL":78975,"3XL":79137},
        "Ivory":       {"S":78991,"M":78992,"L":78993,"XL":78994,"2XL":78995,"3XL":79142},
        "Light Green": {"S":79006,"M":79007,"L":79008,"XL":79009,"2XL":79010,"3XL":79146},
        "Chambray":    {"S":78921,"M":78922,"L":78923,"XL":78924,"2XL":78925,"3XL":79124},
        "Washed Denim":{"S":79096,"M":79097,"L":79098,"XL":79099,"2XL":79100,"3XL":79167},
        "Blossom":     {"S":78886,"M":78887,"L":78888,"XL":78889,"2XL":78890,"3XL":79115},
    },
    "EU_GD": {
        "Black":{"S":12126,"M":12125,"L":12124,"XL":12127,"2XL":12128,"3XL":12129},
        "White":{"S":12102,"M":12101,"L":12100,"XL":12103,"2XL":12104,"3XL":12105},
        "Grey": {"S":12072,"M":12071,"L":12070,"XL":12073,"2XL":12074,"3XL":12075},
    },
}

# ── Load product index from checkpoint ────────────────────────────────────────
def load_product_index():
    index = {}
    if not os.path.exists(CHECKPOINT_PATH):
        return index
    cp = json.load(open(CHECKPOINT_PATH, encoding="utf-8"))
    for entry in cp.values():
        new_sid = entry.get("new_shopify_id")
        pids    = entry.get("printify_ids", {})
        if new_sid and pids:
            index[str(new_sid)] = pids
    return index

# ── Load / save routed orders log ─────────────────────────────────────────────
def load_routed():
    if os.path.exists(ROUTED_LOG_PATH):
        return set(json.load(open(ROUTED_LOG_PATH, encoding="utf-8")))
    return set()

def save_routed(routed: set):
    with open(ROUTED_LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(sorted(routed), f, indent=2)

# ── Determine route key ───────────────────────────────────────────────────────
def get_route_key(country: str, fabric: str) -> str:
    tier   = "CC" if "comfort" in fabric.lower() or "premium" in fabric.lower() else "GD"
    region = "UK" if country == "GB" else ("EU" if country in EU_COUNTRIES else "US")
    return f"{region}_{tier}"

# ── Fetch recent paid orders from Shopify ─────────────────────────────────────
def fetch_paid_orders(since_minutes=10):
    since = (datetime.now(timezone.utc) - timedelta(minutes=since_minutes)).isoformat()
    url   = (f"{SAPI}/orders.json?status=open&financial_status=paid"
             f"&created_at_min={since}&limit=50"
             f"&fields=id,order_number,email,shipping_address,line_items,financial_status")
    r = httpx.get(url, headers=SHR, timeout=20)
    if r.status_code != 200:
        print(f"  Shopify fetch error {r.status_code}: {r.text[:150]}")
        return []
    return r.json().get("orders", [])

# ── Create Printify order ─────────────────────────────────────────────────────
def create_printify_order(printify_pid, order, item, color, size, route_key):
    vid = VARIANT_MAPS.get(route_key, {}).get(color, {}).get(size)
    if not vid:
        raise ValueError(f"No variant for {route_key}/{color}/{size}")

    ship = order.get("shipping_address") or {}
    body = {
        "external_id": f"shopify-{order['id']}-{item['id']}",
        "label":       f"Shopify #{order['order_number']}",
        "line_items":  [{"product_id": printify_pid, "variant_id": vid,
                         "quantity": item.get("quantity", 1)}],
        "shipping_method": 1,
        "send_shipping_notification": False,
        "address_to": {
            "first_name": ship.get("first_name",""),
            "last_name":  ship.get("last_name",""),
            "email":      order.get("email",""),
            "phone":      ship.get("phone",""),
            "country":    ship.get("country_code","GB"),
            "region":     ship.get("province_code",""),
            "address1":   ship.get("address1",""),
            "address2":   ship.get("address2",""),
            "city":       ship.get("city",""),
            "zip":        ship.get("zip",""),
        },
    }
    for attempt in range(4):
        r = httpx.post(f"{PAPI}/shops/{SHOP_ID}/orders.json",
                       headers=PH, json=body, timeout=30)
        if r.status_code == 429:
            time.sleep(20 + attempt * 10)
            continue
        if r.status_code not in (200, 201):
            raise Exception(f"Printify order failed {r.status_code}: {r.text[:300]}")
        return r.json()
    raise Exception("Printify order failed after retries")

# ── Process one poll cycle ─────────────────────────────────────────────────────
def process_once(product_index, routed, since_minutes=10):
    orders = fetch_paid_orders(since_minutes)
    if not orders:
        return 0

    new_routes = 0
    for order in orders:
        order_key = str(order["id"])
        country   = (order.get("shipping_address") or {}).get("country_code", "US")

        for item in order.get("line_items", []):
            item_key = f"{order_key}-{item['id']}"
            if item_key in routed:
                continue

            product_id   = str(item.get("product_id",""))
            printify_ids = product_index.get(product_id)
            if not printify_ids:
                continue  # not one of our migrated products

            # Parse Color / Size / Fabric from variant title
            # Shopify variant title format: "Black / M / Premium Comfort Colors"
            parts  = [p.strip() for p in item.get("variant_title","").split("/")]
            if len(parts) != 3:
                print(f"  [Order #{order['order_number']}] Unexpected variant title: "
                      f"'{item.get('variant_title')}' — skipping")
                continue

            color, size, fabric = parts[0], parts[1], parts[2]
            route_key = get_route_key(country, fabric)
            p_pid     = printify_ids.get(route_key)

            if not p_pid:
                print(f"  [Order #{order['order_number']}] No Printify product "
                      f"for route {route_key} — skipping")
                continue

            try:
                result = create_printify_order(p_pid, order, item, color, size, route_key)
                print(f"  ✓ Order #{order['order_number']} | {color}/{size}/{fabric} "
                      f"→ {route_key} (Printify {result.get('id')})")
                routed.add(item_key)
                save_routed(routed)
                new_routes += 1
            except Exception as e:
                print(f"  ✗ Order #{order['order_number']} | {color}/{size} ERROR: {e}")

    return new_routes

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once",   action="store_true", help="Run one poll then exit")
    ap.add_argument("--status", action="store_true", help="Show routing stats and exit")
    ap.add_argument("--since",  type=int, default=10,
                    help="How many minutes back to check for orders (default 10)")
    args = ap.parse_args()

    product_index = load_product_index()
    routed        = load_routed()

    if args.status:
        print(f"Products indexed : {len(product_index)}")
        print(f"Line items routed: {len(routed)}")
        return

    print(f"Auto-router started — {len(product_index)} products indexed")
    print(f"Previously routed: {len(routed)} line items")

    if args.once:
        n = process_once(product_index, routed, args.since)
        print(f"Routed {n} new line item(s)")
        return

    # Continuous loop
    print(f"Polling every {POLL_INTERVAL//60} minutes. Ctrl+C to stop.\n")
    while True:
        now = datetime.now().strftime("%H:%M:%S")
        print(f"[{now}] Checking for new orders...")
        try:
            n = process_once(product_index, routed, since_minutes=POLL_INTERVAL//60 + 2)
            if n == 0:
                print(f"[{now}] No new orders")
        except Exception as e:
            print(f"[{now}] Poll error: {e}")
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
