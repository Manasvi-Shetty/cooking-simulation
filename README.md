# Carbonara Lab

An interactive cooking simulation: make a Roman-style spaghetti carbonara (with crispy tofu
instead of guanciale) for a customer, step by step, with tips from Nonna Pina. Wrong moves have
consequences; some are fatal.

- `web/`: the simulation (three.js). Serve the folder and open `index.html`, e.g.
  `python -m http.server 8765 --directory web`.
- `design/`: the flow spreadsheet (`carbonara_simulation_flow.xlsx`) and scripts.
  `build_flow_sheet.py` builds the sheet, `export_flow_json.py` exports it to `web/flow.json`,
  `build_flow_page.py` builds the tables page.
- `blender/`: Blender 5.2 scripts for the kitchen model, item card images and restaurant render.
  They need the Poly Haven "blinds" HDRI at `assets/hdri/blinds_2k.hdr` (not committed).
