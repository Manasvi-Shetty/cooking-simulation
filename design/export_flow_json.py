"""Exports carbonara_simulation_flow.xlsx to web/flow.json, the data the simulation runs on.

Run after editing the workbook (or after build_flow_sheet.py):  python export_flow_json.py
"""
import json
from pathlib import Path
from openpyxl import load_workbook

HERE = Path(__file__).parent
wb = load_workbook(HERE / "carbonara_simulation_flow.xlsx")


def rows(name, keys):
    ws = wb[name]
    it = ws.iter_rows(values_only=True)
    head = next(it)
    idx = {h: i for i, h in enumerate(head) if h}
    out = []
    for r in it:
        if not any(v not in (None, "") for v in r):
            break
        out.append({k: ("" if r[idx[h]] is None else r[idx[h]]) for k, h in keys.items()})
    return out


substeps = rows("Flow", {
    "step": "Step", "stepTitle": "Step title", "id": "Substep ID", "title": "Substep title", "type": "Type",
    "required": "Required?", "left": "Left panel: instruction / question", "right": "Right panel shows",
    "tip": "Chef tip at start (ID)", "camera": "Camera view", "passRule": "Pass rule",
    "incomplete": "Feedback if incomplete (multi-select)", "maxAttempts": "Max attempts", "next": "On pass →",
    "learning": "Learning point (science)", "sceneState": "Scene state on entry", "notes": "Notes",
    "multiWrong": "Feedback if several incorrect (multi-select)", "mixedMissing": "Added if also incomplete (multi-select)"})
options = rows("MCQ Options", {
    "id": "Option ID", "sub": "Substep ID", "label": "Option label (right panel)", "item": "Item ID",
    "correctness": "Correctness", "outcome": "Outcome", "feedback": "Chef feedback (on select)",
    "branch": "Branch to", "score": "Score Δ", "effect": "State effect"})
actions = rows("Procedure Actions", {
    "id": "Action ID", "sub": "Substep ID", "order": "Order", "interaction": "Interaction",
    "source": "Source element / item", "srcLoc": "Source location", "target": "Target element",
    "param": "Parameter / value", "correctness": "Correctness", "outcome": "Outcome",
    "okFb": "Chef feedback (done right)", "badFb": "Chef feedback (wrong / out of order)",
    "branch": "Branch to", "score": "Score Δ", "effect": "State effect", "task": "Task instruction (left panel)"})
tips = rows("Chef Tips", {"id": "Tip ID", "sub": "Substep ID", "title": "Modal title", "text": "Tip text", "button": "Button label"})
items = rows("Scene & Items", {"id": "Element / item ID", "name": "Name", "location": "Location",
                               "description": "Visual description", "interactions": "Interactions"})
outcomes = rows("Outcomes", {"id": "Ending ID", "trigger": "Trigger", "title": "Result title",
                             "reaction": "Customer reaction", "nonna": "Nonna Pina", "notes": "Screen notes"})
thresholds = {str(r[0]): r[1] for r in wb["Outcomes"].iter_rows(min_row=2, values_only=True)
              if r[0] and isinstance(r[1], (int, float))}
order = {str(r[0]): str(r[1]) for r in wb["Order"].iter_rows(min_row=3, values_only=True) if r[0] and r[1]}

for a in actions:
    a["order"] = str(a["order"])
for coll in (options, actions):
    for r in coll:
        r["score"] = int(r["score"] or 0)
for s in substeps:
    s["maxAttempts"] = int(s["maxAttempts"] or 1)

data = {"order": order, "substeps": substeps, "options": options, "actions": actions,
        "tips": {t["id"]: t for t in tips}, "items": {i["id"]: i for i in items},
        "outcomes": outcomes, "thresholds": thresholds}
out = HERE.parent / "web" / "flow.json"
out.write_text(json.dumps(data, ensure_ascii=True, indent=1), encoding="utf-8")
print("wrote", out.name, {k: len(v) for k, v in data.items()})
