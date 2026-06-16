"""
order_router.py — Matcha Tee order routing webhook
===================================================
FastAPI service that receives Shopify order webhooks and creates the
correct Printify order based on customer country + fabric variant.

Routing logic:
  Customer in GB         → UK provider  (Shirt Monkey)
  Customer in EU country → EU provider  (Printify Choice / Textildruck)
  Everyone else          → US provider  (Monster Digital)

Run locally:   uvicorn order_router:app --port 8001 --reload
Deploy to:     Railway / Render / any host with a public HTTPS URL

Then register the webhook in Shopify:
  python register_webhook.py --url https://your-host.com/webhook/orders/paid
"""
import os, json, hmac, hashlib, base64, httpx, time
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

SHOPIFY_SECRET = os.environ.get("SHOPIFY_WEBHOOK_SECRET", "")
PRINTIFY_TOKEN = os.environ["PRINTIFY_TOKEN"]
SHOP_ID        = 27883571
PAPI           = "https://api.printify.com/v1"
PH             = {"Authorization": f"Bearer {PRINTIFY_TOKEN}", "Content-Type": "application/json"}

CHECKPOINT_PATH = os.path.join(os.path.dirname(__file__), "full_checkpoint.json")

# EU country codes (ISO 3166-1 alpha-2)
EU_COUNTRIES = {
    "AT","BE","BG","CY","CZ","DE","DK","EE","ES","FI","FR","GR","HR",
    "HU","IE","IT","LT","LU","LV","MT","NL","PL","PT","RO","SE","SI","SK",
}

app = FastAPI(title="Matcha Tee Order Router")

# ── Load checkpoint (printify_ids index) ─────────────────────────────────────
def load_product_index():
    """Build a shopify_product_id → printify_ids lookup from checkpoint."""
    index = {}
    if not os.path.exists(CHECKPOINT_PATH):
        return index
    cp = json.load(open(CHECKPOINT_PATH, encoding="utf-8"))
    for _old_sid, entry in cp.items():
        new_sid = entry.get("new_shopify_id")
        pids    = entry.get("printify_ids", {})
        if new_sid and pids:
            index[str(new_sid)] = pids
    return index

# ── Verify Shopify webhook HMAC ───────────────────────────────────────────────
def verify_webhook(body: bytes, hmac_header: str) -> bool:
    if not SHOPIFY_SECRET:
        return True  # skip verification in dev
    digest = hmac.new(SHOPIFY_SECRET.encode(), body, hashlib.sha256).digest()
    computed = base64.b64encode(digest).decode()
    return hmac.compare_digest(computed, hmac_header or "")

# ── Determine routing key from country + fabric ───────────────────────────────
def get_route_key(country_code: str, fabric: str) -> str:
    tier = "CC" if "comfort" in fabric.lower() or "premium" in fabric.lower() else "GD"
    if country_code == "GB":
        region = "UK"
    elif country_code in EU_COUNTRIES:
        region = "EU"
    else:
        region = "US"
    return f"{region}_{tier}"

# ── Get Printify variant ID for a color+size+key ──────────────────────────────
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

def get_variant_id(route_key: str, color: str, size: str):
    vmap = VARIANT_MAPS.get(route_key, {})
    return vmap.get(color, {}).get(size)

# ── Create Printify order ─────────────────────────────────────────────────────
def create_printify_order(printify_product_id: str, order: dict, line_item: dict,
                          color: str, size: str, route_key: str):
    ship = order.get("shipping_address", {})
    vid  = get_variant_id(route_key, color, size)
    if not vid:
        raise ValueError(f"No Printify variant for {route_key} / {color} / {size}")

    body = {
        "external_id": f"shopify-{order['id']}-{line_item['id']}",
        "label":       f"Shopify #{order['order_number']}",
        "line_items":  [{
            "product_id":  printify_product_id,
            "variant_id":  vid,
            "quantity":    line_item.get("quantity", 1),
        }],
        "shipping_method": 1,
        "send_shipping_notification": False,
        "address_to": {
            "first_name": ship.get("first_name", ""),
            "last_name":  ship.get("last_name", ""),
            "email":      order.get("email", ""),
            "phone":      ship.get("phone", ""),
            "country":    ship.get("country_code", "GB"),
            "region":     ship.get("province_code", ""),
            "address1":   ship.get("address1", ""),
            "address2":   ship.get("address2", ""),
            "city":       ship.get("city", ""),
            "zip":        ship.get("zip", ""),
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

# ── Process order (runs in background) ───────────────────────────────────────
def process_order(order: dict):
    product_index = load_product_index()
    country = (order.get("shipping_address") or {}).get("country_code", "US")
    order_num = order.get("order_number", "?")

    print(f"\n[ORDER #{order_num}] country={country}")

    for item in order.get("line_items", []):
        product_id = str(item.get("product_id", ""))
        printify_ids = product_index.get(product_id)

        if not printify_ids:
            print(f"  [{item['title']}] — product not in index, skipping")
            continue

        # Extract options
        props  = {p["name"]: p["value"] for p in item.get("properties", [])}
        color  = item.get("variant_title", "").split(" / ")[0] if not props.get("Color") else props["Color"]
        size   = props.get("Size", "")
        fabric = props.get("Fabric", "")

        # Fall back to parsing variant title: "Black / M / Premium Comfort Colors"
        if not size or not fabric:
            parts = [p.strip() for p in item.get("variant_title", "").split("/")]
            if len(parts) == 3:
                color, size, fabric = parts[0], parts[1], parts[2]

        route_key     = get_route_key(country, fabric)
        printify_pid  = printify_ids.get(route_key)

        if not printify_pid:
            print(f"  [{item['title']}] No Printify product for route {route_key}")
            continue

        try:
            result = create_printify_order(printify_pid, order, item, color, size, route_key)
            print(f"  [{item['title']}] ✓ Printify order {result.get('id')} via {route_key}")
        except Exception as e:
            print(f"  [{item['title']}] ERROR: {e}")

# ── Webhook endpoint ──────────────────────────────────────────────────────────
@app.post("/webhook/orders/paid")
async def orders_paid(request: Request, background_tasks: BackgroundTasks):
    body = await request.body()
    hmac_header = request.headers.get("X-Shopify-Hmac-Sha256", "")

    if not verify_webhook(body, hmac_header):
        raise HTTPException(status_code=401, detail="Invalid HMAC")

    order = json.loads(body)
    background_tasks.add_task(process_order, order)
    return {"status": "queued"}

@app.get("/health")
def health():
    index = load_product_index()
    return {"status": "ok", "products_indexed": len(index)}
