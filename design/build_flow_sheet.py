"""Builds design/carbonara_simulation_flow.xlsx: the content sheet that drives the simulation.

Recipe source: Gabriella Simonian, "The Best Roman Style Spaghetti Carbonara", No Regretti Spaghetti
(https://noregrettispaghetti.co/the-best-roman-style-carbonara/), adapted for 2 servings with tofu
in place of guanciale at the user's request.
"""
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.comments import Comment

OUT = Path(__file__).with_name("carbonara_simulation_flow.xlsx")

# ---------------------------------------------------------------- styles
FONT = "Arial"
HEAD_FILL = PatternFill("solid", fgColor="2B2420")
HEAD_FONT = Font(name=FONT, bold=True, color="FFFFFF", size=10)
BODY_FONT = Font(name=FONT, size=10)
BOLD = Font(name=FONT, size=10, bold=True)
TITLE = Font(name=FONT, size=16, bold=True, color="2B2420")
SUB = Font(name=FONT, size=11, bold=True, color="7A4B12")
INPUT_FILL = PatternFill("solid", fgColor="FFF8E1")      # content cells you edit
CHECK_FILL = PatternFill("solid", fgColor="ECEFF1")      # formula cells: don't edit
BAND_FILLS = [PatternFill("solid", fgColor="FFF8E1"), PatternFill("solid", fgColor="FDEFD3")]
OUTCOME_FILLS = {
    "Perfect": PatternFill("solid", fgColor="DCEFD6"),
    "Acceptable": PatternFill("solid", fgColor="EAF3DF"),
    "Recoverable": PatternFill("solid", fgColor="FFF1C9"),
    "Degraded": PatternFill("solid", fgColor="FBDDB8"),
    "Fatal": PatternFill("solid", fgColor="F6C6BE"),
}
THIN = Side(style="thin", color="D7CCC0")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
WRAP = Alignment(wrap_text=True, vertical="top")

wb = Workbook()


def sheet(title, headers, widths, rows, band_key=None, input_cols=None, check_cols=(), outcome_col=None):
    ws = wb.create_sheet(title)
    ws.append(headers)
    for c in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=c)
        cell.font, cell.fill, cell.alignment, cell.border = HEAD_FONT, HEAD_FILL, Alignment(wrap_text=True, vertical="center"), BORDER
    ws.row_dimensions[1].height = 32
    for r in rows:
        ws.append(r)
    band, last = 0, None
    for r in range(2, ws.max_row + 1):
        if band_key is not None:
            key = ws.cell(row=r, column=band_key).value
            if key != last:
                band, last = band ^ 1, key
        for c in range(1, len(headers) + 1):
            cell = ws.cell(row=r, column=c)
            cell.font, cell.alignment, cell.border = BODY_FONT, WRAP, BORDER
            if c in check_cols:
                cell.fill = CHECK_FILL
            elif band_key is not None:
                cell.fill = BAND_FILLS[band]
            else:
                cell.fill = INPUT_FILL
        if outcome_col:
            v = ws.cell(row=r, column=outcome_col).value
            if v in OUTCOME_FILLS:
                ws.cell(row=r, column=outcome_col).fill = OUTCOME_FILLS[v]
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = "C2" if title in ("Flow",) else "B2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{max(ws.max_row, 2)}"
    return ws


def dropdown(ws, col_letter, list_range, first=2, last=400):
    dv = DataValidation(type="list", formula1=list_range, allow_blank=True, showDropDown=False)
    dv.error, dv.errorTitle = "Pick a value from the list (see the Lists tab).", "Not in list"
    ws.add_data_validation(dv)
    dv.add(f"{col_letter}{first}:{col_letter}{last}")


# ---------------------------------------------------------------- Lists
LISTS = {
    "Substep types": ["MCQ - Single select", "MCQ - Multi select", "Procedure"],
    "Correctness": ["Correct", "Acceptable", "Incorrect"],
    "Outcome": ["Perfect", "Acceptable", "Recoverable", "Degraded", "Fatal"],
    "Branch keywords": ["NEXT", "RETRY", "GAME_OVER"],
    "Interaction": ["Click", "Drag", "Hold", "Slider / knob", "Timer", "Repeat click"],
    "Location": ["Scene", "Right panel", "Both"],
    "Camera view": ["Counter", "Cutting board", "Stove", "Peek in the pan", "Sink", "Serving"],
    "Required": ["Yes", "No"],
}

