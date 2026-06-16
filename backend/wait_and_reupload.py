"""
wait_and_reupload.py
Polls until all 99 checkpoint products have design PNGs, then runs reupload_designs.py.
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
    products.append(v.get("title", ""))

print(f"Watching for {len(products)} design PNGs...")

while True:
    missing = [t for t in products if not find_png(t)]
    total_pngs = len([f for f in os.listdir(DESIGNS_DIR) if f.endswith(".png")])
    print(f"  Total extracted: {total_pngs}/1525  |  Checkpoint missing: {len(missing)}", flush=True)
    if not missing:
        print("\nAll checkpoint PNGs ready — launching reupload_designs.py...\n")
        break
    time.sleep(20)

result = subprocess.run([sys.executable, os.path.join(BASE, "reupload_designs.py")], cwd=BASE)
sys.exit(result.returncode)
