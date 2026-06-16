"""Search Printify providers for Textiledruck — check all blueprints if needed."""
import httpx, os, sys
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

PTOKEN = os.environ["PRINTIFY_TOKEN"]
PAPI   = "https://api.printify.com/v1"
PH     = {"Authorization": f"Bearer {PTOKEN}"}

# First: check all providers for CC1717 (BP 706)
print("=== All providers for Blueprint 706 (CC1717) ===")
r = httpx.get(f"{PAPI}/catalog/blueprints/706/print_providers.json", headers=PH, timeout=20)
for p in r.json():
    print(f"  ID={p['id']:4d}  {p['title']}")

# Second: search across a broader set of blueprints for any provider with "textile" or "druck" in name
print("\n=== Scanning all blueprints for 'textile' or 'druck' providers ===")
rb = httpx.get(f"{PAPI}/catalog/blueprints.json", headers=PH, timeout=30)
blueprints = rb.json()
print(f"Total blueprints: {len(blueprints)}")

found = {}
for bp in blueprints:
    bid   = bp["id"]
    btitle = bp["title"]
    rp = httpx.get(f"{PAPI}/catalog/blueprints/{bid}/print_providers.json", headers=PH, timeout=20)
    if rp.status_code != 200:
        continue
    for p in rp.json():
        name = p["title"].lower()
        if "textile" in name or "druck" in name or "textiledruck" in name:
            key = (p["id"], p["title"])
            if key not in found:
                found[key] = []
                print(f"  FOUND: {p['title']} (ID={p['id']}) — on blueprint {bid}: {btitle}")
            found[key].append(bid)

if not found:
    print("  No providers with 'textile' or 'druck' found across all blueprints.")