# ---------------------------------------------------------------- Flow
# Step | Step title | Substep ID | Substep title | Type | Required | Left panel | Right panel shows |
# Chef tip ID | Camera | Pass rule | Feedback if incomplete (multi-select) | Max attempts |
# On pass -> | Learning point | Scene state on entry | Notes | (checks)
FLOW = [
    (1, "Assemble the Ingredients and Utensils", "S1.1", "Confirm the order", "MCQ - Single select", "Yes",
     "Select the appropriate order details to confirm what the customer asked for.",
     "Four order summaries (cards)", "T-1.1", "Counter",
     "Select the one correct summary.", "", 2, "S1.2",
     "Reading the brief is the first cooking skill: dietary needs and 'Roman-style' change the whole plan.",
     "Order ticket pinned above the counter; empty counter.", ""),
    (1, "Assemble the Ingredients and Utensils", "S1.2", "Bring the tools", "MCQ - Multi select", "Yes",
     "Select the appropriate tools for preparing the dish.",
     "Equipment cards (12)", "", "Counter",
     "All Correct items selected and no Incorrect items.",
     "You're missing a tool. Think through each stage: press, cut, boil, fry, grate, whisk, move pasta, save water.",
     3, "S1.3",
     "No colander: the pasta moves straight from pot to pan with tongs, carrying starchy water with it.",
     "Empty counter; the chosen tools appear together when the picks pass the check.", ""),
    (1, "Assemble the Ingredients and Utensils", "S1.3", "Bring the ingredients to the table", "MCQ - Multi select", "Yes",
     "Select the appropriate ingredients for two plates of the customer's carbonara.",
     "Pantry and fridge items (14 cards)", "T-1.3", "Counter",
     "All Correct items selected and no Incorrect items. Acceptable items allowed.",
     "Something's missing. Check the order again: pasta, protein, eggs, cheese, seasoning and something to cook the tofu in.",
     3, "S2.1",
     "Carbonara is only five ingredients, so each one matters. No cream: the creaminess comes from egg, cheese, fat and starchy water.",
     "Tools on the counter; the chosen ingredients appear together when the picks pass the check.", "Decoys teach the classic mistakes (cream, garlic, meat)."),
    (2, "Press and Cube the Tofu", "S2.1", "Open the tofu pack", "Procedure", "Yes",
     "Open the tofu pack to drain the packing water.",
     "2 Kitchen Towels, Heavy Pan (not usable yet)", "T-2.1", "Cutting board",
     "Action A-2.1-01.", "", 3, "S2.2",
     "Packing water has to go before pressing can draw out the water inside.",
     "Tofu package on the board.", ""),
    (2, "Press and Cube the Tofu", "S2.2", "Press the tofu", "Procedure", "Yes",
     "Draw out moisture from the tofu.",
     "2 Kitchen Towels, Heavy Pan", "", "Cutting board",
     "Actions A-2.2-01 to 03 in order.", "", 3, "S2.3",
     "Water on the surface turns to steam and stops browning. Dry tofu crisps; wet tofu steams.",
     "Drained tofu block on the board.", ""),
    (2, "Press and Cube the Tofu", "S2.3", "Choose the pressing time", "MCQ - Single select", "Yes",
     "Select the appropriate pressing time for draining the tofu.",
     "Timer options (4)", "", "Cutting board",
     "Select the Correct option.", "", 2, "S2.4",
     "15-20 minutes removes most surface water. Use the time to get the pasta water on.",
     "Tofu stack with weight on top.", "Timer fast-forwards; the scene shows water pooling on the towel."),
    (2, "Press and Cube the Tofu", "S2.4", "Cut the tofu into cubes", "Procedure", "Yes",
     "Select the appropriate cuts for evenly sized pieces that crisp well.",
     "The cuts as a pick-all-that-apply list", "T-2.4", "Cutting board",
     "Tick A-2.4-01 to 03 (multi-select), then Check; they animate in order.",
     "Something’s missing. Which cuts get you all the way to 1 cm cubes?", 3, "S2.5",
     "Even 1 cm cubes cook at the same rate and give the most crisp surface per bite.",
     "Pressed tofu block on the board.", "Cutting pattern: slabs, then strips, then cubes."),
    (2, "Press and Cube the Tofu", "S2.5", "Season the tofu", "MCQ - Single select", "No",
     "Select the appropriate seasoning for a savoury, smoky flavour.",
     "Seasoning options (4)", "T-2.5", "Cutting board",
     "Select the Correct option.", "", 2, "S3.1",
     "Soy sauce adds savoury depth (umami); smoked paprika adds smokiness. Go light: pecorino is already very salty.",
     "Tofu cubes in a bowl.", "Optional substep: skipping it gives a Degraded 'bland' note."),
    (3, "Boil the Pasta Water", "S3.1", "Fill the pasta pot", "Procedure", "Yes",
     "Fill the pot with enough water for the pasta to move freely.",
     "None (panel hidden)", "T-3.1", "Sink",
     "Actions A-3.1-01 to 02 in order.", "", 3, "S3.2",
     "Lots of water stays at the boil when the pasta goes in, and gives the strands room so they don't stick.",
     "Pot on the counter next to the sink.", ""),
    (3, "Boil the Pasta Water", "S3.2", "Bring the water to the boil", "Procedure", "Yes",
     "Bring the water to a fast boil.",
     "None (panel hidden)", "", "Sink",
     "Actions A-3.2-01 to 03 in order.", "", 3, "S4.1",
     "Water takes about 10 minutes to boil, so start it early and prep while it heats.",
     "Filled pot in the sink.", "Salt goes in later (S6.1), once the water boils."),
    (4, "Crisp the tofu", "S4.1", "Choose how to start the pan", "MCQ - Single select", "Yes",
     "The classic recipe starts guanciale in a cold pan. How should you start the tofu?",
     "Four ways to start the pan", "T-4.1", "Stove",
     "Select the Correct option.", "", 2, "S4.2",
     "Guanciale starts cold so its fat can melt out slowly. Tofu has almost no fat, so it needs hot oil to crisp instead of stick.",
     "Empty skillet on the front burner; burner off.", "Key adaptation moment from guanciale to tofu."),
    (4, "Crisp the tofu", "S4.2", "Fry the tofu until golden", "Procedure", "Yes",
     "Heat the oil, then fry the tofu until golden and crisp on most sides.",
     "Olive oil, tofu cubes, tongs, smoked paprika and soy (if seasoned)", "T-4.2", "Stove",
     "Actions A-4.2-01 to 07 in order; heat and wait times inside the target ranges.", "", 2, "S4.3",
     "Browning (the Maillard reaction) starts around 140 °C. Moving the tofu too soon tears the crust before it forms.",
     "Skillet on burner; heat knob at Off.", "Live sim: heat knob, wait-time choices, Peek view to judge colour."),
    (4, "Crisp the tofu", "S4.3", "Lift out the tofu, keep the oil", "Procedure", "Yes",
     "The tofu is crisp. Turn off the heat and set the tofu aside, but keep the flavoured oil in the pan.",
     "Slotted spoon, plate", "T-4.3", "Stove",
     "Actions A-4.3-01 to 03 in order.", "", 2, "S5.1",
     "The oil now carries flavour and becomes the fat in the sauce emulsion. Tofu goes back in at the end so it stays crisp.",
     "Crisp tofu in the skillet; burner on.", ""),
    (5, "Make the egg mixture", "S5.1", "Choose the eggs", "MCQ - Single select", "Yes",
     "How many eggs for two plates?",
     "Egg combinations (4)", "", "Counter",
     "Select the Correct option.", "", 2, "S5.2",
     "Yolks bring richness and colour; a couple of whole eggs make the sauce looser and easier to handle. Rule: 1 whole + 1 yolk per person, plus 1 yolk 'for the pot'.",
     "Egg carton and empty bowl on the counter.", ""),
    (5, "Make the egg mixture", "S5.2", "Crack and separate the eggs", "Procedure", "Yes",
     "Crack 2 whole eggs into the bowl, then separate 3 more and add only the yolks.",
     "Eggs, mixing bowl, small cup for whites", "T-5.2", "Counter",
     "Actions A-5.2-01 to 03 in order (A-5.2-03 repeated 3 times).", "", 3, "S5.3",
     "Egg whites set at a lower temperature than yolks, which is one reason extra yolks make a more forgiving sauce.",
     "Bowl and egg carton on the counter.", ""),
    (5, "Make the egg mixture", "S5.3", "Pick the grater", "MCQ - Single select", "Yes",
     "Which side of the box grater do you use for the pecorino?",
     "Four grater sides", "T-5.3", "Counter",
     "Select the Correct option.", "", 2, "S5.4",
     "Powder-fine cheese melts evenly into the egg. Coarse shreds clump and turn stringy.",
     "Box grater and a wedge of pecorino on the counter.", ""),
    (5, "Make the egg mixture", "S5.4", "Grate, season and whisk", "Procedure", "Yes",
     "Grate 150 g of pecorino into the eggs, add about ½ tbsp of cracked pepper, and whisk to a thick paste.",
     "Pecorino, box grater, pepper mill, whisk", "", "Counter",
     "Actions A-5.4-01 to 03 in order.", "", 2, "S6.1",
     "Freshly cracked pepper is a main flavour here, not a garnish.",
     "Bowl with eggs.", "No salt: the cheese brings plenty."),
    (6, "Cook the pasta", "S6.1", "Salt the water", "MCQ - Single select", "Yes",
     "The water is at a rolling boil (about 3 litres). How much salt goes in?",
     "Salt amounts (4)", "T-6.1", "Stove",
     "Select the Correct option.", "", 1, "S6.2",
     "Pasta absorbs salt as it cooks. Salt more lightly than usual for carbonara: the pecorino and soy are salty, and the water goes into the sauce.",
     "Pot at a rolling boil.", ""),
    (6, "Cook the pasta", "S6.2", "Add the spaghetti", "Procedure", "Yes",
     "Add the spaghetti and stop it from sticking.",
     "Spaghetti (300 g), tongs", "", "Stove",
     "Actions A-6.2-01 to 03 in order.", "", 2, "S6.3",
     "Stirring in the first minute stops the strands sticking while their surface starch is gelatinising.",
     "Salted water at a rolling boil.", ""),
    (6, "Cook the pasta", "S6.3", "Decide when to pull the pasta", "MCQ - Single select", "Yes",
     "The packet says 11 minutes. When do you take the spaghetti out?",
     "Times (4)", "T-6.3", "Stove",
     "Select the Correct option.", "", 1, "S7.1",
     "The pasta keeps cooking in the pan with the sauce, so it comes out a minute before al dente.",
     "Spaghetti boiling; timer running.", "Timer fast-forwards to the chosen minute."),
    (7, "Bring the sauce together", "S7.1", "Move the pasta into the pan", "Procedure", "Yes",
     "Save some pasta water first, then move the pasta into the pan with the tofu oil.",
     "Mug, ladle, tongs", "T-7.1", "Stove",
     "Actions A-7.1-01 to 04 in order.", "", 2, "S7.2",
     "Starchy pasta water is the glue that binds fat and egg. It's your insurance if the sauce gets too thick.",
     "Pasta near al dente; skillet with flavoured oil.", ""),
    (7, "Bring the sauce together", "S7.2", "Temper the eggs", "Procedure", "Yes",
     "Loosen the egg mixture with hot pasta water until it pours like cream.",
     "Mug of pasta water, whisk, egg bowl", "T-7.2", "Counter",
     "Actions A-7.2-01 to 03 in order.", "", 2, "S7.3",
     "Tempering warms the eggs gradually so they aren't shocked by the hot pan. You can always thicken a sauce, but you can't unscramble one.",
     "Egg paste in the bowl; pasta in the skillet.", ""),
    (7, "Bring the sauce together", "S7.3", "Deal with the heat", "MCQ - Single select", "Yes",
     "The egg mixture is ready. What do you do with the pan before it goes in?",
     "Heat choices (4)", "T-7.3", "Stove",
     "Select the Correct option.", "", 1, "S7.4",
     "Egg yolk starts to thicken around 62 °C and scrambles above 70 °C. A pan on the flame is far hotter than that.",
     "Pasta tossing in the pan on low heat.", ""),
    (7, "Bring the sauce together", "S7.4", "Toss into a silky sauce", "Procedure", "Yes",
     "Pour in the eggs and keep everything moving until the sauce is thick and glossy, like béchamel.",
     "Egg mixture, tongs, mug of pasta water, heat knob; live sauce thermometer", "T-7.4", "Peek in the pan",
     "Actions A-7.4-01 to 03 in order; sauce must end Silky (thickened, no curds).", "", 1, "S8.1",
     "Thicken with gentle heat, loosen with pasta water. Constant movement keeps any one spot from overheating.",
     "Pan off the heat; pasta coated in oil.", "Live sim: speed control, heat on/off, splash water, Plate button."),
    (8, "Finish and serve", "S8.1", "Choose the toppings", "MCQ - Multi select", "Yes",
     "What goes on top before it goes out?",
     "Topping cards (6)", "", "Serving",
     "All Correct items selected and no Incorrect items.",
     "Missing something. A Roman carbonara is finished with two things from the ingredients you already have.",
     2, "S8.2",
     "Keep it simple: the toppings repeat the dish's own flavours.",
     "Two warm bowls on the counter.", ""),
    (8, "Finish and serve", "S8.2", "Plate and serve", "Procedure", "Yes",
     "Fold the tofu back in, twirl each portion into a bowl, top it, and send it out straight away.",
     "Crisp tofu, tongs, 2 bowls, pepper mill, pecorino, service bell", "T-8.2", "Serving",
     "Actions A-8.2-01 to 05 in order, within 60 s (sim time).", "", 1, "END",
     "Carbonara keeps thickening as it cools. Serve it immediately.",
     "Finished pasta in the pan.", "Leads to the Outcomes screen."),
]
# Multi-select branching (storyboard): the popup when several incorrect items are checked at once
# ({items} becomes their names), and the line added after the incorrect feedback when something
# is also missing.
MULTI_FEEDBACK = {
    "S1.2": ("A few of these won't help today: {items}. Walk through the dish: press, cut, boil, fry, grate, whisk, "
             "move the pasta, save the water. Which tools does each stage really need?",
             "And something's still missing. Think through each stage again."),
    "S1.3": ("Some of these don't belong in this carbonara: {items}. Read the order again: no meat, no cream, and keep it Roman.",
             "And you're short of something. Check the order again."),
    "S2.4": ("", "And you'll need more cuts to get to even 1 cm cubes."),
}
# Procedure mistakes that aren't actions (storyboard): panel items picked before their turn, and an
# item dropped on the wrong spot. Written into the Flow tab as "ID, ID: text" / "ID: text | ID: text";
# a wrong-spot item can name extra decoy spots to show while it's held: "ID [SPOT SPOT]: text".
TOO_EARLY = {
    "S3.1": "E-KNOB-BACK, T-LID: Fill the pot with water first.",
    "S2.1": "T-TOWELS, E-WEIGHT: Open the pack and drain it before anything else.",
}
WRONG_SPOT = {
    "S3.1": "T-POT [E-BURNER-BACK E-COUNTER]: The pot needs to go under the tap. Put it in the sink.",
    "S3.2": "T-POT [E-COUNTER]: That's not where it boils. Put it on the back burner.",
    "S2.2": "T-TOWELS: One towel under the tofu, one on top. Try again. | E-WEIGHT: The heavy pan goes on top of the tofu to press it.",
}
flow_rows = []
for i, r in enumerate(FLOW, start=2):
    assert len(r) == 17, (r[2], len(r))
    flow_rows.append(list(r) + [
        f'=COUNTIF(\'MCQ Options\'!$B:$B,C{i})+COUNTIF(\'Procedure Actions\'!$B:$B,C{i})',
        f'=IF(I{i}="","None",IF(COUNTIF(\'Chef Tips\'!$A:$A,I{i})>0,"OK","Missing tip"))',
        f'=IF(R{i}=0,"No options/actions",IF(S{i}="Missing tip","Fix tip",IF(OR(N{i}="END",COUNTIF($C:$C,N{i})>0),"OK","Bad next ID")))',
    ] + list(MULTI_FEEDBACK.get(r[2], ("", ""))) + [TOO_EARLY.get(r[2], ""), WRONG_SPOT.get(r[2], "")])

