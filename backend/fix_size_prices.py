"""
fix_size_prices.py
==================
Updates Shopify variant prices for 2XL and 3XL Comfort Colors sizes
based on Printify's actual production cost uplift.

Printify UK_CC costs (pence):
  S/M/L/XL = 2367p (£23.67)  → retail £29.99  margin £6.32
  2XL       = 2574p (£25.74)  → retail £31.99  margin £6.25
  3XL       = 2797p (£27.97)  → retail £34.99  margin £7.02

Gildan (UK_GD): all sizes same cost (£26.26), no size upcharge.
  NOTE: GD retail (£25.99) is BELOW Printify cost (£26.26) — see warning below.

compare_at is set at 30% above retail (consistent with existing CC base).

Run:
  python fix_size_prices.py --dry   # preview changes, no writes
  python fix_size_prices.py         # apply to all products
  python fix_size_prices.py --limit 3 --dry  # preview first 3
"""
import argparse, json, os, sys, time
import httpx
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

STORE = os.environ["SHOPIFY_STORE"]
TOKEN = os.environ["SHOPIFY_TOKEN"]
HR    = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}
API   = f"https://{STORE}/admin/api/2025-01"

# Target prices for Comfort Colors only (Gildan: all sizes same cost, no upcharge)
CC_PRICES = {
    "2XL": {"price": "31.99", "compare_at_price": "41.99"},
    "3XL": {"price": "34.99", "compare_at_price": "45.99"},
}

# Gildan cost vs current retail — informational only
GD_COST_GBP  = 26.26
GD_RETAIL_GBP = 25.99

BASE    = os.path.dirname(os.path.abspath(__file__))
CP_FILE = os.path.join(BASE, "full_checkpoint.json")


def s_get(path):
    for _ in range(4):
        r = httpx.get(f"{API}{path}", headers=HR, timeout=25)
        if r.status_code == 429:
            ra = float(r.headers.get("Retry-After", 10))
            print(f"  rate-limited, waiting {ra:.0f}s")
            time.sleep(ra)
            continue
        return r
    return r


def s_put(path, body):
    for _ in range(4):
        r = httpx.put(f"{API}{path}", headers=HR, json=body, timeout=25)
        if r.status_code == 429:
            ra = float(r.headers.get("Retry-After", 10))
            time.sleep(ra)
            continue
        return r
    return r


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry",   action="store_true", help="Preview only, no writes")
    parser.add_argument("--limit", type=int, default=0, help="Process only first N products")
    args = parser.parse_args()

    # --- GD pricing warning ---
    loss = GD_RETAIL_GBP - GD_COST_GBP
    print("=" * 60)
    print("GILDAN PRICING NOTICE")
    print(f"  Printify UK_GD cost: £{GD_COST_GBP:.2f}")
    print(f"  Current retail:      £{GD_RETAIL_GBP:.2f}")
    print(f"  Margin per unit:     £{loss:.2f}  {'⚠ LOSS' if loss < 0 else 'OK'}")
    if loss < 0:
        print(f"  You are losing £{abs(loss):.2f} on every Gildan sale before shipping.")
        print(f"  Consider raising Gildan price to at least £{GD_COST_GBP + 2:.2f}+")
    print("=" * 60)
    print()

    cp = json.load(open(CP_FILE, encoding="utf-8"))
    seen, products = set(), []
    for v in cp.values():
        if v.get("status") != "done" or not v.get("new_shopify_id"):
            continue
        t = (v.get("title") or "").strip().lower()
        if t in seen:
            continue
        seen.add(t)
        products.append(v)

    if args.limit:
        products = products[:args.limit]

    mode = "DRY RUN" if args.dry else "LIVE"
    print(f"[{mode}] Processing {len(products)} products\n")

    total_changed = total_already_ok = total_no_variant = 0

    for i, entry in enumerate(products, 1):
        pid   = entry["new_shopify_id"]
        title = entry.get("title", "")[:55]

        r = s_get(f"/products/{pid}/variants.json?limit=250")
        if r.status_code == 404:
            print(f"[{i}/{len(products)}] {title} — 404 (stale ID)")
            continue
        if r.status_code != 200:
            print(f"[{i}/{len(products)}] {title} — GET error {r.status_code}")
            continue

        variants = r.json().get("variants", [])
        to_update = []
        already_ok_sizes = []

        for v in variants:
            size   = (v.get("option2") or "").strip()
            fabric = (v.get("option3") or "").lower()

            if "comfort" not in fabric:
                continue
            if size not in CC_PRICES:
                continue

            target = CC_PRICES[size]
            cur_price = (v.get("price") or "").strip()
            cur_cat   = (v.get("compare_at_price") or "").strip()

            if cur_price == target["price"] and cur_cat == target["compare_at_price"]:
                already_ok_sizes.append(size)
                continue

            to_update.append({
                "vid":             v["id"],
                "size":            size,
                "old_price":       cur_price,
                "old_compare_at":  cur_cat,
                "new_price":       target["price"],
                "new_compare_at":  target["compare_at_price"],
            })

        if not to_update and not already_ok_sizes:
            total_no_variant += 1
            continue

        prefix = f"[{i}/{len(products)}] {title}"
        if already_ok_sizes and not to_update:
            print(f"{prefix} — already correct ({', '.join(set(already_ok_sizes))} CC)")
            total_already_ok += len(already_ok_sizes)
            continue

        print(prefix)
        for c in to_update:
            print(f"  {c['size']} CC: £{c['old_price']} → £{c['new_price']}  "
                  f"(compare_at £{c['old_compare_at']} → £{c['new_compare_at']})")

        if args.dry:
            total_changed += len(to_update)
            continue

        for c in to_update:
            r2 = s_put(
                f"/variants/{c['vid']}.json",
                {"variant": {
                    "id":               c["vid"],
                    "price":            c["new_price"],
                    "compare_at_price": c["new_compare_at"],
                }}
            )
            if r2.status_code in (200, 201):
                total_changed += 1
            else:
                print(f"  ! {c['size']} vid={c['vid']}: {r2.status_code} {r2.text[:100]}")
            time.sleep(0.35)

        time.sleep(0.5)

    print(f"\n{'=' * 60}")
    if args.dry:
        print(f"DRY RUN complete — would update {total_changed} variants")
    else:
        print(f"Updated {total_changed} variants")
    print(f"Already correct: {total_already_ok}  |  No 2XL/3XL CC: {total_no_variant}")


if __name__ == "__main__":
    main()
