import httpx, os, sys, json
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
STORE=os.environ["SHOPIFY_STORE"]; TOKEN=os.environ["SHOPIFY_TOKEN"]
H={"X-Shopify-Access-Token":TOKEN}
API=f"https://{STORE}/admin/api/2025-01"
r=httpx.get(f"{API}/notifications.json",headers=H,timeout=20)
notifs=r.json().get("notifications",[])
for n in notifs:
    print(n["id"],"|",n["event"],"|",n.get("subject","")[:60])
