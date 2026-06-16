import sys, os
sys.stdout.reconfigure(encoding="utf-8")
import openpyxl
from collections import Counter

path = os.path.join(os.path.dirname(__file__), "..", "scraper", "matcha_tees_catalogue.xlsx")
wb = openpyxl.load_workbook(path, read_only=True)
ws = wb.active
rows = list(ws.iter_rows(values_only=True))
print("HEADERS:", [str(h) for h in rows[0]])
print("TOTAL ROWS:", len(rows) - 1)

prices = []
included = 0
all_prices = []
for r in rows[1:]:
    inc = str(r[0]).strip().lower() if r[0] is not None else ""
    if r[2] is not None:
        all_prices.append(r[2])
    if inc in ("true", "1", "yes"):
        included += 1
        if r[2] is not None:
            prices.append(r[2])

print("INCLUDED rows:", included)
print("INCLUDED unique prices:", dict(Counter(prices)))
print("ALL rows unique prices:", dict(Counter(all_prices)))
