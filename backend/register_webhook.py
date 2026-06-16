"""
register_webhook.py — Register the order router webhook in Shopify
Usage: python register_webhook.py --url https://your-host.com/webhook/orders/paid
"""
import os, sys, argparse, httpx
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

STORE         = os.environ["SHOPIFY_STORE"]
SHOPIFY_TOKEN = os.environ["SHOPIFY_TOKEN"]
SH            = {"X-Shopify-Access-Token": SHOPIFY_TOKEN, "Content-Type": "application/json"}
SAPI          = f"https://{STORE}/admin/api/2025-01"

ap = argparse.ArgumentParser()
ap.add_argument("--url",  required=True, help="Public URL of the order router endpoint")
ap.add_argument("--list", action="store_true", help="List existing webhooks")
ap.add_argument("--delete", type=int, help="Delete webhook by ID")
args = ap.parse_args()

if args.list:
    r = httpx.get(f"{SAPI}/webhooks.json", headers=SH, timeout=15)
    for wh in r.json().get("webhooks", []):
        print(f"  ID={wh['id']}  topic={wh['topic']}  address={wh['address']}")
    sys.exit(0)

if args.delete:
    r = httpx.delete(f"{SAPI}/webhooks/{args.delete}.json", headers=SH, timeout=15)
    print(f"Deleted webhook {args.delete}: {r.status_code}")
    sys.exit(0)

# Register orders/paid webhook
payload = {"webhook": {
    "topic":   "orders/paid",
    "address": args.url,
    "format":  "json",
}}
r = httpx.post(f"{SAPI}/webhooks.json", headers=SH, json=payload, timeout=15)
if r.status_code in (200, 201):
    wh = r.json()["webhook"]
    print(f"Webhook registered!")
    print(f"  ID:     {wh['id']}")
    print(f"  Topic:  {wh['topic']}")
    print(f"  URL:    {wh['address']}")
    print(f"\nAdd this secret to your .env:")
    print(f"  SHOPIFY_WEBHOOK_SECRET={wh.get('api_client_id','<get from Shopify Partners dashboard>')}")
else:
    print(f"Failed {r.status_code}: {r.text}")
