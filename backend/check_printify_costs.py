"""Show Printify variant costs vs current Shopify retail prices."""
import json, os, httpx
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

TOKEN   = os.environ["PRINTIFY_TOKEN"]
SHOP_ID = 27883571
PH      = {"Authorization": f"Bearer {TOKEN}"}
PAPI    = "https://api.printify.com/v1"

cp    = json.load(open("full_checkpoint.json", encoding="utf-8"))
entry = next(v for v in cp.values() if v.get("status") == "done" and v.get("new_shopify_id"))
title = entry["title"]

for pkey in ["UK_CC", "UK_GD"]:
    ppid = entry["printify_ids"].get(pkey)
    if not ppid: continue
    r = httpx.get(f"{PAPI}/shops/{SHOP_ID}/products/{ppid}.json", headers=PH, timeout=30)
    p = r.json()
    variants = p.get("variants", [])

    # Group by size: pick one representative variant per size
    size_costs = {}
    for v in variants:
        if not v.get("is_enabled"): continue
        title_parts = v.get("title", "").split(" / ")
        size = title_parts[1] if len(title_parts) > 1 else "?"
        cost_pence = v.get("cost", 0)   # in pence (£ × 100)
        if size not in size_costs:
            size_costs[size] = cost_pence

    print(f"\n{pkey} — {entry['title'][:50]}")
    print(f"{'Size':<8} {'Cost (p)':<12} {'Cost GBP':>10}")
    print("-" * 32)
    size_order = ["S","M","L","XL","2XL","3XL","4XL","5XL"]
    for size in size_order:
        if size in size_costs:
            cost_p = size_costs[size]
            print(f"{size:<8} {cost_p:<12} £{cost_p/100:>8.2f}")
