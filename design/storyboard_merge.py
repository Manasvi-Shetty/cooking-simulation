"""Storyboard pass 2 (user's Step 2 pattern): merge consecutive hands-on tasks that share one outcome
into a single task, list every click in order, describe the screen per action (including the cursor
change when an item is picked), and give a feedback case for each way a learner can go wrong.
Writes renders/merge_reqs.json (Sheets batchUpdate requests) for steps 3-8 plus Step 2 touch-ups.
"""
import json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "renders", "merge_reqs.json")
PREV = json.load(open(os.path.join(HERE, "..", "renders", "restyle_reqs.json"), encoding="utf-8"))


def B(lines):          # bullet list
    return "\n".join(f"• {l}" for l in lines)


def F(cases):          # incorrect-feedback cases
    return "\n\n".join(f"• **{label}**: \n{text}" for label, text in cases)


def mcq(old_row):
    """An unchanged question row: reuse its C-I cells from the restyle pass."""
    for r in PREV:
        if r["updateCells"]["start"]["rowIndex"] == old_row:
            return r["updateCells"]["rows"][0]["values"]
    raise KeyError(old_row)


S, K, P = "in the kitchen", "from the items panel", "Procedure"
STEPS = [
    ("Step 3: Boil the Pasta Water", [
        ("Fill the pot with enough water for the pasta to move freely.",
         B([f"Select **Large Pot with Lid** {S}", f"Select **Sink** {S}", f"Select **Tap** {S}",
            "Press and hold **Fill to about 3 litres (fill line)**"]),
         B(["Cursor changes to the pot", "The pot moves into the sink under the tap",
            "While held, water streams from the tap and fills the pot to the line, along with feedback popup"]),
         "Plenty of water, so the pasta moves freely.",
         F([("Tap selected before the pot is in the sink", "Pot under the tap first."),
            ("Wrong spot for the pot", "The pot needs to go under the tap. Put it in the sink."),
            ("Released before the fill line", "Keep holding until the water reaches the line."),
            ("Fill only to 1 litre (Recoverable)", "Too little. The water would drop off the boil and the pasta would stick. Fill it to the line.")]),
         B(["Large Pot with Lid", "Sink (spot to place it)", "Tap", "Back Burner Knob"]), "None (panel hidden)", P),
        ("Bring the water to a fast boil.",
         B([f"Select **Large Pot with Lid** {S}", f"Select **Back Burner** {S}", f"Select **Back Burner Knob** {S}",
            "Choose **High**", f"Select **Large Pot with Lid** {S}", "Choose **Lid on**"]),
         B(["Cursor changes to the pot", "The pot lifts out of the sink and onto the back burner",
            "The knob turns to High and the cooking zone glows",
            "The lid goes on and the water comes to a rolling boil, along with feedback popup"]),
         "A lid brings it to the boil much faster.",
         F([("Pot moved to the stove before filling", "Fill it before it goes on the stove."),
            ("Wrong spot for the pot", "That's not where it boils. Put it on the back burner."),
            ("Burner turned on before the pot is on it", "Pot first, then the heat."),
            ("Low or Medium heat", "Full heat for the pasta water.")]),
         B(["Large Pot with Lid", "Back Burner (spot to place it)", "Back Burner Knob"]), "None (panel hidden)", P),
    ]),
    ("Step 4: Fry the Tofu Until Crisp", [
        ("Select the appropriate way to start the pan for crisp tofu.", mcq(20)),
        ("Heat the oil to frying temperature.",
         B([f"Select **Front Burner Knob** {S}", "Choose **Medium (target 170-200 °C)**", f"Select **Olive Oil** {K}",
            f"Select **Cast-iron Skillet** {S}", f"Select **Oil in the Pan** {S}", "Choose **Wait until the oil shimmers (about 1 min)**"]),
         B(["The knob turns to Medium and the burner comes on under the skillet", "Cursor changes to the olive oil",
            "A film of oil spreads over the skillet",
            "A fast-forward timer runs to 1:00 and the oil starts to shimmer, along with feedback popup"]),
         "See it ripple? That's hot enough.",
         F([("Oil added before the heat is on", "Heat the pan first."),
            ("Low heat", "Too gentle. The tofu would soak up oil instead of crisping. Medium is right."),
            ("High heat", "Too hot. The oil would smoke before the tofu goes in. Medium is right."),
            ("High for more than 4 min (Fatal)", "Smoke! The tofu and oil have burnt. Bitter, acrid and not servable."),
            ("Wrong spot for the oil", "The oil goes into the skillet."),
            ("Tofu added before the oil shimmers", "Wait for the shimmer, or the tofu will stick.")]),
         B(["Front Burner Knob", "Cast-iron Skillet (spot to place it)", "Oil in the Pan", "Extra-firm Tofu"]),
         B(["Olive Oil", "Kitchen Timer", "Smoked Paprika", "Tongs"]), P),
        ("Fry the tofu until crisp and golden on all sides.",
         B([f"Select **Extra-firm Tofu** {S}", f"Select **Cast-iron Skillet** {S}", f"Select **Kitchen Timer** {K}",
            "Choose **Leave undisturbed 3 min**", f"Select **Tongs** {K}", f"Select **Cast-iron Skillet** {S}",
            f"Select **Kitchen Timer** {K}", "Choose **Another 3-4 min, then add soy and paprika for the last 30 s**"]),
         B(["Cursor changes to the tofu", "The cubes slide into the skillet in a single layer and sizzle",
            "A fast-forward timer runs to 3:00 and the undersides turn golden", "Cursor changes to the tongs",
            "The cubes flip to show their browned sides",
            "A fast-forward timer runs to 3:30 and the cubes turn golden and smoky, along with feedback popup"]),
         "Crisp, golden and smoky.",
         F([("Wrong spot for the tofu", "The tofu goes into the hot skillet."),
            ("Toss in the first minute (Degraded)", "Too soon! The crust tore and stuck to the pan. Let it sit next time."),
            ("Timer set to 1 min", "Not yet. The crust needs about 3 minutes to form."),
            ("Timer set to 6 min", "Too long on one side. The cubes will scorch. 3 minutes is enough."),
            ("Paprika at the start of frying (Degraded)", "Paprika burns fast and turns bitter. Add it in the last 30 seconds.")]),
         B(["Extra-firm Tofu", "Cast-iron Skillet (spot to place it)", "Front Burner Knob"]),
         B(["Kitchen Timer", "Smoked Paprika", "Tongs"]), P),
        ("Take the tofu out while keeping the flavoured oil in the pan.",
         B([f"Select **Front Burner Knob** {S}", "Choose **Off**", f"Select **Slotted Spoon** {S}",
            f"Select **Cast-iron Skillet** {S}", f"Select **Slotted Spoon** {S}", f"Select **Resting Plate** {S}"]),
         B(["The knob turns to Off and the burner goes out", "Cursor changes to the slotted spoon",
            "The cubes lift out of the skillet; the oil stays in the pan",
            "The cubes move onto the resting plate, along with feedback popup"]),
         "Set aside. It goes back in at the very end.",
         F([("Tofu lifted out with the heat still on", "Heat off first."),
            ("Pour the oil away (Recoverable)", "That oil was flavour! Add 1 tbsp fresh oil to the pan, but the sauce will taste a little flatter."),
            ("Leave the tofu in the pan (Degraded)", "In the sauce it will soak up liquid and go soft. Crispy tofu was the request!"),
            ("Wrong spot for the tofu", "Put the tofu on the resting plate so it stays crisp.")]),
         B(["Front Burner Knob", "Slotted Spoon", "Cast-iron Skillet (spot to place it)", "Resting Plate (spot to place it)"]),
         "None (panel hidden)", P),
    ]),
    ("Step 5: Prepare the Egg and Cheese Mixture", [
        ("Select the appropriate eggs for a rich sauce for two.", mcq(32)),
        ("Add the eggs to the bowl for the sauce base.",
         B([f"Select **Mixing Bowl and Whisk** {S}", f"Select **Counter** {S}", f"Select **Eggs** {K}",
            "Tap **Crack 2 whole eggs into the bowl** repeatedly until the bar fills", f"Select **Eggs** {K}",
            "Tap **Separate: whites into the cup, yolk into the bowl** repeatedly until the bar fills"]),
         B(["Cursor changes to the bowl", "The mixing bowl is set on the counter", "Cursor changes to the eggs",
            "Each tap fills the bar; two whole eggs drop into the bowl",
            "Three yolks drop into the bowl and the whites go into the cup, along with feedback popup"]),
         "Lovely golden yolks.",
         F([("Eggs cracked before the bowl is out", "Get the bowl onto the counter first."),
            ("Yolks separated before the whole eggs", "Whole eggs first, then the extra yolks."),
            ("Whites added to the bowl", "The whites go into the cup. Only the yolks go in the bowl."),
            ("Shell fragment falls in (Recoverable)", "A bit of shell got in. Scoop it out with a larger piece of shell, it works like a magnet.")]),
         B(["Mixing Bowl and Whisk", "Counter (spot to place it)", "Cup for Whites"]), B(["Eggs"]), P),
        ("Select the appropriate grater side for cheese that melts smoothly.", mcq(36)),
        ("Combine the cheese and pepper with the eggs into a smooth paste.",
         B([f"Select **Pecorino Romano** {K}", "Press and hold **Grate 150 g on the chosen side**",
            f"Select **Black Peppercorns** {K}", "Tap **Crack about ½ tbsp pepper** repeatedly until the bar fills",
            f"Select **Mixing Bowl and Whisk** {S}", "Press and hold **Whisk until a thick, smooth paste**"]),
         B(["Cursor changes to the cheese", "While held, the bar fills and grated pecorino piles up in the bowl",
            "Cursor changes to the pepper mill", "Each tap fills the bar and cracked pepper speckles the bowl",
            "While held, the mixture turns into a thick, smooth paste, along with feedback popup"]),
         "Thick and smooth. It will loosen with pasta water later.",
         F([("Whisked before the cheese and pepper", "Add the cheese and pepper before whisking."),
            ("Released before 150 g", "Keep going. You need about 150 g for the sauce to coat the pasta."),
            ("Add salt to the eggs (Degraded)", "No salt here. Pecorino brings plenty.")]),
         B(["Mixing Bowl and Whisk"]), B(["Pecorino Romano", "Black Peppercorns", "Coarse Salt"]), P),
    ]),
    ("Step 6: Cook the Spaghetti", [
        ("Select the appropriate amount of salt for seasoning the pasta water.", mcq(41)),
        ("Cook the pasta in the salted water without it sticking.",
         B([f"Select **Coarse Salt** {K}", f"Select **Large Pot with Lid** {S}",
            f"Select **Spaghetti (dried, bronze-cut)** {K}", f"Select **Large Pot with Lid** {S}",
            f"Select **Tongs** {K}", "Tap **Stir during the first minute** repeatedly until the bar fills"]),
         B(["Cursor changes to the salt", "The salt goes into the boiling water", "Cursor changes to the spaghetti",
            "The spaghetti goes into the pot and softens", "Cursor changes to the tongs",
            "Each tap fills the bar and the strands are stirred apart, along with feedback popup"]),
         "No sticking.",
         F([("Pasta added before the salt", "Salt the water first."),
            ("Wrong spot", "That goes into the boiling pot."),
            ("Snap the spaghetti in half (Recoverable)", "Mamma mia! Long strands are how you twirl. Push them under gently as they soften."),
            ("Oil in the water (Recoverable)", "Oil just floats on top. Stirring is what stops sticking. And oily pasta won't hold the sauce.")]),
         B(["Large Pot with Lid (spot to place it)"]),
         B(["Coarse Salt", "Spaghetti (dried, bronze-cut)", "Olive Oil", "Tongs"]), P),
        ("Select the appropriate time to take the pasta out for finishing it in the pan.", mcq(45)),
    ]),
    ("Step 7: Combine the Pasta and Sauce", [
        ("Move the pasta into the pan, keeping some cooking water aside.",
         B([f"Select **Ladle and Mug** {S}", f"Select **Large Pot with Lid** {S}", f"Select **Front Burner Knob** {S}",
            "Choose **Lowest flame**", f"Select **Tongs** {S}", f"Select **Cast-iron Skillet** {S}", f"Select **Tongs** {S}",
            "Tap **Toss to coat in the oil** repeatedly until the bar fills"]),
         B(["Cursor changes to the ladle", "The mug fills with pasta water",
            "The knob turns to the lowest setting and the flame drops", "Cursor changes to the tongs",
            "The pasta moves from the pot into the skillet",
            "Each tap fills the bar and the pasta is tossed in the oil, along with feedback popup"]),
         "Every strand coated in that flavoured oil.",
         F([("Pasta moved before saving water", "Save the water before you move the pasta!"),
            ("Heat left on medium", "Lower the flame first, or the oil will spit when the wet pasta goes in."),
            ("Drain the pot into the sink (Recoverable)", "There goes the pasta water! If you saved a mug you're fine, otherwise the sauce has nothing to loosen it."),
            ("Wrong spot for the pasta", "The pasta goes into the skillet with the flavoured oil.")]),
         B(["Ladle and Mug", "Large Pot with Lid", "Front Burner Knob", "Tongs", "Cast-iron Skillet (spot to place it)"]),
         "None (panel hidden)", P),
        ("Temper the egg mixture so it pours like cream.",
         B([f"Select **Ladle and Mug** {S}", f"Select **Mixing Bowl and Whisk** {S}", f"Select **Mixing Bowl and Whisk** {S}",
            "Press and hold **Whisk hard while pouring**", f"Select **Mixing Bowl and Whisk** {S}", "Choose **Check: pours like cream**"]),
         B(["Cursor changes to the mug", "The pasta water pours slowly into the egg bowl",
            "While held, the paste loosens into a smooth, pourable sauce",
            "The sauce pours like cream, along with feedback popup"]),
         "Smooth and pourable. Ready for the pan.",
         F([("Dump all the hot water in at once without whisking (Degraded)", "Some egg cooked into strands. Strain them out if you can. The rest will still work."),
            ("Skip tempering, pour the cold paste straight into the pan (Degraded)", "Thick, cold paste hitting hot pasta cooks unevenly. Expect lumps and a higher scramble risk."),
            ("Checked before whisking", "Whisk it smooth first, then check how it pours.")]),
         B(["Ladle and Mug", "Mixing Bowl and Whisk"]), "None (panel hidden)", P),
        ("Select the appropriate heat level for adding the eggs.", mcq(54)),
        ("Toss the pasta with the eggs into a silky sauce, then plate it.",
         B([f"Select **Mixing Bowl and Whisk** {S}", f"Select **Cast-iron Skillet** {S}",
            "Use the toss-speed buttons and the heat control to keep the sauce between 62 and 70 °C",
            "Click **Plate it** when the sauce is glossy and coats the strands"]),
         B(["Cursor changes to the bowl",
            "The egg mixture pours over the pasta, the thermometer appears and the panel shows the toss controls",
            "The thermometer and the sauce update live while Nonna comments on the temperature",
            "The sauce is judged and the result appears in the feedback popup"]),
         "Look at that shine. Silky!",
         F([("Back to lowest flame briefly if runny (optional, no penalty)", "Gentle heat to thicken. Keep it moving and come off again at the first sign of grains."),
            ("Splash of pasta water if too thick or too hot (optional, no penalty)", "Water loosens it and cools it down at the same time."),
            ("Sauce stays above 70 °C (Fatal)", "It's scrambled. The yolk proteins set into curds. There's no fixing this one."),
            ("Plate while runny (Degraded)", "Too thin. It pools in the bowl. A little gentle heat would have thickened it."),
            ("Plate while grainy (Degraded)", "A few curds formed. Tasty, but not silky.")]),
         B(["Mixing Bowl and Whisk", "Cast-iron Skillet (spot to place it)"]),
         B(["Toss speed: Slow / Medium / Fast", "Heat on/off", "Splash of pasta water", "Plate it"]), P),
    ]),
    ("Step 8: Plate and Serve the Dish", [
        ("Select the appropriate toppings for a classic finish.", mcq(59)),
        ("Plate the pasta with its toppings.",
         B([f"Select **Resting Plate** {S}", f"Select **Cast-iron Skillet** {S}", f"Select **Tongs** {K}",
            f"Select **Serving Bowls (2)** {S}", f"Select **Black Peppercorns** {K}",
            "Tap **Crack pepper over each bowl** repeatedly until the bar fills", f"Select **Pecorino Romano** {K}",
            "Press and hold **Dust with pecorino**"]),
         B(["Cursor changes to the plate", "Most of the crispy tofu folds back into the pasta", "Cursor changes to the tongs",
            "Two pasta nests are twirled into the serving bowls", "Each tap fills the bar and pepper speckles each bowl",
            "While held, pecorino and the reserved tofu go on top of each bowl, along with feedback popup"]),
         "Beautiful. Ready to go out.",
         F([("Toppings added before plating", "Nests first, then the toppings."),
            ("All the tofu folded in", "Keep a few crispy pieces back for the top."),
            ("Wrong spot for the pasta", "The pasta goes into the serving bowls.")]),
         B(["Resting Plate", "Cast-iron Skillet (spot to place it)", "Serving Bowls (2) (spot to place it)", "Service Bell"]),
         B(["Tongs", "Black Peppercorns", "Pecorino Romano", "Kitchen Timer"]), P),
        ("Serve the dish while it's hot.",
         B([f"Select **Service Bell** {S}"]),
         "The bell rings, along with feedback popup; the final screen shows the customer's reaction and the score.",
         "Service! Hot and silky, straight to the customer.",
         F([("Waited more than 60 s before serving (Degraded)", "It's setting in the bowl. Carbonara waits for no one!")]),
         B(["Service Bell"]), "None (panel hidden)", P),
    ]),
]


