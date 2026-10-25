"""Restyle storyboard rows (steps 2-8, plus the new multi-select cases in step 1) to match the
conventions the user set in step 1 of the Google Sheet. Writes renders/restyle_reqs.json: Sheets
updateCells requests for columns C-I, with **bold** markup turned into textFormatRuns.
"""
import json, re, os

HERE = os.path.dirname(os.path.abspath(__file__))
ROWS = json.load(open(os.path.join(HERE, "..", "renders", "sheet_values.json"), encoding="utf-8"))

# Item names in Title Case, as the user wrote them in step 1.
NAMES = {
    "Extra-firm tofu, 280 g": "Extra-firm Tofu", "Extra-firm tofu": "Extra-firm Tofu", "2 clean kitchen towels": "2 Kitchen Towels",
    "Cutting board": "Cutting Board", "Heavy pan (weight)": "Heavy Pan (Weight)", "Chef's knife and board": "Chef's Knife and Board",
    "Large pot with lid": "Large Pot with Lid", "Tap": "Tap", "Sink": "Sink", "Back burner": "Back Burner",
    "Back burner knob": "Back Burner Knob", "Front burner knob": "Front Burner Knob", "Olive oil": "Olive Oil",
    "Cast-iron skillet": "Cast-iron Skillet", "Oil in the pan": "Oil in the Pan", "Kitchen timer": "Kitchen Timer",
    "Tongs": "Tongs", "Smoked paprika": "Smoked Paprika", "Slotted spoon": "Slotted Spoon", "Resting plate": "Resting Plate",
    "Mixing bowl and whisk": "Mixing Bowl and Whisk", "Counter": "Counter", "Eggs": "Eggs", "Pecorino Romano": "Pecorino Romano",
    "Black peppercorns": "Black Peppercorns", "Coarse salt": "Coarse Salt", "Spaghetti (dried, bronze-cut)": "Spaghetti (dried, bronze-cut)",
    "Ladle and mug": "Ladle and Mug", "Serving bowls (2)": "Serving Bowls (2)", "Service bell": "Service Bell",
    "Cup for whites": "Cup for Whites", "Plate it button": "Plate It Button", "Sauce thermometer": "Sauce Thermometer",
    "Toss speed control": "Toss Speed Control",
    "Freshly cracked black pepper": "Freshly Cracked Black Pepper", "A dusting of pecorino": "A Dusting of Pecorino",
    "Extra crispy tofu on top": "Extra Crispy Tofu on Top", "Chopped parsley": "Chopped Parsley", "A drizzle of cream": "A Drizzle of Cream",
    "Chilli flakes": "Chilli Flakes",
}
T = lambda s: NAMES.get(s, s)