# ---------------------------------------------------------------- MCQ options
# Option ID | Substep | Option label (right panel) | Item ID | Correctness | Outcome | Chef feedback | Branch to | Score | State effect
O = []


def opt(sub, label, item, correct, outcome, feedback, branch, score, effect=""):
    letter = chr(ord("a") + sum(1 for r in O if r[1] == sub))
    O.append([f"O-{sub[1:]}-{letter}", sub, label, item, correct, outcome, feedback, branch, score, effect])


opt("S1.1", "2 × Roman-style carbonara (no cream), no meat: tofu instead, extra-crispy", "", "Correct", "Perfect",
    "Exactly. Roman-style means no cream; no meat means tofu, extra crispy. Let's build the plan around that.", "NEXT", 0, "order_confirmed = true")
opt("S1.1", "2 × classic carbonara with guanciale", "", "Incorrect", "Recoverable",
    "Read it again: Saumya doesn't eat meat. That changes our protein.", "RETRY", -5)
opt("S1.1", "2 × creamy carbonara with tofu", "", "Incorrect", "Recoverable",
    "She asked for Roman-style, and a Roman carbonara never has cream. Its creaminess comes from egg, cheese and pasta water.", "RETRY", -5)
opt("S1.1", "4 × tofu carbonara, no cream", "", "Incorrect", "Recoverable",
    "Close, but count again: it's a table for two.", "RETRY", -5)

for label, item, cor, out, fb in [
    ("Spaghetti (dried, bronze-cut)", "I-SPAGHETTI", "Correct", "Perfect", "Dried pasta releases more starch into the water than fresh. Perfect."),
    ("Extra-firm Tofu", "I-TOFU", "Correct", "Perfect", "Extra-firm holds its shape and crisps. Silken would fall apart."),
    ("Eggs", "I-EGGS", "Correct", "Perfect", "The heart of the sauce."),
    ("Pecorino Romano", "I-PECORINO", "Correct", "Perfect", "Sharp, salty sheep's cheese from Lazio. The classic choice."),
    ("Black Peppercorns", "I-PEPPER", "Correct", "Perfect", "Whole, so we can crack them fresh."),
    ("Coarse Salt", "I-SALT", "Correct", "Perfect", "For the pasta water."),
    ("Olive Oil", "I-OIL", "Correct", "Perfect", "Tofu has no fat to render, so the oil does that job."),
    ("Soy Sauce", "I-SOY", "Acceptable", "Acceptable", "Good thinking: a little soy gives the tofu savoury depth."),
    ("Smoked Paprika", "I-PAPRIKA", "Acceptable", "Acceptable", "Nice. A pinch brings back the smokiness guanciale would have given."),
    ("Guanciale", "I-GUANCIALE", "Incorrect", "Recoverable", "That's the classic, but our customer doesn't eat meat. Put it back."),
    ("Heavy Cream", "I-CREAM", "Incorrect", "Recoverable", "No cream! She asked for Roman-style, and in Rome carbonara never has cream."),
    ("Garlic", "I-GARLIC", "Incorrect", "Recoverable", "Garlic isn't in carbonara. Keep it for another dish."),
    ("Butter", "I-BUTTER", "Incorrect", "Recoverable", "We don't need butter. The oil and egg give us all the richness."),
    ("Parsley", "I-PARSLEY", "Incorrect", "Recoverable", "Pretty, but it doesn't belong here."),
]:
    opt("S1.3", label, item, cor, out, fb, "NEXT" if cor != "Incorrect" else "RETRY", 0 if cor != "Incorrect" else -3)

for label, item, cor, out, fb in [
    ("Large Pot with Lid", "T-POT", "Correct", "Perfect", "Big pot, lots of room for the spaghetti to move."),
    ("Heavy Skillet (Cast Iron)", "T-SKILLET", "Correct", "Perfect", "Heavy pans hold heat evenly. Great for crisping tofu."),
    ("Chef's Knife and Board", "T-KNIFE", "Correct", "Perfect", "For neat 1 cm cubes."),
    ("2 Kitchen Towels", "T-TOWELS", "Correct", "Perfect", "To press the water out of the tofu."),
    ("Box Grater", "T-GRATER", "Correct", "Perfect", "We'll use its finest side."),
    ("Mixing Bowl and Whisk", "T-BOWL", "Correct", "Perfect", "For the egg mixture."),
    ("Slotted Spoon", "T-SLOTTED", "Correct", "Perfect", "Lifts the tofu out and leaves the oil behind."),
    ("Tongs", "T-TONGS", "Correct", "Perfect", "To move the pasta straight into the pan."),
    ("Ladle and Mug", "T-MUG", "Correct", "Perfect", "To save pasta water. Don't forget it!"),
    ("Colander", "T-COLANDER", "Incorrect", "Recoverable", "No colander. If we drain the pasta, we pour our best ingredient, the starchy water, down the sink."),
    ("Blender", "T-BLENDER", "Incorrect", "Recoverable", "A whisk is all we need. A blender would whip air into the eggs."),
    ("Baking Tray", "T-TRAY", "Incorrect", "Recoverable", "No oven today. Everything happens on the stove."),
]:
    opt("S1.2", label, item, cor, out, fb, "NEXT" if cor != "Incorrect" else "RETRY", 0 if cor != "Incorrect" else -3)

opt("S2.3", "No pressing, straight to the knife", "", "Incorrect", "Degraded",
    "Wet tofu steams and sticks. It'll never get properly crisp.", "NEXT", -10, "tofu_moisture = high; press_minutes = 0")
opt("S2.3", "5 minutes", "", "Incorrect", "Degraded",
    "A start, but there's still plenty of water inside. It will spit and stay soft.", "NEXT", -5, "tofu_moisture = medium; press_minutes = 5")
opt("S2.3", "15-20 minutes", "", "Correct", "Perfect",
    "Perfect.", "NEXT", 0, "tofu_moisture = low; press_minutes = 20")
opt("S2.3", "2 hours", "", "Incorrect", "Recoverable",
    "It would be very dry, but Table 6 would be gone by then! 15-20 minutes does the job.", "RETRY", -3)

opt("S2.5", "Toss with 1 tsp soy sauce and a pinch of smoked paprika", "I-SOY", "Correct", "Perfect",
    "Savoury and a little smoky. That's our guanciale stand-in. We'll add the paprika at the end of frying so it doesn't burn.", "NEXT", 0, "tofu_seasoned = true")
opt("S2.5", "Salt it generously", "I-SALT", "Incorrect", "Degraded",
    "Careful. Pecorino is very salty, so the dish will be over-salted.", "NEXT", -5, "salt_level += 1")
opt("S2.5", "Soak it in 4 tbsp soy sauce", "I-SOY", "Incorrect", "Degraded",
    "Too much liquid. We just pressed the water out! Now it won't crisp, and it'll be very salty.", "NEXT", -10, "tofu_moisture = high; salt_level += 1")
opt("S2.5", "Leave it plain", "", "Acceptable", "Degraded",
    "It will work, but plain tofu is mild. A little seasoning gives the dish its savoury backbone.", "NEXT", -3, "tofu_seasoned = false")

opt("S4.1", "Cold pan, no oil, then heat up (like guanciale)", "", "Incorrect", "Recoverable",
    "That's the rule for guanciale, because it brings its own fat. Tofu has none, so it would weld itself to the pan.", "RETRY", -5)
opt("S4.1", "Cold pan with oil, then heat up", "", "Incorrect", "Recoverable",
    "The tofu would soak up oil as it slowly warms and turn greasy instead of crisp.", "RETRY", -3)
opt("S4.1", "Heat the pan on medium, add 2 tbsp oil, wait until it shimmers", "", "Correct", "Perfect",
    "Yes! Hot oil seals the surface straight away, so it browns instead of sticking.", "NEXT", 0)
opt("S4.1", "Heat the empty pan on high until it smokes", "", "Incorrect", "Recoverable",
    "Too hot. Oil would burn the moment it went in, and the tofu would char outside and stay cold inside.", "RETRY", -5)

opt("S5.1", "2 whole eggs + 3 yolks", "I-EGGS", "Correct", "Perfect",
    "1 whole and 1 yolk each, plus 1 yolk for the pot. Rich, golden and forgiving.", "NEXT", 0, "egg_mix = ideal")
opt("S5.1", "4 whole eggs", "I-EGGS", "Acceptable", "Degraded",
    "It works, but more whites mean a paler, looser sauce that sets sooner.", "NEXT", -5, "egg_mix = whites_heavy")
opt("S5.1", "2 yolks only", "I-EGGS", "Incorrect", "Degraded",
    "Not enough egg to coat 300 g of pasta. It will be dry and sticky.", "NEXT", -10, "egg_mix = too_little")
opt("S5.1", "6 whole eggs and a splash of cream", "I-CREAM", "Incorrect", "Recoverable",
    "Too much egg, and no cream. Let's try that again.", "RETRY", -5)

opt("S5.3", "Finest star-shaped side (powder)", "T-GRATER", "Correct", "Perfect",
    "Fluffy as snow. It will melt straight into the eggs.", "NEXT", 0, "cheese_grain = fine")
opt("S5.3", "Medium holes", "T-GRATER", "Acceptable", "Degraded",
    "Usable, but expect a few little clumps in the sauce.", "NEXT", -3, "cheese_grain = medium")
opt("S5.3", "Large holes", "T-GRATER", "Incorrect", "Degraded",
    "Big shreds won't melt evenly. They'll go stringy and clump in the sauce.", "NEXT", -8, "cheese_grain = coarse")
opt("S5.3", "Slicing blade", "T-GRATER", "Incorrect", "Recoverable",
    "Slices are for a cheese board, not a sauce. Pick another side.", "RETRY", -3)

opt("S6.1", "None", "I-SALT", "Incorrect", "Degraded",
    "Unsalted pasta tastes flat, and no sauce can fix that from the outside.", "NEXT", -8, "salt_level -= 1")
opt("S6.1", "1 tbsp (about 15 g), lighter than usual", "I-SALT", "Correct", "Perfect",
    "Right. Seasoned, but leaving room for the salty pecorino.", "NEXT", 0)