def rich(text):
    plain, runs, bold = "", [], False
    for part in re.split(r"(\*\*)", text):
        if part == "**":
            bold = not bold; continue
        if part:
            runs.append({"startIndex": len(plain), "format": {"bold": bold}}); plain += part
    cell = {"userEnteredValue": {"stringValue": plain}}
    if any(r["format"]["bold"] for r in runs):
        merged = []
        for r in runs:
            if not merged or merged[-1]["format"] != r["format"]:
                merged.append(r)
        cell["textFormatRuns"] = merged
    return cell


TOP, FIRST_OLD_END = 12, 65          # rows 13..65 (1-based) are rewritten
rows, headers = [], []
for title, tasks in STEPS:
    headers.append(TOP + len(rows))
    rows.append({"values": [rich(title)] + [{"userEnteredValue": {"stringValue": ""}} for _ in range(8)]})
    step = title.split(":")[0].split()[1]
    for n, t in enumerate(tasks, 1):
        tid = {"userEnteredValue": {"stringValue": f"{step}.{n}"}}
        instr = {"userEnteredValue": {"stringValue": t[0]}}
        rest = t[1] if isinstance(t[1], list) else [rich(c) for c in t[1:]]
        rows.append({"values": [tid, instr] + rest})
end = TOP + len(rows)