# One short sentence of what the screen does (the user's style in step 1).
SYS = {
    "2.1": "The pack lifts away and the packing water drains off the board, along with feedback popup.",
    "2.2": "A towel slides onto the board and the tofu settles on top of it.",
    "2.3": "The second towel is laid over the tofu.",
    "2.4": "The heavy pan settles on the towels and the tofu starts pressing, along with feedback popup.",
    "2.5": "Feedback popup appears",
    "2.6": "The cuts animate on the tofu in order and the block separates into cubes, along with feedback popup.",
    "2.7": "Feedback popup appears",
    "3.1": "The pot moves into the sink under the tap.",
    "3.2": "Water streams from the tap and fills the pot to the line, along with feedback popup.",
    "3.3": "The pot lifts out of the sink and onto the back burner.",
    "3.4": "The knob turns to High and the cooking zone glows.",
    "3.5": "The lid goes on and the water comes to a rolling boil, along with feedback popup.",
    "4.1": "Feedback popup appears",
    "4.2": "The knob turns to Medium and the burner comes on under the skillet.",
    "4.3": "A film of oil spreads over the skillet.",
    "4.4": "A fast-forward timer runs to 1:00 and the oil starts to shimmer, along with feedback popup.",
    "4.5": "The tofu cubes slide into the skillet in a single layer and sizzle, along with feedback popup.",
    "4.6": "A fast-forward timer runs to 3:00 and the undersides of the cubes turn golden.",
    "4.7": "The cubes flip to show their browned sides, along with feedback popup.",
    "4.8": "A fast-forward timer runs to 3:30 and the cubes turn golden and smoky, along with feedback popup.",
    "4.9": "The knob turns to Off and the burner goes out.",
    "4.10": "The cubes lift out of the skillet; the oil stays in the pan.",
    "4.11": "The cubes move onto the resting plate, along with feedback popup.",
    "5.1": "Feedback popup appears",
    "5.2": "The mixing bowl is set on the counter.",
    "5.3": "Two whole eggs drop into the bowl.",
    "5.4": "Three yolks drop into the bowl and the whites go into the cup, along with feedback popup.",
    "5.5": "Feedback popup appears",
    "5.6": "Grated pecorino piles up in the bowl.",
    "5.7": "Cracked pepper speckles the bowl, along with feedback popup.",
    "5.8": "The mixture turns into a thick, smooth paste, along with feedback popup.",
    "6.1": "Feedback popup appears",
    "6.2": "The salt goes into the boiling water.",
    "6.3": "The spaghetti goes into the pot and softens, along with feedback popup.",
    "6.4": "The strands are stirred apart in the pot, along with feedback popup.",
    "6.5": "Feedback popup appears",
    "7.1": "The mug fills with pasta water, along with feedback popup.",
    "7.2": "The knob turns to the lowest setting and the flame drops.",
    "7.3": "The pasta moves from the pot into the skillet, along with feedback popup.",
    "7.4": "The pasta is tossed and coated in oil, along with feedback popup.",
    "7.5": "The pasta water pours from the mug into the egg bowl.",
    "7.6": "The paste loosens into a smooth, pourable sauce, along with feedback popup.",
    "7.7": "The sauce pours like cream, along with feedback popup.",
    "7.8": "Feedback popup appears",
    "7.9": "The egg mixture pours over the pasta, the thermometer appears and the panel shows the toss controls, along with feedback popup.",
    "7.10": "The thermometer and the sauce update live while Nonna comments on the temperature.",
    "7.11": "The sauce is judged and the result appears in the feedback popup.",
    "8.1": "Correctly selected items appear on the workspace along with feedback popup.",
    "8.2": "The crispy tofu folds back into the pasta.",
    "8.3": "Two pasta nests are twirled into the serving bowls, along with feedback popup.",
    "8.4": "Pepper speckles each bowl.",
    "8.5": "Pecorino and the reserved tofu go on top of each bowl.",
    "8.6": "The bell rings, along with feedback popup; the final screen shows the customer's reaction and the score.",
}

# Popups for a Check with more than one incorrect pick (multi-select branching).
MULTI_WRONG = {
    "1.2": ("More than one incorrect tool",
            "A few of these won't help today: {incorrect tools selected}. Walk through the dish: press, cut, boil, fry, grate, whisk, move the pasta, save the water. Which tools does each stage really need?"),
    "1.3": ("More than one incorrect ingredient",
            "Some of these don't belong in this carbonara: {incorrect ingredients selected}. Read the order again: no meat, no cream, and keep it Roman."),
    "8.1": ("More than one incorrect topping",
            "{incorrect toppings selected} would cover up the flavours this dish is built on. A Roman carbonara is finished simply, with things already on your counter."),
}
MIXED = {   # incorrect picks and missing ones in the same Check
    "1.2": ("Incorrect and missing tools", "{incorrect tool feedback} And something's still missing. Think through each stage again."),
    "1.3": ("Incorrect and missing ingredients", "{incorrect ingredient feedback} And you're short of something. Check the order again."),
    "2.6": ("Incorrect and missing cuts", "Too big. 3 cm chunks crisp outside but stay soft inside. And you'll need more cuts to get to even 1 cm cubes."),
    "8.1": ("Incorrect and missing toppings", "{incorrect topping feedback} And the classic finish is still missing something."),
}


def bullets(entries):
    """[(label, text)] -> '• **label**: \\ntext' blocks separated by a blank line."""
    return "\n\n".join(f"• **{l}**: \n{t}" for l, t in entries)


def expected(cell, multi):
    if multi:   # "Select the following:" then only the things clicked; items in Title Case, cut options as written
        items = []
        for line in cell.split("\n"):
            m = re.match(r"^• Select (?:“(.+)”|(.+?) from the items panel)$", line)
            if m: items.append(f"• **{T(m.group(1) or m.group(2))}**"); continue
            m = re.match(r"^• Tick “(.+)”$", line)
            if m: items.append(f"• **{m.group(1)}**")
        return "Select the following:\n" + "\n".join(items)
    out = []
    for line in cell.split("\n"):
        if line.startswith("• Click Continue") or line.startswith("• The timer fast-forwards"):
            continue
        m = re.match(r"^• Select (?!“)(.+?)( in the kitchen| from the items panel)$", line)
        if m:
            out.append(f"• Select **{T(m.group(1))}**{m.group(2)}"); continue
        out.append(re.sub(r"“([^”]+)”", r"**\1**", line))
    return "\n".join(out)


