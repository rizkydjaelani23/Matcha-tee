"""Dump the full top-level structure of settings_data.json."""
import os, sys, json, httpx
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

STORE    = os.environ["SHOPIFY_STORE"]
TOKEN    = os.environ["SHOPIFY_TOKEN"]
RH       = {"X-Shopify-Access-Token": TOKEN}
API      = f"https://{STORE}/admin/api/2025-01"
THEME_ID = 143507587185

r = httpx.get(f"{API}/themes/{THEME_ID}/assets.json", headers=RH,
              params={"asset[key]": "config/settings_data.json"}, timeout=15)
raw = r.json()["asset"]["value"]
settings = json.loads(raw)

def dump_structure(obj, prefix="", depth=0):
    if depth > 4:
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, (dict, list)):
                vlen = len(v)
                print(f"{'  '*depth}{prefix}{k}: {type(v).__name__}({vlen})")
                if vlen > 0 and vlen <= 5:
                    dump_structure(v, "", depth+1)
            else:
                print(f"{'  '*depth}{prefix}{k}: {repr(v)[:80]}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj[:3]):
            dump_structure(v, f"[{i}].", depth)
        if len(obj) > 3:
            print(f"{'  '*depth}... ({len(obj)} total items)")

dump_structure(settings)

# Also show the raw size
print(f"\nTotal settings_data.json size: {len(raw)} chars")

# Check if there's a 'sections' key at any level
def find_key(obj, target, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            new_path = f"{path}.{k}" if path else k
            if k == target:
                print(f"Found '{target}' at: {new_path}  len={len(v) if hasattr(v, '__len__') else 'n/a'}")
            find_key(v, target, new_path)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            find_key(v, target, f"{path}[{i}]")

print("\n=== Finding all 'sections' keys ===")
find_key(settings, "sections")
