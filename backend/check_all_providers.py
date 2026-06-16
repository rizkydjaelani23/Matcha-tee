"""Check all providers for CC1717 to find Neon Pink."""
import httpx, os, sys
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

PTOKEN = os.environ["PRINTIFY_TOKEN"]
PAPI = "https://api.printify.com/v1"
PH = {"Authorization": f"Bearer {PTOKEN}"}
BLUEPRINT_ID = 706

# Get all providers
r = httpx.get(f"{PAPI}/catalog/blueprints/{BLUEPRINT_ID}/print_providers.json", headers=PH, timeout=20)
providers = r.json()
print(f"Checking {len(providers)} providers for Neon Pink...\n")

for p in providers:
    pid = p["id"]
    pname = p["title"]
    r2 = httpx.get(f"{PAPI}/catalog/blueprints/{BLUEPRINT_ID}/print_providers/{pid}/variants.json",
                   headers=PH, timeout=20)
    variants = r2.json().get("variants", [])
    colors = set()
    for v in variants:
        color = v.get("options", {}).get("color", "")
        if color:
            colors.add(color)

    pink_colors = [c for c in colors if "pink" in c.lower() or "neon" in c.lower()]
    if pink_colors:
        print(f"  Provider {pid} ({pname}): FOUND → {pink_colors}")
    else:
        print(f"  Provider {pid} ({pname}): no neon/pink  [{len(colors)} colors total]")
