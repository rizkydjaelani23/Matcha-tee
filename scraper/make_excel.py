"""Convert catalogue.csv into a formatted Excel file with checkbox-style INCLUDE column."""
import csv
import os
import sys

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.utils import get_column_letter

sys.stdout.reconfigure(encoding="utf-8")

BASE = os.path.dirname(os.path.abspath(__file__))
CATALOGUE_CSV = os.path.join(BASE, "catalogue.csv")
EXCEL_OUT = os.path.join(BASE, "matcha_tees_catalogue.xlsx")

# ── colours ──────────────────────────────────────────────────────────────────
GREEN_HEADER = "2D6A4F"   # dark green header
GREEN_TICK   = "D8F3DC"   # light green for included rows
GREY_NO      = "F0F0F0"   # grey for excluded
WHITE        = "FFFFFF"

def thin_border():
    s = Side(style="thin", color="CCCCCC")
    return Border(left=s, right=s, top=s, bottom=s)


def main():
    # read CSV
    with open(CATALOGUE_CSV, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Products"

    # ── instruction row (row 1) ───────────────────────────────────────────────
    ws.append(["✅ TICK = include on Shopify    ❌ UNTICK = skip    "
               "You can also edit TITLE, PRICE_GBP and DESCRIPTION directly in this sheet."])
    ws.merge_cells("A1:J1")
    ws["A1"].font = Font(bold=True, size=11, color="FFFFFF")
    ws["A1"].fill = PatternFill("solid", fgColor="1B4332")
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 24

    # ── column headers (row 2) ────────────────────────────────────────────────
    cols = ["INCLUDE", "TITLE", "PRICE_GBP", "DESCRIPTION",
            "SIZES", "COLORS", "TAGS", "IMAGE1_URL", "IMAGE2_URL", "IMAGE3_URL"]
    ws.append(cols)
    header_row = ws[2]
    for cell in header_row:
        cell.font = Font(bold=True, color="FFFFFF", size=10)
        cell.fill = PatternFill("solid", fgColor=GREEN_HEADER)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=False)
        cell.border = thin_border()
    ws.row_dimensions[2].height = 22

    # ── data validation: dropdown ✓ / ✗ in INCLUDE column ────────────────────
    dv = DataValidation(
        type="list",
        formula1='"✓,✗"',
        allow_blank=False,
        showDropDown=False,   # False = SHOW the dropdown arrow
        showErrorMessage=True,
        errorTitle="Invalid",
        error="Please choose ✓ (include) or ✗ (skip)",
    )
    ws.add_data_validation(dv)

    # ── data rows ─────────────────────────────────────────────────────────────
    for i, row in enumerate(rows, start=3):   # data starts on row 3
        include = "✓"  # default all ticked

        ws.append([
            include,
            row.get("TITLE", ""),
            row.get("PRICE_GBP", ""),
            row.get("DESCRIPTION", "")[:300],
            row.get("SIZES", ""),
            row.get("COLORS", ""),
            row.get("TAGS", ""),
            row.get("IMAGE1_URL", ""),
            row.get("IMAGE2_URL", ""),
            row.get("IMAGE3_URL", ""),
        ])

        ws_row = ws[i]
        bg = GREEN_TICK  # all start green (included)

        for j, cell in enumerate(ws_row):
            cell.border = thin_border()
            cell.alignment = Alignment(vertical="center", wrap_text=(j == 3))
            cell.fill = PatternFill("solid", fgColor=bg)

        # INCLUDE cell styling
        ws_row[0].alignment = Alignment(horizontal="center", vertical="center",
                                        wrap_text=False)
        ws_row[0].font = Font(bold=True, size=12)

        # attach validation to INCLUDE cell
        dv.add(ws_row[0])

        ws.row_dimensions[i].height = 40

    # ── column widths ─────────────────────────────────────────────────────────
    widths = {
        "A": 10,   # INCLUDE
        "B": 45,   # TITLE
        "C": 12,   # PRICE
        "D": 60,   # DESCRIPTION
        "E": 30,   # SIZES
        "F": 35,   # COLORS
        "G": 40,   # TAGS
        "H": 20,   # IMAGE1
        "I": 20,   # IMAGE2
        "J": 20,   # IMAGE3
    }
    for col, width in widths.items():
        ws.column_dimensions[col].width = width

    # ── freeze header rows ────────────────────────────────────────────────────
    ws.freeze_panes = "A3"   # freeze instruction + header rows

    # ── auto-filter on header row ─────────────────────────────────────────────
    ws.auto_filter.ref = f"A2:{get_column_letter(len(cols))}2"

    wb.save(EXCEL_OUT)
    print(f"Excel file saved: {EXCEL_OUT}")
    print(f"{len(rows)} products, {sum(1 for r in rows if r.get('INCLUDE','YES')=='YES')} ticked")


if __name__ == "__main__":
    main()