def correct(cell):
    lines = [l[2:] if l.startswith("• ") else l for l in cell.split("\n") if l]
    if not lines or lines == ["(No message; moves straight to the next task)"]:
        return "None"
    main, extra = [], []
    for l in lines:
        m = re.match(r"^Also accepted, “(.+)”: (.+)$", l)
        if m:
            extra.append(f"**{m.group(1)}** (also accepted): \n{m.group(2)}")
        elif re.match(r"^(Soy sauce|Smoked paprika|Extra crispy tofu on top): ", l):
            continue
        else:
            main.append(l)
    return "\n\n".join([" ".join(main)] + extra)


def incorrect(cell, tid):
    entries = []
    for l in [x for x in cell.split("\n") if x]:
        l = l[2:] if l.startswith("• ") else l
        m = re.match(r"^Out of order: (.+)$", l)
        if m: entries.append(("Out of order", m.group(1))); continue
        m = re.match(r"^Wrong move \((\w+)\), “(.+)”: (.+)$", l)
        if m: entries.append((f"{m.group(2)} ({m.group(1)})", m.group(3))); continue
        m = re.match(r"^Optional, “(.+)”: (.+)$", l)
        if m: entries.append((f"{m.group(1)} (optional, no penalty)", m.group(2))); continue
        m = re.match(r"^(.+?): (.+)$", l)
        if m: entries.append((m.group(1), m.group(2))); continue
        entries.append(("Note", l))
    if tid in MULTI_WRONG: entries.append(MULTI_WRONG[tid])
    if tid in MIXED: entries.append(MIXED[tid])
    return bullets(entries) if entries else "None"


def listcell(cell, title_all):
    out = []
    for l in cell.split("\n"):
        m = re.match(r"^• (.+?)( \(spot to place it\))?$", l)
        if m and (title_all or m.group(1) in NAMES):
            out.append(f"• {T(m.group(1))}{m.group(2) or ''}")
        else:
            out.append(l)
    return "\n".join(out)


def rich(text):
    """'**bold**' markup -> (plain text, textFormatRuns)."""
    plain, runs, pos, bold = "", [], 0, False
    for part in re.split(r"(\*\*)", text):
        if part == "**":
            bold = not bold; continue
        if part:
            runs.append({"startIndex": len(plain), "format": {"bold": bold}})
            plain += part
    cell = {"userEnteredValue": {"stringValue": plain}}
    if any(r["format"]["bold"] for r in runs):
        merged = []
        for r in runs:
            if merged and merged[-1]["format"] == r["format"]: continue
            merged.append(r)
        cell["textFormatRuns"] = merged
    return cell


TYPES = {}
reqs = []
for i, r in enumerate(ROWS):
    if i < 2 or not r[1]: continue
    tid = r[0].lstrip("'")
    step = int(tid.split(".")[0])
    multi = "Click Check" in r[2]
    single = "Click Continue" in r[2]
    ttype = "MCQ: Multi-Select" if multi else "MCQ: Single-Select" if single else "Procedure"
    if step == 1:
        if tid in MULTI_WRONG:   # step 1 keeps the user's text; just add the new cases to Incorrect feedback
            reqs.append(("F", i, tid))
        continue
    cells = [
        expected(r[2], multi),
        SYS[tid],
        "Neat little cubes, just like guanciale." if tid == "2.6" else correct(r[3]),
        incorrect(r[4], tid),
        listcell(r[5], False),
        listcell(r[6], multi),
        ttype,
    ]
    reqs.append(("C-I", i, [rich(c) for c in cells]))

out = []
for kind, i, payload in reqs:
    if kind == "C-I":
        out.append({"updateCells": {"start": {"sheetId": 0, "rowIndex": i, "columnIndex": 2},
                                    "rows": [{"values": payload}], "fields": "userEnteredValue,textFormatRuns"}})
json.dump(out, open(os.path.join(HERE, "..", "renders", "restyle_reqs.json"), "w", encoding="utf-8"), ensure_ascii=False)
step1_extra = {tid: bullets([MULTI_WRONG[tid], MIXED[tid]]) for tid in ("1.2", "1.3")}
json.dump(step1_extra, open(os.path.join(HERE, "..", "renders", "step1_extra.json"), "w", encoding="utf-8"), ensure_ascii=False)
print(len(out), "rows")
