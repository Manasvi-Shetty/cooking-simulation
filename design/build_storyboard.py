"""Build the storyboard workbook (design/carbonara_storyboard.xlsx) from web/flow.json.

One sheet. Each step gets a heading row, then one row per learner task, numbered within the
step (2.1, 2.2, ...): a question counts as one task, a hands-on substep as one task per action.
Columns: task number, instruction, expected correct action, correct feedback, incorrect
feedback, clickable hotspots in the kitchen, items in the panel.
  python build_storyboard.py
"""
import json, os, re
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

HERE = os.path.dirname(os.path.abspath(__file__))
F = json.load(open(os.path.join(HERE, "..", "web", "flow.json"), encoding="utf-8"))
OUT = os.path.join(HERE, "carbonara_storyboard.xlsx")

SUBS = {s["id"]: s for s in F["substeps"]}
ITEMS = F["items"]
name = lambda i: ITEMS.get(i, {}).get("name", i) if i else ""
# Item cards in the panel use the Step 1 option label (or the name without its quantity).
LABEL = {}
for o in F["options"]:
    if o["item"]:
        LABEL.setdefault(o["item"], o["label"])        # first use (Step 1), as the page does
card = lambda i: LABEL.get(i) or re.sub(r",\s*\d.*$", "", name(i))

# Spots the kitchen draws a clickable pin for (props.js _anchors). Items from the sheet that
# are in the kitchen are clicked there; everything else is a card in the items panel.
ANCHORS = {"E-BOARD", "I-TOFU", "E-CUT-GUIDES", "E-SINK", "E-TAP", "E-BURNER-BACK", "E-KNOB-BACK", "E-KNOB-FRONT",
           "E-PAN-OIL", "T-SKILLET", "T-POT", "T-BOWL", "E-COUNTER", "E-WHITES-CUP", "E-PLATE", "T-MUG", "E-BOWLS",
           "E-BELL", "T-SLOTTED", "T-TONGS"}
ON_COUNTER = {"I-TOFU", "T-POT", "T-BOWL", "T-MUG", "T-SKILLET"}      # have a model on the counter after step 1
LIVE = "S7.4"


def in_kitchen(src, acts):
    if src not in ANCHORS:
        return False
    return src.startswith("E-") or src in ON_COUNTER or any(a["source"] == src and a["srcLoc"] == "Scene" for a in acts)


def bullets(lines):
    return "\n".join(f"• {l}" for l in lines if l)


def where(src, acts):
    return "in the kitchen" if in_kitchen(src, acts) else "from the items panel"


def action_steps(a, acts):
    tgt, p = name(a["target"]), a["param"]
    src = name(a["source"]) if in_kitchen(a["source"], acts) else card(a["source"])
    first = f"Select {src} {where(a['source'], acts)}"
    k = a["interaction"]
    targeted = tgt and a["target"] != a["source"] and a["target"] in ANCHORS
    if k in ("Drag", "Click") and targeted:
        return [first, f"Select {tgt} in the kitchen"]
    if k == "Hold":
        return [first, f"Press and hold “{p}”"]
    if k == "Repeat click":
        return [first, f"Tap “{p}” repeatedly until the bar fills"]
    if k == "Timer":
        return [first, f"Choose “{p}”", "The timer fast-forwards the wait"]
    if k == "Slider / knob":
        return [first, f"Choose “{p}”"]
    return [first, f"Choose “{p}”"]


