"""Check footer.liquid schema presets to understand default blocks."""
import os, sys, json, re, httpx
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

STORE    = os.environ["SHOPIFY_STORE"]
TOKEN    = os.environ["SHOPIFY_TOKEN"]
RH       = {"X-Shopify-Access-Token": TOKEN}
API      = f"https://{STORE}/admin/api/2025-01"
THEME_ID = 143507587185

r = httpx.get(f"{API}/themes/{THEME_ID}/assets.json", headers=RH,
              params={"asset[key]": "sections/footer.liquid"}, timeout=15)
content = r.json().get("asset", {}).get("value", "")

# Extract the schema JSON from {% schema %} ... {% endschema %}
m = re.search(r'\{%-?\s*schema\s*-?%\}(.*?)\{%-?\s*endschema\s*-?%\}', content, re.DOTALL)
if m:
    schema_raw = m.group(1).strip()
    try:
        schema = json.loads(schema_raw)
        # Show presets / default blocks
        print("Footer schema presets:")
        print(json.dumps(schema.get("presets", schema.get("default", {})), indent=2))
    except json.JSONDecodeError as e:
        print(f"JSON error: {e}")
        print(schema_raw[:2000])
else:
    print("No schema tag found")
    # Show last 3000 chars which usually has schema
    print(content[-3000:])