HEADER_BG = {"red": 0.9529412, "green": 0.8509804, "blue": 0.6509804}
reqs = [{"unmergeCells": {"range": {"sheetId": 0, "startRowIndex": TOP, "endRowIndex": FIRST_OLD_END, "startColumnIndex": 0, "endColumnIndex": 9}}},
        {"updateCells": {"start": {"sheetId": 0, "rowIndex": TOP, "columnIndex": 0}, "rows": rows, "fields": "userEnteredValue,textFormatRuns"}},
        {"deleteDimension": {"range": {"sheetId": 0, "dimension": "ROWS", "startIndex": end, "endIndex": FIRST_OLD_END}}},
        # task-row look everywhere first, then the step bands on top
        {"repeatCell": {"range": {"sheetId": 0, "startRowIndex": TOP, "endRowIndex": end, "startColumnIndex": 0, "endColumnIndex": 9},
                        "cell": {"userEnteredFormat": {"backgroundColorStyle": {"rgbColor": {"red": 1, "green": 1, "blue": 1}},
                                                       "verticalAlignment": "TOP", "textFormat": {"bold": False, "fontSize": 10}}},
                        "fields": "userEnteredFormat.backgroundColorStyle,userEnteredFormat.verticalAlignment,userEnteredFormat.textFormat.bold,userEnteredFormat.textFormat.fontSize"}},
        {"repeatCell": {"range": {"sheetId": 0, "startRowIndex": TOP, "endRowIndex": end, "startColumnIndex": 0, "endColumnIndex": 1},
                        "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}}, "fields": "userEnteredFormat.textFormat.bold"}}]
for h in headers:
    reqs.append({"mergeCells": {"range": {"sheetId": 0, "startRowIndex": h, "endRowIndex": h + 1, "startColumnIndex": 0, "endColumnIndex": 9}, "mergeType": "MERGE_ALL"}})
    reqs.append({"repeatCell": {"range": {"sheetId": 0, "startRowIndex": h, "endRowIndex": h + 1, "startColumnIndex": 0, "endColumnIndex": 9},
                                "cell": {"userEnteredFormat": {"backgroundColorStyle": {"rgbColor": HEADER_BG}, "verticalAlignment": "MIDDLE",
                                                               "textFormat": {"bold": True, "fontSize": 11}}},
                                "fields": "userEnteredFormat.backgroundColorStyle,userEnteredFormat.verticalAlignment,userEnteredFormat.textFormat.bold,userEnteredFormat.textFormat.fontSize"}})
reqs.append({"autoResizeDimensions": {"dimensions": {"sheetId": 0, "dimension": "ROWS", "startIndex": TOP, "endIndex": end}}})

# Step 2 touch-ups: consistent bullets, typo, no full stops on options, and the ways to go wrong.
def cell(row, col, text):
    return {"updateCells": {"start": {"sheetId": 0, "rowIndex": row, "columnIndex": col}, "rows": [{"values": [rich(text)]}],
                            "fields": "userEnteredValue,textFormatRuns"}}
step2 = [
    cell(6, 2, B([f"Select **Extra-firm Tofu** {S}"])),
    cell(6, 5, F([("Towels or heavy pan selected first", "Open the pack and drain it before anything else."),
                  ("Squeeze the block hard by hand (Degraded)", "Gently! You've cracked it. We'll still get cubes, but some will crumble.")])),
    cell(7, 3, B(["Cursor changes to the kitchen towel", "A towel slides onto the board and the tofu settles on top of it",
                  "Cursor changes to the kitchen towel", "The second towel is laid over the tofu",
                  "Cursor changes to the heavy pan", "The heavy pan settles on the towels and the tofu starts pressing"])),
    cell(7, 5, F([("Towel placed on the tofu first", "The first towel goes on the board, underneath the tofu, to catch the water."),
                  ("Heavy pan placed before the towels", "The weight goes on last, on top of the towels."),
                  ("Wrong spot for a towel", "One towel under the tofu, one on top. Try again."),
                  ("Wrong spot for the heavy pan", "The heavy pan goes on top of the tofu to press it."),
                  ("Squeeze the block hard by hand (Degraded)", "Gently! You've cracked it. We'll still get cubes, but some will crumble.")])),
    cell(9, 7, B(["1 cm slabs, cut lengthways", "1 cm strips", "1 cm cubes, cut across", "3 cm chunks", "Crumble by hand"])),
    cell(10, 2, B(["Select **Toss with 1 tsp soy sauce and a pinch of smoked paprika**"])),
    cell(10, 7, B(["Toss with 1 tsp soy sauce and a pinch of smoked paprika", "Salt it generously",
                   "Soak it in 4 tbsp soy sauce", "Leave it plain"])),
]
json.dump(step2 + reqs, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
print("rows", len(rows), "end", end, "headers", headers)
