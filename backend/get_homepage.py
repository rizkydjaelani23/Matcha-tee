import httpx, os, json
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
token = os.environ["SHOPIFY_TOKEN"]
store = os.environ["SHOPIFY_STORE"]
headers = {"X-Shopify-Access-Token": token}

r = httpx.get(f"https://{store}/admin/api/2025-01/themes/143507587185/assets.json",
    headers=headers, params={"asset[key]": "templates/index.json"}, timeout=20)
content = r.json()["asset"]["value"]
parsed = json.loads(content)
print("Section order:", parsed.get("order", []))
print("Section types:")
for k, v in parsed["sections"].items():
    t = v["type"]
    print(f"  {k}: {t}")
