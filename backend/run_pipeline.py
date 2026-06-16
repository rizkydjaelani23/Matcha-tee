"""
run_pipeline.py
Waits until all 99 checkpoint products have design PNGs, then:
  1. reupload_designs.py  — push fixed artwork to Printify print areas
  2. 90-second pause      — give Printify time to regenerate mockup images
  3. sync_color_images.py — pull fresh Printify mockups into Shopify (color-matched)
"""
import json, os, re, subprocess, sys, time

sys.stdout.reconfigure(encoding="utf-8")
BASE = os.path.dirname(os.path.abspath(__file__))

CP_FILE     = os.path.join(BASE, "full_checkpoint.json")
DESIGNS_DIR = os.path.join(BASE, "designs")

def slug(title):
    return re.sub(r"[^a-z0-9]+", "-", (title or "").lower()).strip("-")

def find_png(title):
    handle = slug(title)
    p = os.path.join(DESIGNS_DIR, f"{handle}.png")
    if os.path.exists(p):
        return p
    key = re.sub(r"[^a-z0-9]", "", (title or "").lower())[:15]
    for f in os.listdir(DESIGNS_DIR):
        if f.endswith(".png") and re.sub(r"[^a-z0-9]", "", f[:-4].lower()).startswith(key):
            return os.path.join(DESIGNS_DIR, f)
    return None

cp = json.load(open(CP_FILE, encoding="utf-8"))
seen, products = set(), []
for v in cp.values():
    if v.get("status") != "done":
        continue
    t = (v.get("title") or "").strip().lower()
    if t in seen:
        continue
    seen.add(t)
    # Skip products with no Shopify presence AND no local image — they can never
    # be extracted (no source image available anywhere)
    if not v.get("new_shopify_id"):
        print(f"  Skipping (no Shopify / no image): {v.get('title','')[:60]}")
        continue
    products.append(v.get("title", ""))

print(f"Watching for {len(products)} design PNGs...", flush=True)

while True:
    missing = [t for t in products if not find_png(t)]
    total   = len([f for f in os.listdir(DESIGNS_DIR) if f.endswith(".png")])
    print(f"  Extracted: {total}  |  Missing: {len(missing)}", flush=True)
    if not missing:
        break
    time.sleep(20)

print("\nAll PNGs ready — step 1: reupload to Printify...\n", flush=True)
r1 = subprocess.run([sys.executable, os.path.join(BASE, "reupload_designs.py")], cwd=BASE)

print(f"\nReupload done (exit {r1.returncode}). Waiting 90s for Printify to regenerate mockups...", flush=True)
time.sleep(90)

print("\nStep 2: sync fresh Printify mockups to Shopify...\n", flush=True)
r2 = subprocess.run([sys.executable, os.path.join(BASE, "sync_color_images.py")], cwd=BASE)

print(f"\nAll done. reupload={r1.returncode}  sync={r2.returncode}", flush=True)