opt("S6.1", "2 tbsp (about 30 g)", "I-SALT", "Acceptable", "Degraded",
    "That's standard for most pasta, but with pecorino and soy this will end up on the salty side.", "NEXT", -5, "salt_level += 1")
opt("S6.1", "Half a cup", "I-SALT", "Incorrect", "Fatal",
    "That's seawater! The pasta and the pasta water, which goes into the sauce, are now inedibly salty.", "GAME_OVER", -100, "ending = FATAL-SALT")

opt("S6.3", "After 7 minutes", "", "Incorrect", "Degraded",
    "Too early. It will still be chalky in the middle after finishing in the sauce.", "NEXT", -8, "pasta_doneness = underdone")
opt("S6.3", "After 10 minutes (1 minute under the packet)", "", "Correct", "Perfect",
    "Just before al dente. It finishes cooking in the pan.", "NEXT", 0, "pasta_doneness = ideal")
opt("S6.3", "After 11 minutes (packet time)", "", "Acceptable", "Degraded",
    "Fine, but it will be slightly soft by the time the sauce is done.", "NEXT", -3, "pasta_doneness = soft")
opt("S6.3", "After 14 minutes", "", "Incorrect", "Degraded",
    "Overcooked. Mushy pasta and a gluey sauce.", "NEXT", -10, "pasta_doneness = mushy")

opt("S7.3", "Take the pan off the heat", "", "Correct", "Perfect",
    "Exactly. The pasta's own heat is enough to start thickening the eggs.", "NEXT", 0, "heat = off")
opt("S7.3", "Turn it to the lowest flame", "", "Acceptable", "Recoverable",
    "Risky. You'll need to toss fast and watch the thermometer closely.", "NEXT", -3, "heat = low")
opt("S7.3", "Leave it on medium", "", "Incorrect", "Degraded",
    "Way too hot for eggs. You'll be fighting to stop them scrambling.", "NEXT", -8, "heat = medium")
opt("S7.3", "Turn it up so the sauce thickens faster", "", "Incorrect", "Fatal",
    "The eggs hit a scorching pan and set in seconds. Scrambled eggs on spaghetti.", "GAME_OVER", -100, "ending = FATAL-SCRAMBLED")

for label, cor, out, fb in [
    ("Freshly cracked black pepper", "Correct", "Perfect", "Yes. A fresh crack for aroma."),
    ("A dusting of pecorino", "Correct", "Perfect", "Yes. A little more on top."),
    ("Chopped parsley", "Incorrect", "Recoverable", "Not on a Roman carbonara. Let's keep it classic."),
    ("A drizzle of cream", "Incorrect", "Recoverable", "No cream. She ordered it Roman-style!"),
    ("Chilli flakes", "Incorrect", "Recoverable", "Nice on other pastas, but it would drown out the pepper and cheese here."),
    ("Extra crispy tofu on top", "Acceptable", "Acceptable", "Good idea for an 'extra-crispy' request: a few pieces on top stay crunchiest."),
]:
    opt("S8.1", label, "", cor, out, fb, "NEXT" if cor != "Incorrect" else "RETRY", 0 if cor != "Incorrect" else -3)

# ---------------------------------------------------------------- Procedure actions
# Action ID | Substep | Order | Interaction | Source element | Source location | Target element | Parameter / value |
# Correctness | Outcome | Chef feedback (correct) | Chef feedback (out of order / wrong) | Branch to | Score | State effect
A = []


def act(sub, order, inter, src, srcloc, tgt, param, correct, outcome, ok_fb, bad_fb, branch, score, effect=""):
    n = sum(1 for r in A if r[1] == sub) + 1
    A.append([f"A-{sub[1:]}-{n:02d}", sub, order, inter, src, srcloc, tgt, param, correct, outcome, ok_fb, bad_fb, branch, score, effect])


S = "Scene"; RP = "Right panel"
act("S2.1", 1, "Click", "I-TOFU", S, "", "Open the pack", "Correct", "Perfect",
    "", "Open the pack and drain it before anything else.", "NEXT", 0)

act("S2.2", 1, "Drag", "T-TOWELS", RP, "E-BOARD", "First towel under the tofu", "Correct", "Perfect",
    "", "The first towel goes on the board, underneath the tofu, to catch the water.", "NEXT", 0)
act("S2.2", 2, "Drag", "T-TOWELS", RP, "I-TOFU", "Second towel on top", "Correct", "Perfect",
    "", "The first towel goes on the board, underneath the tofu, to catch the water.", "NEXT", 0)
act("S2.2", 3, "Drag", "E-WEIGHT", RP, "I-TOFU", "Heavy pan on top as a weight", "Correct", "Perfect",
    "", "The weight goes on last, on top of the towels.", "NEXT", 0, "tofu_pressing = true")

# The cuts as a pick-all-that-apply list → Check: the three 1 cm cuts animate in order.
act("S2.4", 1, "Click", "T-KNIFE", RP, "E-CUT-GUIDES", "1 cm slabs, cut lengthways", "Correct", "Perfect",
    "", "Slabs first, so every piece ends up the same height.", "NEXT", 0)
act("S2.4", 2, "Click", "T-KNIFE", RP, "E-CUT-GUIDES", "1 cm strips", "Correct", "Perfect",
    "", "Slabs, then strips, then cubes.", "NEXT", 0)
act("S2.4", 3, "Click", "T-KNIFE", RP, "E-CUT-GUIDES", "1 cm cubes, cut across", "Correct", "Perfect",
    "Neat little cubes, just like guanciale.", "Cut the strips first.", "NEXT", 0, "tofu_cut = cubes_1cm")
act("S2.4", "-", "Click", "T-KNIFE", RP, "E-CUT-GUIDES", "3 cm chunks", "Incorrect", "Degraded",
    "", "Too big. The outside will crisp but the middle stays soft, and they won't sit nicely on a fork.", "NEXT", -5, "tofu_cut = chunks")
act("S2.4", "-", "Click", "T-KNIFE", RP, "E-CUT-GUIDES", "Crumble by hand", "Incorrect", "Degraded",
    "", "Crumbles burn quickly and vanish into the pasta. Cubes give you a crisp bite.", "NEXT", -5, "tofu_cut = crumbled")

act("S3.1", 1, "Drag", "T-POT", S, "E-SINK", "Pot under the tap", "Correct", "Perfect",
    "", "", "NEXT", 0)
act("S3.1", 2, "Click", "E-TAP", S, "", "Fill to about 3 litres (fill line)", "Correct", "Perfect",
    "Plenty of water, so the pasta moves freely.", "Place the pot under the tap first.", "NEXT", 0, "water_l = 3")
act("S3.1", "-", "Click", "E-TAP", S, "", "Fill only to 1 litre", "Incorrect", "Recoverable",
    "", "Too little. The water would drop off the boil and the pasta would stick. Fill it to the line.", "RETRY", -3)

act("S3.2", 1, "Drag", "T-POT", S, "E-BURNER-BACK", "Pot onto the back burner", "Correct", "Perfect",
    "", "", "NEXT", 0)
act("S3.2", "-", "Slider / knob", "E-KNOB-BACK", S, "", "Low", "Incorrect", "Recoverable",
    "", "Full heat for the pasta water.", "RETRY", 0)
act("S3.2", "-", "Slider / knob", "E-KNOB-BACK", S, "", "Medium", "Incorrect", "Recoverable",
    "", "Full heat for the pasta water.", "RETRY", 0)
act("S3.2", 2, "Slider / knob", "E-KNOB-BACK", S, "", "High", "Correct", "Perfect",
    "", "Pot first, then the heat.", "NEXT", 0)
act("S3.2", 3, "Drag", "T-LID", S, "T-POT", "Lid on", "Correct", "Perfect",
    "A lid brings it to the boil much faster.", "Get the pot heating first, then the lid goes on.", "NEXT", 0, "water_heating = true")

act("S4.2", 1, "Slider / knob", "E-KNOB-FRONT", S, "", "Medium (target 170-200 °C)", "Correct", "Perfect",
    "", "Heat the pan first.", "NEXT", 0)
act("S4.2", 2, "Drag", "I-OIL", RP, "T-SKILLET", "2 tbsp olive oil", "Correct", "Perfect",
    "", "Oil before tofu.", "NEXT", 0)
act("S4.2", 3, "Timer", "E-PAN-OIL", S, "", "Wait until the oil shimmers (about 1 min)", "Correct", "Perfect",
    "See it ripple? That's hot enough.", "Wait for the shimmer, or the tofu will stick.", "NEXT", 0)
act("S4.2", 4, "Drag", "I-TOFU", S, "T-SKILLET", "Tofu cubes in a single layer", "Correct", "Perfect",
    "Listen to that sizzle.", "", "NEXT", 0, "tofu_in_pan = true")
act("S4.2", 5, "Timer", "E-TIMER", S, "", "Leave undisturbed 3 min (choices: 1 / 3 / 6 min)", "Correct", "Perfect",
    "", "Don't touch it yet: the crust needs time to form.", "NEXT", 0)
act("S4.2", 6, "Click", "T-TONGS", RP, "T-SKILLET", "Toss / turn the cubes", "Correct", "Perfect",
    "Golden underneath. Now the other sides.", "", "NEXT", 0)
act("S4.2", 7, "Timer", "E-TIMER", S, "", "Another 3-4 min, then add soy and paprika for the last 30 s", "Correct", "Perfect",
    "Crisp, golden and smoky.", "", "NEXT", 0, "tofu_state = crisp")
act("S4.2", "-", "Click", "T-TONGS", RP, "T-SKILLET", "Toss in the first minute", "Incorrect", "Degraded",
    "", "Too soon! The crust tore and stuck to the pan. Let it sit next time.", "NEXT", -5, "tofu_torn = true")
act("S4.2", "-", "Slider / knob", "E-KNOB-FRONT", S, "", "High for more than 4 min", "Incorrect", "Fatal",
    "", "Smoke! The tofu and oil have burnt. Bitter, acrid and not servable.", "GAME_OVER", -100, "ending = FATAL-BURNT")
act("S4.2", "-", "Drag", "I-PAPRIKA", RP, "T-SKILLET", "Paprika at the start of frying", "Incorrect", "Degraded",
    "", "Paprika burns fast and turns bitter. Add it in the last 30 seconds.", "NEXT", -5, "paprika_bitter = true")

