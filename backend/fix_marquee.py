import httpx, os, json, sys
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
TOKEN = os.environ["SHOPIFY_TOKEN"]
STORE = os.environ["SHOPIFY_STORE"]
THEME = 143507587185
BASE  = f"https://{STORE}/admin/api/2025-01/themes/{THEME}/assets.json"
H     = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}

raw    = httpx.get(BASE, headers=H, params={"asset[key]": "templates/index.json"}, timeout=20).json()["asset"]["value"]
parsed = json.loads(raw)

new_text = (
    "<p>New designs weekly &nbsp;•&nbsp; "
    "Worldwide tracked delivery &mdash; we ship anywhere &nbsp;•&nbsp; "
    "100% quality guaranteed &nbsp;•&nbsp; "
    "24-hour happiness guarantee &nbsp;•&nbsp;</p>"
)

parsed["sections"]["marquee_strip"]["blocks"]["marquee_text"]["settings"]["text"] = new_text

r = httpx.put(BASE, headers=H, json={"asset": {"key": "templates/index.json", "value": json.dumps(parsed, indent=2)}}, timeout=20)
print(r.status_code, "OK" if r.status_code in (200, 201) else r.text[:300])
print(f"\nNew marquee: {new_text}")
