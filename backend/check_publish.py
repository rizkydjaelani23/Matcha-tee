import os, httpx, json, sys, time
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
TOKEN = os.environ["PRINTIFY_TOKEN"]
PH = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
PAPI = "https://api.printify.com/v1"
SHOP_ID = 27883571
PID = "6a2f6bc7a4bf9acfe9043bcf"

r = httpx.get(f"{PAPI}/shops/{SHOP_ID}/products/{PID}.json", headers=PH, timeout=20)
p = r.json()
print("Status:", r.status_code)
print("visible:", p.get("visible"))
print("is_locked:", p.get("is_locked"))
print("external:", json.dumps(p.get("external"), indent=2))
print("Keys:", list(p.keys()))

print("\nPublishing...")
r2 = httpx.post(
    f"{PAPI}/shops/{SHOP_ID}/products/{PID}/publish.json",
    headers=PH,
    json={"title": True, "description": True, "images": True,
          "variants": True, "tags": True, "keyFeatures": True, "shipping_template": True},
    timeout=30,
)
print("Publish status:", r2.status_code)
print("Response:", r2.text[:600])

# Wait and re-check
print("\nWaiting 8 seconds...")
time.sleep(8)
r3 = httpx.get(f"{PAPI}/shops/{SHOP_ID}/products/{PID}.json", headers=PH, timeout=20)
p3 = r3.json()
print("external after publish:", json.dumps(p3.get("external"), indent=2))