act("S4.3", 1, "Slider / knob", "E-KNOB-FRONT", S, "", "Off", "Correct", "Perfect",
    "", "Heat off first.", "NEXT", 0)
act("S4.3", 2, "Drag", "T-SLOTTED", RP, "T-SKILLET", "Lift the tofu out (oil drains back)", "Correct", "Perfect",
    "", "", "NEXT", 0)
act("S4.3", 3, "Drag", "T-SLOTTED", S, "E-PLATE", "Tofu onto the plate", "Correct", "Perfect",
    "Set aside. It goes back in at the very end.", "", "NEXT", 0, "tofu_reserved = true")
act("S4.3", "-", "Drag", "T-SKILLET", S, "E-SINK", "Pour the oil away", "Incorrect", "Recoverable",
    "", "That oil was flavour! Add 1 tbsp fresh oil to the pan, but the sauce will taste a little flatter.", "NEXT", -5, "fat_flavour = plain")
act("S4.3", "-", "Click", "T-SKILLET", S, "", "Leave the tofu in the pan", "Incorrect", "Degraded",
    "", "In the sauce it will soak up liquid and go soft. Crispy tofu was the request!", "NEXT", -5, "tofu_state = soggy")

act("S5.2", 1, "Drag", "T-BOWL", RP, "E-COUNTER", "Bowl onto the counter", "Correct", "Perfect", "", "", "NEXT", 0)
act("S5.2", 2, "Repeat click", "I-EGGS", RP, "T-BOWL", "Crack 2 whole eggs into the bowl (×2)", "Correct", "Perfect",
    "", "", "NEXT", 0)
act("S5.2", 3, "Repeat click", "I-EGGS", RP, "E-WHITES-CUP", "Separate: pass the yolk between the shell halves, whites into the cup, yolk into the bowl (×3)", "Correct", "Perfect",
    "Lovely golden yolks.", "Whole eggs first, then the extra yolks.", "NEXT", 0, "yolks_added = 3")
act("S5.2", "-", "Click", "I-EGGS", RP, "T-BOWL", "Shell fragment falls in", "Incorrect", "Recoverable",
    "", "A bit of shell got in. Scoop it out with a larger piece of shell, it works like a magnet.", "NEXT", 0)

act("S5.4", 1, "Hold", "I-PECORINO", RP, "T-BOWL", "Grate 150 g on the chosen side (scale shows grams)", "Correct", "Perfect",
    "", "", "NEXT", 0, "cheese_g = 150")
act("S5.4", 2, "Repeat click", "I-PEPPER", RP, "T-BOWL", "Crack about ½ tbsp pepper (about 12 twists)", "Correct", "Perfect",
    "Be generous, pepper is a main flavour here.", "", "NEXT", 0)
act("S5.4", 3, "Hold", "T-BOWL", RP, "T-BOWL", "Whisk until a thick, smooth paste", "Correct", "Perfect",
    "Thick and smooth. It will loosen with pasta water later.", "Add the cheese and pepper before whisking.", "NEXT", 0, "egg_paste = ready")
act("S5.4", "-", "Drag", "I-SALT", RP, "T-BOWL", "Add salt to the eggs", "Incorrect", "Degraded",
    "", "No salt here. Pecorino brings plenty.", "NEXT", -5, "salt_level += 1")

act("S6.2", 1, "Drag", "I-SALT", RP, "T-POT", "Salt as chosen in S6.1", "Correct", "Perfect", "", "", "NEXT", 0)
act("S6.2", 2, "Drag", "I-SPAGHETTI", RP, "T-POT", "300 g spaghetti", "Correct", "Perfect",
    "In it goes. Push it under as it softens.", "Salt the water first.", "NEXT", 0, "pasta_in = true")
act("S6.2", 3, "Repeat click", "T-TONGS", RP, "T-POT", "Stir during the first minute", "Correct", "Perfect",
    "No sticking.", "", "NEXT", 0)
act("S6.2", "-", "Drag", "I-OIL", RP, "T-POT", "Oil in the water", "Incorrect", "Recoverable",
    "", "Oil just floats on top. Stirring is what stops sticking. And oily pasta won't hold the sauce.", "NEXT", -2)
act("S6.2", "-", "Click", "I-SPAGHETTI", RP, "", "Snap the spaghetti in half", "Incorrect", "Recoverable",
    "", "Mamma mia! Long strands are how you twirl. Push them under gently as they soften.", "NEXT", -2)

act("S7.1", 1, "Drag", "T-MUG", RP, "T-POT", "Ladle about 1 cup of pasta water into the mug", "Correct", "Perfect",
    "Our insurance policy.", "Save the water before you move the pasta!", "NEXT", 0, "water_saved_ml = 240")
act("S7.1", 2, "Slider / knob", "E-KNOB-FRONT", S, "", "Lowest flame", "Correct", "Perfect",
    "", "", "NEXT", 0)
act("S7.1", 3, "Drag", "T-TONGS", RP, "T-SKILLET", "Lift the pasta from pot to pan (water clinging)", "Correct", "Perfect",
    "Straight in, starchy water and all.", "", "NEXT", 0, "pasta_in_pan = true")
act("S7.1", 4, "Repeat click", "T-TONGS", S, "T-SKILLET", "Toss to coat in the oil (about 30 s)", "Correct", "Perfect",
    "Every strand coated in that flavoured oil.", "", "NEXT", 0)
act("S7.1", "-", "Drag", "T-POT", S, "E-SINK", "Drain the pot into the sink", "Incorrect", "Recoverable",
    "", "There goes the pasta water! If you saved a mug you're fine, otherwise the sauce has nothing to loosen it.", "NEXT", -5, "water_saved_ml = 0 if not saved")

act("S7.2", 1, "Drag", "T-MUG", RP, "T-BOWL", "Pour 60 ml (¼ cup) slowly into the eggs", "Correct", "Perfect",
    "", "", "NEXT", 0)
act("S7.2", 2, "Hold", "T-BOWL", RP, "T-BOWL", "Whisk hard while pouring", "Correct", "Perfect",
    "Keep it moving so no egg sits in the hot water.", "", "NEXT", 0)
act("S7.2", 3, "Click", "T-BOWL", S, "", "Check: pours like cream", "Correct", "Perfect",
    "Smooth and pourable. Ready for the pan.", "", "NEXT", 0, "eggs_tempered = true")
act("S7.2", "-", "Drag", "T-MUG", RP, "T-BOWL", "Dump all the hot water in at once without whisking", "Incorrect", "Degraded",
    "", "Some egg cooked into strands. Strain them out if you can. The rest will still work.", "NEXT", -5, "egg_strands = true")
act("S7.2", "-", "Click", "T-BOWL", RP, "", "Skip tempering, pour the cold paste straight into the pan", "Incorrect", "Degraded",
    "", "Thick, cold paste hitting hot pasta cooks unevenly. Expect lumps and a higher scramble risk.", "NEXT", -5, "eggs_tempered = false")

act("S7.4", 1, "Drag", "T-BOWL", RP, "T-SKILLET", "Pour the egg mixture over the pasta", "Correct", "Perfect",
    "Now toss, toss, toss!", "", "NEXT", 0, "eggs_in = true")
act("S7.4", 2, "Slider / knob", "E-TOSS-SPEED", S, "", "Toss continuously (Slow / Medium / Fast); watch the thermometer, 62-70 °C", "Correct", "Perfect",
    "", "", "NEXT", 0)
act("S7.4", 3, "Click", "E-PLATE-BTN", S, "", "Plate when glossy and béchamel-thick", "Correct", "Perfect",
    "Look at that shine. Silky!", "", "NEXT", 0)
act("S7.4", "opt", "Slider / knob", "E-KNOB-FRONT", S, "", "Back to lowest flame briefly if runny", "Acceptable", "Recoverable",
    "", "Gentle heat to thicken. Keep it moving and come off again at the first sign of grains.", "NEXT", 0)
act("S7.4", "opt", "Drag", "T-MUG", RP, "T-SKILLET", "Splash of pasta water if too thick or too hot", "Acceptable", "Recoverable",
    "", "Water loosens it and cools it down at the same time.", "NEXT", 0)
act("S7.4", "-", "Timer", "E-THERMO", S, "", "Sauce stays above 70 °C (curds ≥ 0.65)", "Incorrect", "Fatal",
    "", "It's scrambled. The yolk proteins set into curds. There's no fixing this one.", "GAME_OVER", -100, "ending = FATAL-SCRAMBLED")
act("S7.4", "-", "Click", "E-PLATE-BTN", S, "", "Plate while runny (thicken < 0.45)", "Incorrect", "Degraded",
    "", "Too thin. It pools in the bowl. A little gentle heat would have thickened it.", "NEXT", -8)
act("S7.4", "-", "Click", "E-PLATE-BTN", S, "", "Plate while grainy (curds 0.3-0.65)", "Incorrect", "Degraded",
    "", "A few curds formed. Tasty, but not silky.", "NEXT", -10)

act("S8.2", 1, "Drag", "E-PLATE", S, "T-SKILLET", "Fold most of the tofu back in", "Correct", "Perfect", "", "", "NEXT", 0)
act("S8.2", 2, "Drag", "T-TONGS", RP, "E-BOWLS", "Twirl a nest into each bowl (×2)", "Correct", "Perfect",
    "Twist the tongs against the pan to make a tidy nest.", "", "NEXT", 0)
act("S8.2", 3, "Repeat click", "I-PEPPER", RP, "E-BOWLS", "Crack pepper over each bowl", "Correct", "Perfect", "", "", "NEXT", 0)
act("S8.2", 4, "Hold", "I-PECORINO", RP, "E-BOWLS", "Dust with pecorino (plus reserved crispy tofu on top)", "Correct", "Perfect", "", "", "NEXT", 0)
act("S8.2", 5, "Click", "E-BELL", S, "", "Ring the bell: serve immediately", "Correct", "Perfect",
    "Service! Hot and silky, straight to Table 6.", "", "NEXT", 0)
act("S8.2", "-", "Timer", "E-TIMER", S, "", "Wait more than 60 s (sim) before serving", "Incorrect", "Degraded",
    "", "It's setting in the bowl. Carbonara waits for no one!", "NEXT", -5, "sauce_set = true")

