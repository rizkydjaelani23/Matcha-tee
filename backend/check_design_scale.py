"""Check Printify product image placements to detect small/off-center designs."""
import httpx, os, sys, json
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

PTOKEN  = os.environ["PRINTIFY_TOKEN"]
PAPI    = "https://api.printify.com/v1"
SHOP_ID = 27883571
PH      = {"Authorization": f"Bearer {PTOKEN}"}

# Load a page of Printify products
r = httpx.get(f"{PAPI}/shops/{SHOP_ID}/products.json?limit=10", headers=PH, timeout=30)
products = r.json().get("data", [])
print(f"Checking {len(products)} products for design scale/position...\n")

for p in products:
    pid   = p["id"]
    title = p["title"]
    # Fetch full product to get print_areas
    r2 = httpx.get(f"{PAPI}/shops/{SHOP_ID}/products/{pid}.json", headers=PH, timeout=20)
    if r2.status_code != 200:
        continue
    full = r2.json()
    areas = full.get("print_areas", [])
    for area in areas:
        for ph in area.get("placeholders", []):
            for img in ph.get("images", []):
                scale = img.get("scale", "?")
                x     = img.get("x", "?")
                y     = img.get("y", "?")
                flag  = " ⚠ SMALL" if isinstance(scale, (int,float)) and scale < 0.5 else ""
                print(f"  {title[:50]:50}  scale={scale}  x={x}  y={y}{flag}")
