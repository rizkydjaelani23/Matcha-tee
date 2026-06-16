import os
import re
import sys

import httpx
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

STORE = os.environ["SHOPIFY_STORE"]
H = {"X-Shopify-Access-Token": os.environ["SHOPIFY_TOKEN"]}
API = f"https://{STORE}/admin/api/2025-01"
THEME_ID = 143507587185

for key in ["sections/marquee.liquid", "sections/collection-list.liquid",
            "sections/collection-links.liquid"]:
    r = httpx.get(f"{API}/themes/{THEME_ID}/assets.json", headers=H,
                  params={"asset[key]": key}, timeout=30)
    val = r.json()["asset"].get("value", "")
    m = re.search(r"{%-?\s*schema\s*-?%}(.*?){%-?\s*endschema\s*-?%}", val, re.S)
    print(f"\n===== {key} =====")
    print(m.group(1).strip()[:3500] if m else "(no schema)")