# ---------------------------------------------------------------- Chef tips
TIPS = [
    ("T-1.1", "S1.1", "Read the ticket twice", "Before anything touches a pan, read the order twice. Dietary needs change the ingredients, and a request like 'Roman-style' (so no cream) changes the method.", "Got it"),
    ("T-1.3", "S1.3", "Five ingredients, no shortcuts", "Real carbonara is pasta, eggs, pecorino, black pepper and a cured meat. Today tofu takes the meat's place. Creaminess comes from technique, not cream.", "Let's shop"),
    ("T-2.1", "S2.1", "Dry tofu, crisp tofu", "Tofu is mostly water. Press it under a weight and it browns instead of steaming. Use the time to start your pasta water.", "Start pressing"),
    ("T-2.4", "S2.4", "Same size, same cook", "Cut 1 cm cubes. Even pieces brown at the same rate, so none burn while others stay pale.", "Start cutting"),
    ("T-2.5", "S2.5", "Borrow guanciale's flavour", "Guanciale is salty, smoky and savoury. A splash of soy and a pinch of smoked paprika get the tofu part of the way there. Go easy on salt: pecorino is very salty.", "Season"),
    ("T-3.1", "S3.1", "Water first", "A big pot of water takes about 10 minutes to boil. Get it going now, and the rest of the prep fits around it.", "To the sink"),
    ("T-4.1", "S4.1", "Not every rule transfers", "Guanciale goes into a cold pan so its fat melts out slowly. Tofu has no fat to give. Think about what tofu needs instead.", "Choose"),
    ("T-4.2", "S4.2", "Hands off!", "Once the tofu is in the hot oil, leave it alone for about 3 minutes. The crust needs time to form. Move it too early and it tears and sticks.", "Fire up"),
    ("T-4.3", "S4.3", "Save that oil", "The oil in the pan now tastes of crispy, smoky tofu. It becomes the fat in your sauce, so don't pour it away.", "Got it"),
    ("T-5.2", "S5.2", "Yolks for richness", "Extra yolks make the sauce golden, rich and more forgiving, because yolks set at a higher temperature than whites.", "Crack on"),
    ("T-5.3", "S5.3", "Finer is better", "The finer the cheese, the faster and more evenly it melts into the egg. Coarse shreds go stringy and clump.", "Grate"),
    ("T-6.1", "S6.1", "Season the water, gently", "Pasta water should taste seasoned, not like the sea. In carbonara, go lighter: the water ends up in a sauce full of salty pecorino.", "Salt it"),
    ("T-6.3", "S6.3", "One minute early", "Pull the pasta a minute before al dente. It finishes cooking in the pan while the sauce comes together.", "Watch the clock"),
    ("T-7.1", "S7.1", "Never drain carbonara pasta", "Save a mug of pasta water first, then lift the pasta straight into the pan with tongs. The starchy water binds the sauce.", "Ready"),
    ("T-7.2", "S7.2", "Temper the eggs", "Whisk a little hot pasta water into the eggs before they go near the pan. It warms them gently, so they thicken instead of scrambling.", "Whisk"),
    ("T-7.3", "S7.3", "The magic numbers", "Egg yolk thickens at about 62 °C and scrambles above 70 °C. A pan on the flame is over 150 °C. The pasta's own heat is usually enough.", "Decide"),
    ("T-7.4", "S7.4", "Keep it moving", "Toss constantly. Too thin? Brief, gentle heat. Too thick or too hot? A splash of pasta water. You can always thicken a sauce, but you can't unscramble one.", "Toss!"),
    ("T-8.2", "S8.2", "Serve it now", "Carbonara thickens as it cools. Plate it, top it, and get it to the table straight away.", "Plate up"),
]

# ---------------------------------------------------------------- Scene & items
ITEMS = [
    ("I-SPAGHETTI", "Spaghetti, 300 g", "Right panel", "Dried bronze-cut spaghetti in a paper pack", "Select; drag into pot"),
    ("I-TOFU", "Extra-firm tofu, 280 g", "Both", "Block in a water-filled pack; becomes a pressed block, then 1 cm cubes, then golden cubes", "Select; drag; cut; fry"),
    ("I-EGGS", "Eggs", "Right panel", "Carton of 6 brown eggs", "Select; crack; separate"),
    ("I-PECORINO", "Pecorino Romano, 150 g", "Right panel", "Wedge with black rind", "Select; grate"),
    ("I-PEPPER", "Black peppercorns / pepper mill", "Right panel", "Wooden pepper mill", "Select; repeat-click to grind"),
    ("I-SALT", "Coarse salt", "Right panel", "Salt cellar with a measuring spoon", "Select; drag"),
    ("I-OIL", "Olive oil", "Right panel", "Bottle with pour spout", "Select; drag (2 tbsp)"),
    ("I-SOY", "Soy sauce", "Right panel", "Small bottle", "Select; drag"),
    ("I-PAPRIKA", "Smoked paprika", "Right panel", "Small tin", "Select; drag (pinch)"),
    ("I-GUANCIALE", "Guanciale (decoy)", "Right panel", "Cured pork cheek", "Select (incorrect)"),
    ("I-CREAM", "Heavy cream (decoy)", "Right panel", "Carton", "Select (incorrect)"),
    ("I-GARLIC", "Garlic (decoy)", "Right panel", "Bulb", "Select (incorrect)"),
    ("I-BUTTER", "Butter (decoy)", "Right panel", "Block in foil", "Select (incorrect)"),
    ("I-PARSLEY", "Parsley (decoy)", "Right panel", "Bunch", "Select (incorrect)"),
    ("T-POT", "Large pot with lid", "Both", "5 L stainless pot with fill line at 3 L", "Select; drag; lid"),
    ("T-SKILLET", "Cast-iron skillet", "Both", "The skillet from the 3D kitchen", "Drop target for oil, tofu, pasta, eggs"),
    ("T-KNIFE", "Chef's knife", "Right panel", "With the cutting board", "Select; click cut guides"),
    ("T-TOWELS", "Kitchen towels (2)", "Right panel", "Folded linen towels", "Select; drag"),
    ("T-GRATER", "Box grater", "Right panel", "Four sides: star (fine), medium, large, slicer", "Select; choose side"),
    ("T-BOWL", "Mixing bowl and whisk", "Both", "Ceramic bowl", "Select; whisk (hold)"),
    ("T-SLOTTED", "Slotted spoon", "Right panel", "Steel slotted spoon", "Select; drag"),
    ("T-TONGS", "Tongs", "Right panel", "Steel tongs", "Select; drag; toss"),
    ("T-MUG", "Ladle and mug", "Right panel", "Ladle and a ceramic mug for pasta water", "Select; drag; pour"),
    ("T-COLANDER", "Colander (decoy)", "Right panel", "Steel colander", "Select (incorrect)"),
    ("T-BLENDER", "Blender (decoy)", "Right panel", "Countertop blender", "Select (incorrect)"),
    ("T-TRAY", "Baking tray (decoy)", "Right panel", "Sheet pan", "Select (incorrect)"),
    ("E-BOARD", "Cutting board", "Scene", "Wooden board on the counter", "Drop target"),
    ("E-CUT-GUIDES", "Cutting guides", "Scene", "Dashed lines projected on the tofu; sets A, B, C (correct) and X (decoy)", "Click a line set to cut"),
    ("E-WEIGHT", "Heavy pan (weight)", "Right panel", "Spare cast-iron pan used as a press", "Drag on top of tofu"),
    ("E-SINK", "Sink", "Scene", "Sink to the left of the stove", "Drop target"),
    ("E-TAP", "Tap", "Scene", "Mixer tap", "Hold to fill"),
    ("T-LID", "Pot lid", "Scene", "The large pot's lid, resting on the counter", "Drag onto the pot"),
    ("E-BURNER-BACK", "Back burner", "Scene", "Gas burner for the pasta pot", "Drop target"),
    ("E-KNOB-BACK", "Back burner knob", "Scene", "Off / Low / Medium / High", "Turn"),
    ("E-KNOB-FRONT", "Front burner knob", "Scene", "Off / Lowest / Low / Medium / High", "Turn"),
    ("E-PAN-OIL", "Oil in the pan", "Scene", "Shimmers when hot", "Observe; click to check"),
    ("E-TIMER", "Kitchen timer", "Scene", "Wait-time chooser with fast-forward", "Choose a time"),
    ("E-PLATE", "Resting plate", "Scene", "Small plate with paper towel for the tofu", "Drop target"),
    ("E-COUNTER", "Counter", "Scene", "Butcher-block counter", "Drop target"),
    ("E-WHITES-CUP", "Cup for whites", "Scene", "Small glass cup", "Drop target"),
    ("E-TOSS-SPEED", "Toss speed control", "Scene", "Slow / Medium / Fast", "Select"),
    ("E-THERMO", "Sauce thermometer", "Scene", "Live gauge with 62 °C and 70 °C marks", "Observe"),
    ("E-PLATE-BTN", "Plate it button", "Scene", "Ends the tossing", "Click"),
    ("E-BOWLS", "Serving bowls (2)", "Scene", "Warm pasta bowls", "Drop target"),
    ("E-BELL", "Service bell", "Scene", "Brass bell on the pass", "Click to serve"),
]
item_rows = []
for i, r in enumerate(ITEMS, start=2):
    item_rows.append(list(r) + [
        f'=COUNTIF(\'MCQ Options\'!$D:$D,A{i})+COUNTIF(\'Procedure Actions\'!$E:$E,A{i})+COUNTIF(\'Procedure Actions\'!$G:$G,A{i})'])

