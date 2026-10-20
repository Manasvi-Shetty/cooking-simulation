"""Export the kitchen set (no food) as a web-ready GLB for the three.js simulation.

Builds on skillet_test.py, adds a stovetop with burner and grate, lifts the skillet
onto the grate, bakes the procedural wood/tile into image textures, and exports.
  blender --background --factory-startup --python export_kitchen.py -- <out.glb>
"""
import bpy, bmesh, os, sys
from math import pi, radians, cos, sin

HERE = os.path.dirname(os.path.abspath(__file__))
os.environ["SCENE_ONLY"] = "1"
base = os.path.join(HERE, "skillet_test.py")
exec(compile(open(base).read(), base, "exec"), {"__file__": base, "__name__": "base_scene"})

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT_GLB = argv[0] if argv else os.path.join(HERE, "..", "web", "assets", "kitchen.glb")
scene = bpy.context.scene

GRATE_TOP = 0.047      # skillet base sits here (cooktop 12 mm + grate 35 mm)


def material(name, color, rough, metal=0.0, coat=0.0):
    mat = bpy.data.materials.new(name)
    try:
        mat.use_nodes = True
    except AttributeError:
        pass
    b = mat.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    b.inputs["Coat Weight"].default_value = coat
    return mat


def box(name, size, loc, mat, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.active_object
    o.name = name
    o.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.data.materials.append(mat)
    if bevel:
        m = o.modifiers.new("Bevel", "BEVEL")
        m.width, m.segments = bevel, 3
        bpy.ops.object.shade_smooth()
    return o


def cylinder(name, r, depth, loc, mat, verts=48, bevel=0.0):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=depth, location=loc)
    o = bpy.context.active_object
    o.name = name
    o.data.materials.append(mat)
    if bevel:
        m = o.modifiers.new("Bevel", "BEVEL")
        m.width, m.segments = bevel, 3
        m.limit_method = "ANGLE"
    bpy.ops.object.shade_smooth()
    return o


STEEL = material("BrushedSteel", (0.72, 0.72, 0.72), 0.32, metal=1.0)
ENAMEL = material("BurnerEnamel", (0.02, 0.02, 0.02), 0.35, coat=0.5)
BRASS = material("BurnerCap", (0.06, 0.06, 0.06), 0.5, metal=0.6)
GRATE = material("GrateIron", (0.03, 0.03, 0.03), 0.6)
KNOB = material("KnobSteel", (0.8, 0.8, 0.8), 0.2, metal=1.0)

# ---------- stovetop ----------
box("Cooktop", (0.62, 0.52, 0.012), (0.0, 0.0, 0.006), STEEL, bevel=0.003)
cylinder("BurnerBase", 0.058, 0.01, (0, 0, 0.017), ENAMEL, bevel=0.002)
cylinder("BurnerCap", 0.042, 0.008, (0, 0, 0.025), BRASS, bevel=0.002)
# Grate: four radial arms on an outer square frame, all cast iron.
for k in range(4):
    a = k * pi / 2 + pi / 4
    arm = box(f"GrateArm{k}", (0.13, 0.011, 0.011), (0.115 * cos(a), 0.115 * sin(a), GRATE_TOP - 0.0055), GRATE, bevel=0.002)
    arm.rotation_euler.z = a
    leg = box(f"GrateLeg{k}", (0.012, 0.012, GRATE_TOP - 0.012), (0.17 * cos(a), 0.17 * sin(a), (GRATE_TOP + 0.012) / 2), GRATE, bevel=0.002)
F = 0.127                                              # frame half-size, under the arm tips
for k, (sx, sy, x, y) in enumerate([(2 * F, 0.012, 0, F), (2 * F, 0.012, 0, -F),
                                    (0.012, 2 * F, F, 0), (0.012, 2 * F, -F, 0)]):
    box(f"GrateFrame{k}", (sx + 0.012, sy, 0.011), (x, y, GRATE_TOP - 0.0055), GRATE, bevel=0.002)
# Control knob, front right.
knob = cylinder("HeatKnob", 0.024, 0.022, (0.24, -0.19, 0.023), KNOB, bevel=0.002)
box("HeatKnobGrip", (0.034, 0.008, 0.012), (0.24, -0.19, 0.039), KNOB, bevel=0.002)

# ---------- move the set around the stove ----------
for name in ("Skillet", "Handle", "HelperHandle"):
    bpy.data.objects[name].location.z += GRATE_TOP
for name, (x, y) in {"Bowl": (-0.46, 0.16), "Egg0": (0.44, 0.2), "Egg1": (0.5, 0.12)}.items():
    o = bpy.data.objects[name]
    o.location.x, o.location.y = x, y
# Yolk spheres were placed relative to the old bowl position; move them with it.
for o in bpy.data.objects:
    if o.data and getattr(o.data, "materials", None) and o.data.materials and o.data.materials[0].name == "Yolk":
        o.location.x += -0.46 - (-0.24)
        o.location.y += 0.16 - 0.21


# ---------- bake procedural materials to images (glTF can't carry node shaders) ----------
def bake_color(obj, size):
    mat = obj.data.materials[0]
    nt = mat.node_tree
    img = bpy.data.images.new(f"{obj.name}_color", size, size)
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    nt.nodes.active = tex
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.bake(type="DIFFUSE", pass_filter={"COLOR"}, margin=4)
    img.file_format = "JPEG"
    # Swap the procedural graph for the baked image, keeping roughness as a constant.
    bsdf = nt.nodes["Principled BSDF"]
    for link in list(bsdf.inputs["Base Color"].links) + list(bsdf.inputs["Normal"].links) + \
            list(bsdf.inputs["Roughness"].links):
        nt.links.remove(link)
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    return img


scene.render.engine = "CYCLES"
scene.cycles.samples = 4
scene.cycles.device = "CPU"
bake_color(bpy.data.objects["Counter"], 2048)
bake_color(bpy.data.objects["Backsplash"], 1024)
for name, rough in (("ButcherBlock", 0.42), ("SubwayTile", 0.15)):
    bpy.data.materials[name].node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = rough
# Cast-iron roughness came from a noise texture; use its midpoint.
iron = bpy.data.materials["CastIron"].node_tree
for link in list(iron.nodes["Principled BSDF"].inputs["Roughness"].links):
    iron.links.remove(link)
iron.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.38

# ---------- export ----------
for o in list(bpy.data.objects):
    if o.type in {"LIGHT", "CAMERA", "EMPTY"}:
        bpy.data.objects.remove(o)
os.makedirs(os.path.dirname(os.path.abspath(OUT_GLB)), exist_ok=True)
bpy.ops.export_scene.gltf(filepath=OUT_GLB, export_format="GLB", export_apply=True,
                          export_image_format="JPEG", export_jpeg_quality=88,
                          export_cameras=False, export_lights=False)
print("EXPORT_DONE", OUT_GLB, os.path.getsize(OUT_GLB))
