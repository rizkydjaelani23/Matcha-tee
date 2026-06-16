"""Find Comfort Colors brand blueprint on Printify."""
import httpx, os, sys, json
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

PTOKEN = os.environ["PRINTIFY_TOKEN"]
PAPI = "https://api.printify.com/v1"
PH = {"Authorization": f"Bearer {PTOKEN}"}

print("Searching for Comfort Colors brand blueprints...")
r = httpx.get(f"{PAPI}/catalog/blueprints.json", headers=PH, timeout=30)
blueprints = r.json()

# Search specifically for "Comfort Colors" brand
comfort = [b for b in blueprints if "comfort colors" in b.get("title", "").lower()
           or "comfort colors" in b.get("brand", "").lower()
           or "comfort colors" in (b.get("description", "") or "").lower()]

print(f"Found {len(comfort)} Comfort Colors brand blueprints:\n")
for b in comfort:
    print(f"  ID={b['id']}  title={b['title']}")
    desc = (b.get("description") or "")[:120]
    print(f"    {desc}")
    print()

# Also check blueprint structure keys
if blueprints:
    print("Blueprint keys:", list(blueprints[0].keys()))