# ---------------------------------------------------------------- Outcomes
OUTCOMES = [
    ("END-PERFECT", "Score ≥ 90 and no Fatal outcome", "Nonna-approved",
     "Saumya: \"This is incredible. Crispy tofu, silky sauce, and not a drop of cream. Can I get the recipe?\"",
     "Perfetto. That's a real carbonara, tofu and all.", "Recap all steps; unlock 'Carbonara master' badge."),
    ("END-GOOD", "Score 75-89 and no Fatal outcome", "Very good",
     "Saumya: \"Really tasty! Maybe just a touch [saltier / thicker / softer] than I'd expect.\"",
     "Good work. One or two things to tighten up.", "Show the Degraded notes as 'Next time'."),
    ("END-OK", "Score 50-74 and no Fatal outcome", "Edible",
     "Saumya: \"Thanks, it's... fine. The sauce was a bit off.\"",
     "It's dinner. Let's look at what went sideways.", "Show the Degraded notes and offer to replay those steps."),
    ("END-POOR", "Score < 50 and no Fatal outcome", "Sent back",
     "Saumya: \"Sorry, I don't think I can finish this.\"",
     "Every cook has nights like this. Let's try again.", "Offer a full restart."),
    ("FATAL-SALT", "S6.1 half a cup of salt", "Too salty to serve",
     "(Dish never leaves the kitchen.)",
     "Seawater pasta can't be saved. Salt lightly: the cheese does the rest.", "Game over; restart from S6.1."),
    ("FATAL-BURNT", "S4.2 high heat too long", "Burnt tofu",
     "(Smoke alarm; dish never leaves the kitchen.)",
     "Burnt oil turns everything bitter. Medium heat, and patience.", "Game over; restart from S4.1."),
    ("FATAL-SCRAMBLED", "S7.3 heat turned up, or S7.4 sauce held above 70 °C", "Scrambled eggs",
     "(Dish never leaves the kitchen.)",
     "Above 70 °C the yolk sets into curds. Off the heat, keep tossing, and use that pasta water.", "Game over; restart from S7.1."),
]
GRADES = [("Starting score", 100), ("END-PERFECT minimum", 90), ("END-GOOD minimum", 75), ("END-OK minimum", 50)]

# ---------------------------------------------------------------- build
wb.remove(wb.active)

# README
ws = wb.create_sheet("README")
ws.column_dimensions["A"].width = 30
ws.column_dimensions["B"].width = 95
ws["A1"] = "Carbonara Lab: simulation flow"
ws["A1"].font = TITLE
ws["A2"] = "Content sheet for building the cooking simulation. One row = one substep, option, action or tip."
ws["A2"].font = Font(name=FONT, size=10, italic=True, color="5F5A55")
row = 4
blocks = [
    ("Screen layout", [
        ("Left panel", "The step/substep title and the instruction or question (Flow: column G)."),
        ("Right panel", "Options (MCQ Options tab) or items and tools for procedures (Scene & Items tab, Location = Right panel)."),
        ("Chef tip modal", "Opens at the start of a substep when Flow column I names a tip (Chef Tips tab). Dismissed with its button label."),
        ("3D scene", "Clickable elements (Scene & Items tab, Location = Scene). Camera view set per substep (Flow: column J)."),
    ]),
    ("How the tabs connect", [
        ("Order", "The customer order that opens the simulation. Feeds S1.1."),
        ("Flow", "Steps and substeps in play order. 'On pass →' gives the next substep ID (END = Outcomes screen)."),
        ("MCQ Options", "One row per option for MCQ substeps. Substep ID links to Flow."),
        ("Procedure Actions", "One row per action for Procedure substeps. 'Order' is the correct sequence; '-' marks a wrong action, 'opt' an optional one."),
        ("Chef Tips", "Modal content. Tip ID links from Flow."),
        ("Scene & Items", "Every element and item referenced by ID in the other tabs."),
        ("Outcomes", "Endings, customer reactions and score thresholds."),
        ("Lists", "Values for the dropdowns. Add a value here before using it elsewhere."),
    ]),
    ("Substep types", [
        ("MCQ - Single select", "One answer. Each option has its own feedback, outcome and branch."),
        ("MCQ - Multi select", "Pick a set. Pass = every Correct option chosen and no Incorrect ones; Acceptable options are allowed. Missing items trigger Flow column L feedback."),
        ("Procedure", "The learner performs actions on scene elements and right-panel items in the order given. Out-of-order attempts show the 'out of order' feedback."),
    ]),
    ("Outcome scale", [
        ("Perfect", "Correct; full marks."),
        ("Acceptable", "Not ideal, but fine. No or small penalty."),
        ("Recoverable", "Mistake caught in time: feedback, then retry or a fix. The game continues."),
        ("Degraded", "Mistake carries on into the dish: score penalty, noted on the result screen. The game continues."),
        ("Fatal", "Dish ruined: GAME_OVER and a Fatal ending from the Outcomes tab."),
    ]),
    ("Branch keywords", [
        ("NEXT", "Continue to the Flow 'On pass →' substep."),
        ("RETRY", "Stay on the same substep; the attempt counts toward Max attempts. After the last attempt, Nonna reveals the answer and the learner continues with the penalty."),
        ("GAME_OVER", "End now and show the Fatal ending named in State effect."),
        ("A substep ID", "Jump to that substep (e.g. S4.1 to redo the pan)."),
    ]),
    ("Legend", [
        ("Cream / tan cells", "Content to edit. Flow rows are banded by step."),
        ("Grey cells", "Formula checks. Don't type in them."),
        ("Coloured Outcome cells", "Green = Perfect/Acceptable, yellow = Recoverable, orange = Degraded, red = Fatal."),
    ]),
]
for title, pairs in blocks:
    ws.cell(row=row, column=1, value=title).font = SUB
    row += 1
    for k, v in pairs:
        a, b = ws.cell(row=row, column=1, value=k), ws.cell(row=row, column=2, value=v)
        a.font, b.font = BOLD, BODY_FONT
        a.alignment = b.alignment = WRAP
        row += 1
    row += 1

ws.cell(row=row, column=1, value="Content summary (live)").font = SUB
row += 1
summary = [
    ("Steps", "=SUMPRODUCT((Flow!$A$2:$A$200<>\"\")/COUNTIF(Flow!$A$2:$A$200,Flow!$A$2:$A$200&\"\"))"),
    ("Substeps", "=COUNTA(Flow!$C$2:$C$200)"),
    ("  MCQ - Single select", "=COUNTIF(Flow!$E:$E,\"MCQ - Single select\")"),
    ("  MCQ - Multi select", "=COUNTIF(Flow!$E:$E,\"MCQ - Multi select\")"),
    ("  Procedure", "=COUNTIF(Flow!$E:$E,\"Procedure\")"),
    ("MCQ options", "=COUNTA('MCQ Options'!$A$2:$A$400)"),
    ("Procedure actions", "=COUNTA('Procedure Actions'!$A$2:$A$400)"),
    ("Chef tips", "=COUNTA('Chef Tips'!$A$2:$A$200)"),
    ("Fatal branches", "=COUNTIF('MCQ Options'!$F:$F,\"Fatal\")+COUNTIF('Procedure Actions'!$J:$J,\"Fatal\")"),
    ("Substeps with a problem", "=COUNTIFS(Flow!$C$2:$C$200,\"<>\",Flow!$T$2:$T$200,\"<>OK\")"),
    ("Elements never used", "=COUNTIF('Scene & Items'!$F$2:$F$200,0)"),
]
for k, f in summary:
    a, b = ws.cell(row=row, column=1, value=k), ws.cell(row=row, column=2, value=f)
    a.font, b.font, b.fill = BODY_FONT, BOLD, CHECK_FILL
    b.alignment = Alignment(horizontal="left")
    row += 1
row += 1
ws.cell(row=row, column=1, value="Sources and open decisions").font = SUB
row += 1
for k, v in [
    ("Recipe source", "Gabriella Simonian, \"The Best Roman Style Spaghetti Carbonara\", No Regretti Spaghetti, https://noregrettispaghetti.co/the-best-roman-style-carbonara/ (2 servings: 300 g spaghetti, 2 eggs + 3 yolks, 150 g pecorino, ½ tbsp pepper)."),
    ("Adaptation", "Guanciale replaced with extra-firm tofu, as requested. Tofu needs pressing, hot oil (not a cold pan) and seasoning; the frying oil stands in for rendered guanciale fat."),
    ("Open: pecorino and vegetarians", "Pecorino Romano is traditionally made with animal rennet, which strict vegetarians avoid. Drafted as: the customer doesn't eat meat but eats pecorino. Alternatives: a vegetarian hard cheese, or a teaching MCQ in S1.3."),
    ("Open: timings", "Sim times (pressing, boil, frying) are fast-forwarded. Real-time pacing for live substeps (S4.2, S7.4) to be tuned in play-testing."),
    ("Open: scoring", "Penalties in the Score columns are first-pass values; thresholds are on the Outcomes tab."),
]:
    a, b = ws.cell(row=row, column=1, value=k), ws.cell(row=row, column=2, value=v)
    a.font, b.font = BOLD, BODY_FONT
    a.alignment = b.alignment = WRAP
    row += 1

# Order
wo = wb.create_sheet("Order")
wo.column_dimensions["A"].width = 30
wo.column_dimensions["B"].width = 90
wo["A1"] = "Customer order (opening scene)"
wo["A1"].font = TITLE
order = [
    ("Ticket", None),
    ("Order no.", "014"),
    ("Table", "6"),
    ("Time placed", "19:42 (sim clock starts at 0:00)"),
    ("Customer", "Saumya (fictional), with a friend"),
    ("Covers", "2"),
    ("Dish", "Spaghetti carbonara × 2"),
    ("Dietary", "No meat: swap guanciale for tofu. Eats eggs and dairy."),
    ("Requests", "Roman-style, so no cream. Extra-crispy tofu."),
    ("Target time", "25 minutes (sim time) from order to service"),
    ("Printed ticket text", "#014  T6  2 COVERS\n2x SPAGH CARBONARA (ROMAN)\n  ** NO MEAT -> TOFU **\n  tofu extra crispy\n19:42"),
    ("Opening scene", None),
    ("Setting", "Evening service. The ticket printer chatters; the ticket slides onto the rail above the counter."),
    ("Customer line 1", "\"Hi! Could we get two of the carbonara in Roman-style, please?\""),
    ("Customer line 2", "\"Neither of us eats meat, though. Could you do it with tofu instead of the guanciale?\""),
    ("Customer line 3", "\"If the tofu could be extra crispy, that would be amazing.\""),
    ("Server line (to kitchen)", "\"Two carbonara for Table 6. Roman-style. No meat, tofu instead. Extra-crispy tofu!\""),
    ("Nonna Pina intro (modal)", "\"A tofu carbonara! Same technique, new star. Read the ticket carefully: every word on it changes something we do. Ready?\""),
    ("Intro button", "Start cooking"),
    ("Learning goals", None),
    ("Goal 1", "Adapt a recipe to a dietary requirement without losing what makes it work."),
    ("Goal 2", "Understand why tofu is pressed and fried in hot oil while guanciale starts in a cold pan."),
    ("Goal 3", "Build an emulsion from egg, cheese, fat and starchy pasta water, with no cream."),
    ("Goal 4", "Control egg temperature: thickens at ~62 °C, scrambles above 70 °C."),
    ("Success criteria", "Silky, glossy sauce; crisp tofu; well seasoned, not salty; served within the target time."),
]
r = 3
for k, v in order:
    if v is None:
        wo.cell(row=r, column=1, value=k).font = SUB
    else:
        a, b = wo.cell(row=r, column=1, value=k), wo.cell(row=r, column=2, value=v)
        a.font, b.font, b.fill = BOLD, BODY_FONT, INPUT_FILL
        a.alignment = b.alignment = WRAP
        b.border = BORDER
    r += 1
