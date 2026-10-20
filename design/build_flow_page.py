"""Renders carbonara_simulation_flow.xlsx as a tabbed HTML page of plain tables (flow_tables.html).

Formula columns (the sheet's own checks) are left out; everything else is copied as-is.
"""
import json
from pathlib import Path
from openpyxl import load_workbook

HERE = Path(__file__).parent
wb = load_workbook(HERE / "carbonara_simulation_flow.xlsx")

TABS = ["Order", "Flow", "MCQ Options", "Procedure Actions", "Chef Tips", "Scene & Items", "Outcomes"]
SKIP_HEADERS = {"Options / actions defined", "Tip check", "Row check", "Times used"}


def table(ws):
    rows = list(ws.iter_rows(values_only=True))
    head = list(rows[0])
    keep = [i for i, h in enumerate(head) if h and h not in SKIP_HEADERS]
    body = []
    for r in rows[1:]:
        if not any(v not in (None, "") for v in r):
            break                                    # stop at the first blank row (notes below tables)
        body.append(["" if r[i] is None else str(r[i]) for i in keep])
    return {"head": [head[i] for i in keep], "rows": body}


data = {}
order = []
for r in wb["Order"].iter_rows(min_row=3, values_only=True):
    if r[0]:
        order.append([r[0], "" if r[1] is None else str(r[1])])
data["Order"] = order
for name in TABS[1:]:
    data[name] = table(wb[name])
ws = wb["Outcomes"]
data["Thresholds"] = [[str(r[0]), str(r[1])] for r in ws.iter_rows(min_row=2, values_only=True)
                      if r[0] and isinstance(r[1], (int, float))]
readme = []
for r in wb["README"].iter_rows(min_row=4, values_only=True):
    a, b = r[0], r[1]
    if a and isinstance(b, str) and b.startswith("="):
        continue                                     # live summary formulas: not rendered
    if a or b:
        readme.append(["" if a is None else str(a), "" if b is None else str(b)])
data["Guide"] = readme

template = (HERE / "flow_tables_template.html").read_text(encoding="utf-8")
out = HERE / "flow_tables.html"
out.write_text(template.replace("/*DATA*/null", json.dumps(data, ensure_ascii=False)), encoding="utf-8")
print("wrote", out, out.stat().st_size, "bytes;", {k: len(v["rows"]) if isinstance(v, dict) else len(v) for k, v in data.items()})
