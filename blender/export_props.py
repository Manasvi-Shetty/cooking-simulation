"""Export the kitchen props as one web-ready GLB, using the same models as the item cards.

Reuses the item builders from item_cards.py (everything above its studio section), adds a few
props the cards don't have (pepper mill, service bell, flat towel, glass cup), bakes any
procedural colour (towel stripes, tofu, grater holes) into small textures, and exports each prop
under a root node named "P-<name>" so the web page can swap it in for the simple shape.
  blender --background --factory-startup --python export_props.py -- <out.glb>
"""
import bpy, bmesh, os, sys
from math import pi, cos, sin, radians

HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, "item_cards.py"), encoding="utf-8").read()
lib = src[:src.index("# ---------- studio ----------")]
sys.argv = [sys.argv[0], "--", os.path.join(HERE, "..", "renders", "items")]   # item_cards reads an out dir
exec(compile(lib, "item_cards.py", "exec"), globals())

argv_out = [a for a in sys.orig_argv[sys.orig_argv.index("--") + 1:]] if "--" in sys.orig_argv else []
OUT_GLB = argv_out[0] if argv_out else os.path.join(HERE, "..", "web", "assets", "props.glb")


# ---------- props the cards don't have ----------
def p_mill():
    wood = noisy("MillWood", (0.16, 0.08, 0.035), 0.35, 120, 0.15, Coat_Weight=0.4)
    lathe("Mill", [(0, 0), (0.022, 0), (0.024, 0.004), (0.02, 0.03), (0.017, 0.07), (0.02, 0.1), (0.023, 0.112),
                   (0.02, 0.122), (0.012, 0.13), (0, 0.132)], wood, sub=1)
    lathe("MillBand", [(0.0205, 0.098), (0.0215, 0.1), (0.0215, 0.104), (0.0205, 0.106)], STEEL)
    sphere("MillKnob", 0.007, (0, 0, 0.137), STEEL)


def p_bell():
    lathe("BellBase", [(0, 0), (0.038, 0), (0.04, 0.004), (0.036, 0.011), (0, 0.011)], noisy("BellBase", (0.03, 0.025, 0.02), 0.35, 200, 0.1))
    lathe("BellDome", [(0, 0.011), (0.032, 0.011), (0.031, 0.02), (0.025, 0.033), (0.014, 0.04), (0, 0.042)],
          material("BellChrome", (0.86, 0.84, 0.8), 0.12, 1.0), sub=1)
    cyl("Plunger", 0.0025, 0.012, (0, 0, 0.047), STEEL)
    sphere("PlungerCap", 0.005, (0, 0, 0.054), STEEL)


def p_towel():
    """A cotton tea towel lying flat: white with blue stripes, softly wrinkled."""
    from mathutils import noise, Vector as V
    stripe = bpy.data.materials.get("Towel") or None
    if stripe is None:
        t_towels()                                       # creates the striped material
        for o in list(ITEM.objects):
            bpy.data.objects.remove(o, do_unlink=True)
        stripe = bpy.data.materials["Towel"]
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=40, y_segments=30, size=0.5)
    for v in bm.verts:
        x, y = v.co.x * 0.17, v.co.y * 0.12
        z = 0.0012 * noise.noise(V((x, y, 0)) * 40) + 0.0006 * noise.noise(V((x, y, 3)) * 110)
        v.co = (x, y, max(z, -0.0004) + 0.0015)
    o = from_bm("Towel", bm, stripe)
    m = o.modifiers.new("Thick", "SOLIDIFY")
    m.thickness = 0.003


def p_cup():
    lathe("Cup", [(0, 0), (0.028, 0), (0.0315, 0.05), (0.029, 0.05), (0.026, 0.004), (0, 0.004)], GLASS)


def p_tofu():
    """One pressed block, the same textured tofu as the card."""
    tofu_block("Block", (0.1, 0.065, 0.03), (0, 0, 0.015), (0, 0, 0), tofu_material())


def only(names):
    """Keep just these objects of a builder (e.g. the pot without its lid)."""
    def keep_some():
        for o in list(ITEM.objects):
            if not any(o.name.startswith(n) for n in names):
                bpy.data.objects.remove(o, do_unlink=True)
    return keep_some


PROPS = {
    "board": [t_knife],
    "pot": [t_pot, only(["Pot"])],
    "lid": [t_pot, only(["Lid"])],
    "mug": [t_mug, only(["Mug"])],
    "grater": [t_grater],
    "pecorino": [i_pecorino],
    "weight": [e_weight],
    "mill": [p_mill],
    "bell": [p_bell],
    "towel": [p_towel],
    "cup": [p_cup],
    "tofu": [p_tofu],
    "bowl": [t_bowl],
}


# ---------- bake procedural colour so glTF can carry it ----------
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = 8


def baked(obj, size=512):
    mats = [m for m in obj.data.materials if m and m.node_tree]
    needs = [m for m in mats if m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].links]
    if not needs:
        return
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    if not obj.data.uv_layers:
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.smart_project(angle_limit=radians(60), island_margin=0.02)
        bpy.ops.object.mode_set(mode="OBJECT")
    img = bpy.data.images.new(f"{obj.name}_color", size, size)
    for m in needs:
        nt = m.node_tree
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = img
        nt.nodes.active = tex
    bpy.ops.object.bake(type="DIFFUSE", pass_filter={"COLOR"}, margin=4)
    for m in needs:
        nt = m.node_tree
        bsdf = nt.nodes["Principled BSDF"]
        for link in list(bsdf.inputs["Base Color"].links):
            nt.links.remove(link)
        tex = [n for n in nt.nodes if n.type == "TEX_IMAGE" and n.image == img][0]
        nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])


roots = []
for name, steps in PROPS.items():
    ITEM = bpy.data.collections.new(f"P-{name}")
    scene.collection.children.link(ITEM)
    for step in steps:
        step()
    # Curves (tubes) become meshes; modifiers are applied so the web gets the final shape.
    for o in list(ITEM.objects):
        bpy.ops.object.select_all(action="DESELECT")
        o.select_set(True)
        bpy.context.view_layer.objects.active = o
        if o.type == "CURVE":
            bpy.ops.object.convert(target="MESH")
        for mod in list(o.modifiers):
            if mod.type == "SUBSURF":
                mod.levels = mod.render_levels = min(mod.levels, 2)   # keep the web mesh light
            bpy.ops.object.modifier_apply(modifier=mod.name)
    for o in list(ITEM.objects):
        if o.type == "MESH":
            baked(o)
    root = bpy.data.objects.new(f"P-{name}", None)
    ITEM.objects.link(root)
    for o in list(ITEM.objects):
        if o is not root:
            mw = o.matrix_world.copy()
            o.parent = root
            o.matrix_world = mw
    roots.append(root)
    print("PROP", name, sum(len(o.data.polygons) for o in ITEM.objects if o.type == "MESH"))

# Export only the props.
bpy.ops.object.select_all(action="DESELECT")
for coll in [c for c in scene.collection.children if c.name.startswith("P-")]:
    for o in coll.objects:
        o.select_set(True)
os.makedirs(os.path.dirname(os.path.abspath(OUT_GLB)), exist_ok=True)
bpy.ops.export_scene.gltf(filepath=OUT_GLB, export_format="GLB", use_selection=True, export_apply=True,
                          export_image_format="JPEG", export_jpeg_quality=85, export_cameras=False, export_lights=False)
print("EXPORT_DONE", OUT_GLB, os.path.getsize(OUT_GLB))
