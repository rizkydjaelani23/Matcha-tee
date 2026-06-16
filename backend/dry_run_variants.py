import sys; sys.stdout.reconfigure(encoding="utf-8")
from update_variants import load_catalogue

cat = load_catalogue()
print(f"Products in catalogue: {len(cat)}\n")

for title, info in list(cat.items())[:5]:
    sz = info["sizes"]
    cl = info["colors"]
    total = len(sz) * max(len(cl), 1)
    print(f"{title[:55]}")
    print(f"  Sizes  ({len(sz)}): {sz}")
    print(f"  Colors ({len(cl)}): {cl}")
    print(f"  Variants: {total}")
    print()

over = [(t, i) for t, i in cat.items() if len(i["sizes"]) * max(len(i["colors"]), 1) > 99]
print(f"Products over 99 variants (before cap): {len(over)}")
for t, i in over:
    print(f"  {t}: {len(i['sizes'])} sizes x {len(i['colors'])} colors")