wo.row_dimensions[13].height = 92

FLOW_HEAD = ["Step", "Step title", "Substep ID", "Substep title", "Type", "Required?",
             "Left panel: instruction / question", "Right panel shows", "Chef tip at start (ID)", "Camera view",
             "Pass rule", "Feedback if incomplete (multi-select)", "Max attempts", "On pass →",
             "Learning point (science)", "Scene state on entry", "Notes",
             "Options / actions defined", "Tip check", "Row check",
             "Feedback if several incorrect (multi-select)", "Added if also incomplete (multi-select)",
             "Picked too early (procedure)", "Wrong spot (procedure)"]
wf = sheet("Flow", FLOW_HEAD, [6, 20, 9, 24, 17, 9, 42, 26, 11, 13, 30, 34, 9, 9, 44, 30, 28, 11, 11, 13, 44, 34, 40, 50],
           flow_rows, band_key=1, check_cols=(18, 19, 20))
dropdown(wf, "E", "=Lists!$A$2:$A$4")
dropdown(wf, "F", "=Lists!$H$2:$H$3")
dropdown(wf, "J", "=Lists!$G$2:$G$7")
wf["I1"].comment = Comment("Leave blank for substeps with no tip. The tip opens as a modal before the substep starts.", "Design")
wf["M1"].comment = Comment("Attempts before Nonna reveals the answer. 1 = no retry.", "Design")

wm = sheet("MCQ Options", ["Option ID", "Substep ID", "Option label (right panel)", "Item ID", "Correctness",
                           "Outcome", "Chef feedback (on select)", "Branch to", "Score Δ", "State effect"],
           [10, 9, 40, 13, 11, 12, 60, 11, 8, 30], O, band_key=2, outcome_col=6)
dropdown(wm, "E", "=Lists!$B$2:$B$4")
dropdown(wm, "F", "=Lists!$C$2:$C$6")

# Learner-facing instruction for each required task, shown as a numbered list in the left panel.
TASKS = {
    "A-4.2-01": "Turn the front burner knob to Medium (aim for 170-200 °C).",
    "A-4.2-02": "Pour 2 tbsp of olive oil into the skillet.",
    "A-4.2-03": "Wait until the oil shimmers, about 1 minute.",
    "A-4.2-04": "Add the tofu cubes to the skillet in a single layer.",
    "A-4.2-05": "Set the timer and leave the cubes alone so they can brown.",
    "A-4.2-06": "Use the tongs to turn the cubes over.",
    "A-4.2-07": "Cook 3-4 minutes more; add the soy sauce and paprika in the last 30 seconds.",
    "A-4.3-01": "Turn the front burner knob to Off.",
    "A-4.3-02": "With the slotted spoon, lift the tofu out and let the oil drain back into the pan.",
    "A-4.3-03": "Put the tofu on the resting plate.",
    "A-5.2-01": "Pick the mixing bowl and put it on the counter.",
    "A-5.2-02": "Tap the eggs to crack 2 whole eggs into the bowl.",
    "A-5.2-03": "Separate 3 more eggs: whites go into the cup, yolks into the bowl.",
    "A-5.4-01": "Hold to grate 150 g of pecorino into the bowl. Watch the scale.",
    "A-5.4-02": "Tap the pepper mill about 12 times over the bowl.",
    "A-5.4-03": "Hold to whisk until you have a thick, smooth paste.",
    "A-6.2-01": "Add the salt you chose to the boiling water.",
    "A-6.2-02": "Add the 300 g of spaghetti to the pot.",
    "A-6.2-03": "Tap the tongs to stir the pasta during the first minute so it doesn't stick.",
    "A-7.1-01": "With the ladle, scoop about 1 cup of pasta water into the mug.",
    "A-7.1-02": "Turn the front burner knob to the lowest flame.",
    "A-7.1-03": "With the tongs, lift the pasta from the pot into the skillet.",
    "A-7.1-04": "Tap the tongs to toss the pasta in the oil for about 30 seconds.",
    "A-7.2-01": "Pour about 60 ml (¼ cup) of the pasta water slowly into the egg bowl.",
    "A-7.2-02": "Hold to whisk hard while you pour.",
    "A-7.2-03": "Check the sauce: it should pour like cream.",
    "A-7.4-01": "Pour the egg mixture over the pasta in the skillet.",
    "A-7.4-02": "Keep tossing. Watch the thermometer and stay between 62 and 70 °C.",
    "A-7.4-03": "Plate it as soon as the sauce is glossy and coats the strands.",
    "A-8.2-01": "Fold most of the crispy tofu back into the pasta.",
    "A-8.2-02": "With the tongs, twirl a nest of pasta into each serving bowl.",
    "A-8.2-03": "Tap the pepper mill to crack pepper over each bowl.",
    "A-8.2-04": "Hold to dust each bowl with pecorino, then top with the reserved tofu.",
    "A-8.2-05": "Ring the bell to serve right away.",
}
# Steps whose procedure tasks are merged (storyboard): one instruction per task, from the Flow tab.
MERGED_STEPS = {2, 3}
missing = [r[0] for r in A if r[2] not in ("-", "opt") and r[0] not in TASKS and int(r[1][1]) not in MERGED_STEPS]
assert not missing, f"No task instruction for {missing}"
for r in A:
    r.append(TASKS.get(r[0], ""))

wa = sheet("Procedure Actions", ["Action ID", "Substep ID", "Order", "Interaction", "Source element / item",
                                 "Source location", "Target element", "Parameter / value", "Correctness", "Outcome",
                                 "Chef feedback (done right)", "Chef feedback (wrong / out of order)", "Branch to",
                                 "Score Δ", "State effect", "Task instruction (left panel)"],
           [11, 9, 6, 13, 15, 12, 15, 40, 11, 12, 34, 46, 11, 8, 26, 56], A, band_key=2, outcome_col=10)
dropdown(wa, "D", "=Lists!$E$2:$E$7")
dropdown(wa, "F", "=Lists!$F$2:$F$4")
dropdown(wa, "I", "=Lists!$B$2:$B$4")
dropdown(wa, "J", "=Lists!$C$2:$C$6")
wa["C1"].comment = Comment("1, 2, 3... = correct sequence. '-' = wrong action. 'opt' = optional helper action.", "Design")

wt = sheet("Chef Tips", ["Tip ID", "Substep ID", "Modal title", "Tip text", "Button label"],
           [9, 10, 30, 90, 16], [list(t) for t in TIPS])

wi = sheet("Scene & Items", ["Element / item ID", "Name", "Location", "Visual description", "Interactions", "Times used"],
           [15, 30, 12, 60, 34, 10], item_rows, check_cols=(6,))
dropdown(wi, "C", "=Lists!$F$2:$F$4")

wout = sheet("Outcomes", ["Ending ID", "Trigger", "Result title", "Customer reaction", "Nonna Pina", "Screen notes"],
             [15, 34, 18, 60, 52, 34], [list(o) for o in OUTCOMES])
start = wout.max_row + 2
wout.cell(row=start, column=1, value="Score thresholds").font = SUB
for i, (k, v) in enumerate(GRADES, start=start + 1):
    a, b = wout.cell(row=i, column=1, value=k), wout.cell(row=i, column=2, value=v)
    a.font, b.font, b.fill = BODY_FONT, Font(name=FONT, size=10, color="0000FF"), INPUT_FILL
b.comment = Comment("Design assumption: thresholds are first-pass values to tune in play-testing.", "Design")

wl = wb.create_sheet("Lists")
for c, (name, vals) in enumerate(LISTS.items(), start=1):
    h = wl.cell(row=1, column=c, value=name)
    h.font, h.fill = HEAD_FONT, HEAD_FILL
    for r, v in enumerate(vals, start=2):
        wl.cell(row=r, column=c, value=v).font = BODY_FONT
    wl.column_dimensions[get_column_letter(c)].width = 20

for w in wb.worksheets:
    w.sheet_view.zoomScale = 100
wb.calculation.fullCalcOnLoad = True          # formulas have no cached values; compute on open

# Same checks as the sheet formulas, run here so content errors surface at build time.
ids = {r[2] for r in FLOW}
used = {r[3] for r in O} | {r[4] for r in A} | {r[6] for r in A}
problems = []
for r in FLOW:
    n = sum(1 for o in O if o[1] == r[2]) + sum(1 for a in A if a[1] == r[2])
    if n == 0: problems.append(f"{r[2]}: no options/actions")
    if r[8] and r[8] not in {t[0] for t in TIPS}: problems.append(f"{r[2]}: missing tip {r[8]}")
    if r[13] != "END" and r[13] not in ids: problems.append(f"{r[2]}: bad next {r[13]}")
    if r[4] == "Procedure" and any(o[1] == r[2] for o in O): problems.append(f"{r[2]}: procedure has MCQ options")
    if r[4].startswith("MCQ") and any(a[1] == r[2] for a in A): problems.append(f"{r[2]}: MCQ has actions")
for t in TIPS:
    if t[1] not in ids: problems.append(f"tip {t[0]}: unknown substep {t[1]}")
item_ids = {i[0] for i in ITEMS}
for ref in used - {""}:
    if ref not in item_ids: problems.append(f"unknown element {ref}")
print("CHECKS:", problems or "all OK", "| unused elements:", sorted(item_ids - used) or "none",
      f"| {len(FLOW)} substeps, {len(O)} options, {len(A)} actions, {len(TIPS)} tips, {len(ITEMS)} elements")
wb.save(OUT)
print("saved", OUT)
