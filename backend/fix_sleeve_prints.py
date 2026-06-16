"""
fix_sleeve_prints.py
====================
Strips all non-front print areas from every Printify product.
These are front-print-only designs — back, sleeves etc. add cost for nothing.

Applies to all 6 pkeys: UK_CC, UK_GD, US_CC, US_GD, EU_CC, EU_GD
Keeps: front only
Removes: back, right_sleeve, left_sleeve, and any other positions

Run:
  python fix_sleeve_prints.py --dry   # preview
  python fix_sleeve_prints.py --limit 1 --dry  # check one product
  python fix_sleeve_prints.py         # apply all
"""
import argparse, json, os, sys, time
import httpx
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

TOKEN   = os.environ["PRINTIFY_TOKEN"]
SHOP_ID = 27883571
PH      = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
PAPI    = "https://api.printify.com/v1"

# All 6 pkeys — front only for everything
ALL_KEYS      = ["UK_CC", "UK_GD", "US_CC", "US_GD", "EU_CC", "EU_GD"]
KEEP_POSITIONS = {"front"}

BASE    = os.path.dirname(os.path.abspath(__file__))
CP_FILE = os.path.join(BASE, "full_checkpoint.json")


def p_get(path):
    for _ in range(5):
        r = httpx.get(f"{PAPI}{path}", headers=PH, timeout=60)
        if r.status_code == 429:
            time.sleep(float(r.headers.get("Retry-After", 30)))
            continue
        return r
    return r


def p_put(path, body):
    for _ in range(5):
        r = httpx.put(f"{PAPI}{path}", headers=PH, json=body, timeout=120)
        if r.status_code == 429:
            time.sleep(float(r.headers.get("Retry-After", 30)))
            continue
        return r
    return r


def fix_product(ppid, pkey, dry=False):
    r = p_get(f"/shops/{SHOP_ID}/products/{ppid}.json")
    if r.status_code == 404:
        return "not_found", []
    if r.status_code != 200:
        return f"get_err:{r.status_code}", []

    product    = r.json()
    print_areas = product.get("print_areas", [])
    removed_positions = set()
    updated = []

    for area in print_areas:
        kept = []
        for ph in area.get("placeholders", []):
            pos = ph.get("position", "")
            if pos in KEEP_POSITIONS:
                kept.append(ph)
            else:
                removed_positions.add(pos)
        if kept:
            updated.append({"variant_ids": area.get("variant_ids", []), "placeholders": kept})

    if not removed_positions:
        return "no_sleeves", []

    if dry:
        return f"dry_ok(removed:{','.join(sorted(removed_positions))})", list(removed_positions)

    r2 = p_put(f"/shops/{SHOP_ID}/products/{ppid}.json", {"print_areas": updated})
    if r2.status_code in (200, 201):
        return f"ok(removed:{','.join(sorted(removed_positions))})", list(removed_positions)
    return f"put_err:{r2.status_code}", []


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry",   action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    cp = json.load(open(CP_FILE, encoding="utf-8"))
    seen, products = set(), []
    for v in cp.values():
        if v.get("status") != "done":
            continue
        t = (v.get("title") or "").strip().lower()
        if t in seen:
            continue
        seen.add(t)
        products.append(v)

    if args.limit:
        products = products[:args.limit]

    mode = "DRY RUN" if args.dry else "LIVE"
    print(f"[{mode}] Stripping to front-only on {len(products)} products (all 6 pkeys)\n")

    fixed = skipped = failed = 0

    for i, entry in enumerate(products, 1):
        title   = entry.get("title", "")[:55]
        pid_map = entry.get("printify_ids", {})

        product_had_sleeves = False
        results = {}

        for pkey in ALL_KEYS:
            ppid = pid_map.get(pkey)
            if not ppid:
                results[pkey] = "no_id"
                continue
            status, removed = fix_product(ppid, pkey, dry=args.dry)
            results[pkey] = status
            if removed:
                product_had_sleeves = True
            if not args.dry:
                time.sleep(0.7)

        result_str = "  ".join(f"{k}:{v}" for k, v in results.items())
        if product_had_sleeves:
            print(f"[{i}/{len(products)}] {title}")
            print(f"  {result_str}")
            if "err" in result_str:
                failed += 1
            else:
                fixed += 1
        else:
            skipped += 1

        if not args.dry:
            time.sleep(0.5)

    print(f"\n{'='*60}")
    print(f"Fixed: {fixed}  Already clean: {skipped}  Failed: {failed}")
    if not args.dry:
        print(f"\nCost impact: front-only should reduce production costs for all products.")
        print(f"Allow ~5-10 min for Printify to recalculate variant costs.")
        print(f"Then run check_printify_costs.py to verify new prices.")


if __name__ == "__main__":
    main()