rows = []          # (kind, values)
step_no, step_title, task_no = 0, None, 0
sid = F["substeps"][0]["id"]
while sid and sid != "END":
    s = SUBS[sid]
    if s["step"] != step_no:
        step_no, task_no = s["step"], 0
        rows.append(("step", [f"Step {step_no}: {s['stepTitle']}"]))
    kind = s["type"]
    if kind.startswith("MCQ"):
        opts = [o for o in F["options"] if o["sub"] == sid]
        right = [o for o in opts if o["correctness"] != "Incorrect"]
        wrong = [o for o in opts if o["correctness"] == "Incorrect"]
        multi = kind == "MCQ - Multi select"
        task_no += 1
        if multi:
            expect = [f"Select “{o['label']}”" for o in right] + ["Click Check"]
            ok = ["All there. Nicely done."] + [f"{o['label']}: {o['feedback']}" for o in right if o["correctness"] == "Acceptable"]
            bad = [f"{o['label']}: {o['feedback']}" for o in wrong] + [f"If something is missing: {s['incomplete'] or 'Something is missing.'}"]
        else:
            best = [o for o in right if o["correctness"] == "Correct"] or right
            expect = [f"Select “{o['label']}”" for o in best[:1]] + ["Click Continue (enabled once the answer is right)"]
            ok = [o["feedback"] for o in best[:1]] + [f"Also accepted, “{o['label']}”: {o['feedback']}" for o in right if o not in best[:1]]
            bad = [f"{o['label']}: {o['feedback']}" for o in wrong]
        rows.append(("task", [f"{step_no}.{task_no}", f"{s['title']}\n{s['left']}", bullets(expect), bullets(ok), bullets(bad),
                              "None", bullets(o["label"] for o in opts)]))
    else:
        acts = [a for a in F["actions"] if a["sub"] == sid]
        req = [a for a in acts if a["order"].isdigit()]
        req.sort(key=lambda a: int(a["order"]))
        extra = [a for a in acts if not a["order"].isdigit()]
        # Where each wrong/optional move shows up: the first task using the same item, else the last task.
        home = {}
        for a in extra:
            match = next((r for r in req if r["source"] == a["source"]), req[-1])
            home.setdefault(match["id"], []).append(a)
        knife = sid == "S2.3"       # knife: tick all three cuts, then Check (one task)
        groups = [req] if knife else [[a] for a in req]
        done = set()
        for g in groups:
            a = g[0]
            task_no += 1
            avail = [x for x in acts if x["id"] not in done and (x["order"].isdigit() or x["order"] in ("-", "opt"))]
            kitchen = sorted({name(x["source"]) for x in avail if in_kitchen(x["source"], acts)})
            targets = sorted({name(x["target"]) for x in g if x["interaction"] in ("Drag", "Click") and x["target"] in ANCHORS and x["target"] != x["source"]})
            panel = sorted({card(x["source"]) for x in avail if not in_kitchen(x["source"], acts)})
            if knife:
                cuts = [x for x in acts if x["source"] == "T-KNIFE"]
                expect = [f"Select {card('T-KNIFE')} from the items panel"] + [f"Tick “{x['param']}”" for x in g] + ["Click Check (the cuts animate in order)"]
                ok = [x["okFb"] for x in g if x["okFb"]]
                instr = a["task"]
                panel_note = panel + [f"After selecting the knife: {', '.join(x['param'] for x in cuts)}"]
            elif sid == LIVE and a["order"] != "1":
                expect = ["Use the toss-speed buttons and the heat control in the panel",
                          "Watch the thermometer: keep the sauce between 62 and 70 °C",
                          "Click “Plate it” when the sauce is glossy and coats the strands"] if a["order"] == "2" else \
                         ["Click “Plate it”"]
                ok = [a["okFb"]] if a["okFb"] else ["Nonna’s live commentary follows the thermometer (too cool / steady / close to scrambling / shiny)"]
                instr = a["task"]
                panel_note = ["Toss speed: Slow / Medium / Fast", "Heat on/off", "Splash of pasta water", "Plate it"]
                kitchen = []
            else:
                expect = action_steps(a, acts)
                ok = [a["okFb"]] if a["okFb"] else ["(No message; moves straight to the next task)"]
                instr = a["task"]
                panel_note = panel
            bad = ["If a cut is left out: Something’s missing. Which cuts get you all the way to 1 cm cubes?"] if knife else [f"Out of order: {x['badFb']}" for x in g if x["badFb"]]
            for x in sum((home.get(y["id"], []) for y in g), []):
                lab = "Optional" if x["order"] == "opt" else f"Wrong move ({x['outcome']})"
                bad.append(f"{lab}, “{x['param']}”: {x['badFb'] or x['okFb']}")
            hot = kitchen + ([] if knife else [f"{t} (spot to place it)" for t in targets if t not in kitchen])
            rows.append(("task", [f"{step_no}.{task_no}", instr, bullets(expect), bullets(ok), bullets(bad),
                                  bullets(hot) or "None", bullets(panel_note) or "None (panel hidden)"]))
            done.update(x["id"] for x in g)
    sid = s["next"]

# ---------- write ----------
wb = Workbook()
ws = wb.active
ws.title = "Storyboard"
HEAD = ["Task", "Instruction", "Expected correct action", "Correct feedback", "Incorrect feedback",
        "Clickable items on the workspace", "Items in the panel"]
WIDTHS = [8, 42, 46, 44, 60, 32, 34]
font = lambda **k: Font(**{"name": "Arial", "size": 10, **k})
thin = Side(style="thin", color="D9D4CC")
box = Border(left=thin, right=thin, top=thin, bottom=thin)
ws.append(HEAD)
for c, w in zip("ABCDEFG", WIDTHS):
    ws.column_dimensions[c].width = w
for cell in ws[1]:
    cell.font = font(bold=True, color="FFFFFF")
    cell.fill = PatternFill("solid", fgColor="3B2F26")
    cell.alignment = Alignment(vertical="center", wrap_text=True)
    cell.border = box
ws.row_dimensions[1].height = 22
ws.freeze_panes = "A2"
# One row per task. Lists sit in one cell, a bullet per line (line breaks + wrap); the row is
# made tall enough for the longest cell so every bullet shows.
def cell_lines(text, width):
    per = max(width - 2, 8)
    return sum(max(1, -(-len(line) // per)) for line in str(text).split("\n"))


for kind, vals in rows:
    ws.append(vals)
    r = ws.max_row
    if kind == "step":
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=7)
        c = ws.cell(r, 1)
        c.font = font(bold=True, size=11)
        c.fill = PatternFill("solid", fgColor="F3D9A6")
        c.alignment = Alignment(vertical="center")
        ws.row_dimensions[r].height = 20
        continue
    ws.row_dimensions[r].height = min(13.5 * max(cell_lines(v, w) for v, w in zip(vals, WIDTHS)) + 6, 409)
    for i, c in enumerate(ws[r]):
        c.font = font(bold=(i == 0))
        c.alignment = Alignment(vertical="top", wrap_text=True)
        c.border = box
ws.auto_filter.ref = f"A1:G{ws.max_row}"
wb.save(OUT)
print("wrote", OUT, sum(1 for k, _ in rows if k == "task"), "tasks in", sum(1 for k, _ in rows if k == "step"), "steps")
