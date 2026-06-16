"""Find no-image products, pull mockup images from Printify, push to Shopify."""
import httpx, os, sys, json, time
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

TOKEN    = os.environ["SHOPIFY_TOKEN"]
STORE    = os.environ["SHOPIFY_STORE"]
PTOKEN   = os.environ["PRINTIFY_TOKEN"]
BASE     = f"https://{STORE}/admin/api/2025-01"
PAPI     = "https://api.printify.com/v1"
SHOP_ID  = 27883571
HR       = {"X-Shopify-Access-Token": TOKEN}
H        = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}
PH       = {"Authorization": f"Bearer {PTOKEN}"}

# No-image products found in the audit
NO_IMAGE_IDS = [
    7697693147249,  # JENNA MARBLES Retro T-shirt
    7697699536497,  # JAMIE CAMPBELL BOWER Retro T-shirt  (need to verify IDs)
    7697700061297,  # JAMIE CAMPBELL Retro T-shirt
]

# Get all no-image products fresh
print("Finding all no-image active products...")
url = f"{BASE}/products.json?limit=250&fields=id,title,handle,images,status"
no_image = []
while url:
    r = httpx.get(url, headers=HR, timeout=30)
    for p in r.json().get("products", []):
        if len(p.get("images", [])) == 0 and p.get("status") == "active":
            no_image.append(p)
    link = r.headers.get("Link", "")
    url = None
    for part in link.split(","):
        if 'rel="next"' in part:
            url = part.strip().split(";")[0].strip("<> ")

print(f"Found {len(no_image)} no-image products")

# Load checkpoint to find Printify IDs for these products
checkpoint = {}
cp_path = os.path.join(os.path.dirname(__file__), "sync_checkpoint.json")
if os.path.exists(cp_path):
    checkpoint = json.load(open(cp_path, encoding="utf-8"))

# Build map: shopify_id -> printify_id from checkpoint
shopify_to_printify = {}
for old_shopify_id, data in checkpoint.items():
    new_sid = data.get("new_shopify_id")
    pid     = data.get("printify_id")
    if new_sid and pid:
        shopify_to_printify[str(new_sid)] = pid

print(f"Checkpoint has {len(shopify_to_printify)} shopify→printify mappings")

# Also load all Printify products for cross-referencing by title
print("Loading Printify product list...")
r = httpx.get(f"{PAPI}/shops/{SHOP_ID}/products.json?limit=100", headers=PH, timeout=30)
printify_by_title = {}
if r.status_code == 200:
    for p in r.json().get("data", []):
        printify_by_title[p["title"].lower().strip()] = p["id"]
    print(f"  Loaded {len(printify_by_title)} Printify products")

fixed = 0
for sp in no_image:
    sid   = str(sp["id"])
    title = sp["title"]
    print(f"\n--- {title} (shopify_id={sid}) ---")

    # Find Printify ID
    pid = shopify_to_printify.get(sid)
    if not pid:
        pid = printify_by_title.get(title.lower().strip())
    if not pid:
        print(f"  No Printify ID found — skipping (old product, will be synced later)")
        continue

    print(f"  Printify ID: {pid}")

    # Get Printify product images
    r2 = httpx.get(f"{PAPI}/shops/{SHOP_ID}/products/{pid}.json", headers=PH, timeout=20)
    if r2.status_code != 200:
        print(f"  Printify fetch failed: {r2.status_code}")
        continue
    pp = r2.json()
    images = pp.get("images", [])
    print(f"  Printify has {len(images)} images")

    if not images:
        print(f"  No images on Printify either — cannot fix automatically")
        continue

    # Upload images to Shopify
    for i, img in enumerate(images[:5]):  # max 5 images
        src = img.get("src")
        if not src:
            continue
        r3 = httpx.post(f"{BASE}/products/{sp['id']}/images.json", headers=H,
            json={"image": {"src": src, "position": i+1}}, timeout=30)
        if r3.status_code in (200, 201):
            print(f"  Added image {i+1}: {src[src.rfind('/')+1:src.rfind('/')+50]}")
        else:
            print(f"  Image {i+1} failed: {r3.status_code} {r3.text[:100]}")
        time.sleep(0.3)
    fixed += 1

print(f"\nFixed {fixed} products.")
