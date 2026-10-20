"""Photoreal still of an upscale dining room for the simulation's opening (Ana's order).

Table 6 sits sharp in the right foreground; the room falls away, soft, on the left where
the page puts Ana's speech bubble.
  blender --background --factory-startup --python restaurant_still.py -- <out.png> [preview]
"""
import bpy, bmesh, sys, random
from math import pi, cos, sin, radians
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0] if argv else "//restaurant.png"
PREVIEW = len(argv) > 1 and argv[1] == "preview"

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
rng = random.Random(7)


# ---------- helpers ----------
def link(o):
    scene.collection.objects.link(o)
    return o


def mesh_from(name, bm, mat=None, smooth=True):
    me = bpy.data.meshes.new(name)
    if smooth:
        for f in bm.faces:
            f.smooth = True
    bm.to_mesh(me)
    bm.free()
    o = link(bpy.data.objects.new(name, me))
    if mat:
        o.data.materials.append(mat)
    return o


def lathe(name, prof, mat, steps=64, loc=(0, 0, 0)):
    bm = bmesh.new()
    vs = [bm.verts.new((r, 0, z)) for r, z in prof]
    es = [bm.edges.new((vs[i], vs[i + 1])) for i in range(len(vs) - 1)]
    bmesh.ops.spin(bm, geom=vs + es, cent=(0, 0, 0), axis=(0, 0, 1), angle=2 * pi, steps=steps)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o = mesh_from(name, bm, mat)
    o.location = loc
    return o


def box(name, size, loc, mat, bevel=0.0, rot=(0, 0, 0)):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1)
    for v in bm.verts:
        v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2]))
    o = mesh_from(name, bm, mat, smooth=bevel > 0)
    o.location, o.rotation_euler = loc, rot
    if bevel:
        m = o.modifiers.new("Bevel", "BEVEL")
        m.width, m.segments = bevel, 3
    return o


def cyl(name, r, h, loc, mat, verts=48):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=h, location=loc)
    o = bpy.context.active_object
    o.name = name
    o.data.materials.append(mat)
    bpy.ops.object.shade_smooth()
    return o


def material(name, color=(0.8, 0.8, 0.8), rough=0.5, metal=0.0, **extra):
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except AttributeError:
        pass
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    for k, v in extra.items():
        b.inputs[k.replace("_", " ")].default_value = v
    return m


def emissive(name, color, strength):
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except AttributeError:
        pass
    nt = m.node_tree
    nt.nodes.remove(nt.nodes["Principled BSDF"])
    e = nt.nodes.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = (*color, 1)
    e.inputs["Strength"].default_value = strength
    nt.links.new(e.outputs["Emission"], nt.nodes["Material Output"].inputs["Surface"])
    return m


def point(name, loc, power, color=(1.0, 0.72, 0.42), radius=0.05):
    d = bpy.data.lights.new(name, "POINT")
    d.energy, d.color, d.shadow_soft_size = power, color, radius
    o = link(bpy.data.objects.new(name, d))
    o.location = loc
    return o


# ---------- materials ----------
LINEN = material("Linen", (0.86, 0.84, 0.79), 0.75, Sheen_Weight=0.6, Subsurface_Weight=0.08, Subsurface_Scale=0.01)
PLASTER = material("Plaster", (0.035, 0.06, 0.05), 0.9)
PANEL = material("Panel", (0.06, 0.032, 0.018), 0.38, Coat_Weight=0.4)
BRASS = material("Brass", (0.78, 0.56, 0.27), 0.28, 1.0)
GLASS = material("Glass", (1, 1, 1), 0.0, Transmission_Weight=1.0, IOR=1.45)
CERAMIC = material("Porcelain", (0.92, 0.91, 0.88), 0.15, Coat_Weight=0.6)
SILVER = material("Silver", (0.85, 0.85, 0.85), 0.18, 1.0)
VELVET = material("Velvet", (0.012, 0.035, 0.028), 0.85, Sheen_Weight=0.45, Sheen_Tint=(0.35, 0.55, 0.45, 1))
CURTAIN = material("Curtain", (0.22, 0.025, 0.03), 0.8, Sheen_Weight=1.0)
DARKWOOD = material("Darkwood", (0.05, 0.028, 0.016), 0.35, Coat_Weight=0.3)
WAX = material("Wax", (0.95, 0.92, 0.85), 0.4, Subsurface_Weight=0.6, Subsurface_Scale=0.02)
FLAME = emissive("Flame", (1.0, 0.62, 0.25), 25)
GLOBE = emissive("Globe", (1.0, 0.78, 0.5), 9)
SKY = emissive("Dusk", (0.05, 0.08, 0.22), 0.9)
BACKLIGHT = emissive("BarGlow", (1.0, 0.5, 0.2), 2.0)
ROSE = material("Rose", (0.45, 0.02, 0.05), 0.5, Sheen_Weight=0.5)
LEAF = material("Leaf", (0.03, 0.12, 0.03), 0.5)
WINE = material("WineGlass", (0.7, 0.4, 0.15), 0.0, Transmission_Weight=1.0, IOR=1.45)
BOTTLES = [material(f"Bottle{i}", c, 0.05, Transmission_Weight=0.9, IOR=1.5)
           for i, c in enumerate([(0.25, 0.12, 0.03), (0.05, 0.18, 0.08), (0.5, 0.35, 0.12), (0.6, 0.6, 0.6)])]
CARD = material("Card", (0.93, 0.9, 0.82), 0.6)
INK = material("Ink", (0.08, 0.06, 0.05), 0.5)


def floor_material():
    m = bpy.data.materials.new("Floor")
    try:
        m.use_nodes = True
    except AttributeError:
        pass
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    coord = nt.nodes.new("ShaderNodeTexCoord")
    planks = nt.nodes.new("ShaderNodeTexBrick")
    planks.inputs["Scale"].default_value = 1.0
    planks.inputs["Brick Width"].default_value = 1.2
    planks.inputs["Row Height"].default_value = 0.14
    planks.inputs["Mortar Size"].default_value = 0.002
    planks.inputs["Color1"].default_value = (0.11, 0.06, 0.03, 1)
    planks.inputs["Color2"].default_value = (0.07, 0.038, 0.02, 1)
    planks.inputs["Mortar"].default_value = (0.02, 0.01, 0.006, 1)
    nt.links.new(coord.outputs["Object"], planks.inputs["Vector"])
    grain = nt.nodes.new("ShaderNodeTexWave")
    grain.bands_direction = "Y"
    grain.inputs["Scale"].default_value = 30
    grain.inputs["Distortion"].default_value = 8
    nt.links.new(coord.outputs["Object"], grain.inputs["Vector"])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type, mix.blend_type = "RGBA", "MULTIPLY"
    mix.inputs["Factor"].default_value = 0.35
    nt.links.new(planks.outputs["Color"], mix.inputs["A"])
    nt.links.new(grain.outputs["Color"], mix.inputs["B"])
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.28
    b.inputs["Coat Weight"].default_value = 0.5
    return m


FLOOR = floor_material()

# ---------- room (Z up; camera looks toward +Y) ----------
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 3, 0))
fl = bpy.context.active_object
fl.scale = (12, 12, 1)
bpy.ops.object.transform_apply(scale=True)
fl.data.materials.append(FLOOR)
box("Ceiling", (12, 12, 0.05), (0, 3, 3.45), material("Ceiling", (0.02, 0.018, 0.016), 0.9))
box("BackWall", (12, 0.1, 3.5), (0, 7.05, 1.75), PLASTER)
box("LeftWall", (0.1, 12, 3.5), (-5.05, 3, 1.75), PLASTER)
box("RightWall", (0.1, 12, 3.5), (5.05, 3, 1.75), PLASTER)
# Wainscot panelling with raised panels and a brass rail.
for wall, axis, fixed, span in [("Back", "x", 6.98, (-5, 5)), ("Left", "y", -4.98, (-1, 7)), ("Right", "y", 4.98, (-1, 7))]:
    length = span[1] - span[0]
    if axis == "x":
        box(f"Wainscot{wall}", (length, 0.04, 1.05), (0, fixed, 0.525), PANEL)
        box(f"Rail{wall}", (length, 0.03, 0.025), (0, fixed - 0.03, 1.07), BRASS)
    else:
        box(f"Wainscot{wall}", (0.04, length, 1.05), (fixed, (span[0] + span[1]) / 2, 0.525), PANEL)
        box(f"Rail{wall}", (0.03, length, 0.025), (fixed + (0.03 if fixed < 0 else -0.03), (span[0] + span[1]) / 2, 1.07), BRASS)
    n = int(length / 0.9)
    for i in range(n):
        c = span[0] + (i + 0.5) * length / n
        if axis == "x":
            box(f"Pnl{wall}{i}", (0.7, 0.03, 0.7), (c, fixed - 0.03, 0.52), PANEL, bevel=0.01)
        else:
            box(f"Pnl{wall}{i}", (0.03, 0.7, 0.7), (fixed + (0.03 if fixed < 0 else -0.03), c, 0.52), PANEL, bevel=0.01)

# Tall windows at dusk, framed in dark wood, with velvet curtains.
for i, x in enumerate([-3.6, -1.2]):
    box(f"Sky{i}", (1.3, 0.02, 2.0), (x, 6.99, 2.25), SKY)
    for dx in (-0.66, 0, 0.66):
        box(f"Mullion{i}{dx}", (0.05, 0.05, 2.05), (x + dx, 6.96, 2.25), DARKWOOD)
    for dz in (1.24, 2.0, 3.26):
        box(f"Transom{i}{dz}", (1.36, 0.05, 0.05), (x, 6.96, dz), DARKWOOD)
    for s in (-1, 1):
        bm = bmesh.new()
        bmesh.ops.create_grid(bm, x_segments=40, y_segments=2, size=0.5)
        for v in bm.verts:
            u = v.co.x
            v.co = Vector((u * 0.55, 0.05 * sin(u * 34), v.co.y * 2.7))
        bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=0.02)
        c = mesh_from(f"Curtain{i}{s}", bm, CURTAIN)
        c.location = (x + s * 0.92, 6.85, 1.75)

# Backlit bar on the back-right: three shelves of bottles in front of a warm glow.
box("BarGlow", (3.0, 0.02, 1.4), (3.3, 6.97, 1.85), BACKLIGHT)
for k, z in enumerate((1.25, 1.75, 2.25)):
    box(f"Shelf{k}", (3.0, 0.25, 0.03), (3.3, 6.85, z), DARKWOOD)
    for j in range(12):
        h = rng.uniform(0.22, 0.32)
        cyl(f"Bottle{k}{j}", rng.uniform(0.035, 0.045), h, (2.0 + j * 0.23 + rng.uniform(-0.03, 0.03), 6.85, z + 0.015 + h / 2), rng.choice(BOTTLES), verts=24)
box("BarCounter", (3.2, 0.6, 1.05), (3.3, 6.3, 0.525), PANEL, bevel=0.02)
box("BarTop", (3.3, 0.7, 0.05), (3.3, 6.3, 1.07), material("Marble", (0.85, 0.83, 0.8), 0.12, Coat_Weight=0.6))


# ---------- tables ----------
def tablecloth(name, loc):
    """Round table with a draped linen cloth: vertical folds that grow toward the hem."""
    bm = bmesh.new()
    rings, seg = 10, 128
    top = 0.76
    rows = []
    for k in range(rings + 1):
        t = k / rings
        z = top - t * 0.62
        row = []
        for j in range(seg):
            a = 2 * pi * j / seg
            r = 0.55 + 0.03 * t + t * t * 0.022 * sin(a * 19 + rng.random() * 0.2) + t * 0.01 * sin(a * 7)
            row.append(bm.verts.new((r * cos(a), r * sin(a), z)))
        rows.append(row)
    for k in range(rings):
        for j in range(seg):
            bm.faces.new((rows[k][j], rows[k][(j + 1) % seg], rows[k + 1][(j + 1) % seg], rows[k + 1][j]))
    centre = bm.verts.new((0, 0, top + 0.005))
    for j in range(seg):
        bm.faces.new((centre, rows[0][(j + 1) % seg], rows[0][j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o = mesh_from(name, bm, LINEN)
    o.location = loc
    m = o.modifiers.new("Bevel", "SUBSURF")
    m.levels = m.render_levels = 1
    return o


def chair(name, loc, facing):
    g = bpy.data.objects.new(name, None)
    link(g)
    g.location, g.rotation_euler = loc, (0, 0, facing)
    parts = [box(f"{name}Seat", (0.46, 0.46, 0.09), (0, 0, 0.48), VELVET, bevel=0.03),
             box(f"{name}Back", (0.46, 0.08, 0.55), (0, -0.21, 0.82), VELVET, bevel=0.03, rot=(radians(-8), 0, 0))]
    for dx in (-0.19, 0.19):
        for dy in (-0.19, 0.19):
            parts.append(cyl(f"{name}Leg{dx}{dy}", 0.018, 0.44, (dx, dy, 0.22), DARKWOOD, verts=12))
    for p in parts:
        p.parent = g
        for m in p.modifiers:
            pass
    return g


def place_setting(prefix, centre, angle):
    d = Vector((cos(angle), sin(angle), 0))
    side = Vector((-d.y, d.x, 0))
    p = centre + d * 0.3
    lathe(f"{prefix}Plate", [(0, 0.761), (0.11, 0.761), (0.14, 0.768), (0.145, 0.772), (0.14, 0.774), (0.1, 0.766), (0, 0.766)], CERAMIC, loc=(p.x, p.y, 0))
    lathe(f"{prefix}Glass", [(0, 0.761), (0.035, 0.761), (0.036, 0.764), (0.004, 0.768), (0.004, 0.86), (0.03, 0.88), (0.042, 0.93),
                             (0.038, 0.98), (0.036, 0.98), (0.04, 0.93), (0.028, 0.882), (0.002, 0.866), (0, 0.866)],
          GLASS if prefix.endswith("b") else WINE, loc=(p.x + side.x * 0.17 - d.x * 0.12, p.y + side.y * 0.17 - d.y * 0.12, 0))
    for s, w in ((1, 0.012), (-1, 0.016)):
        c = box(f"{prefix}Cutlery{s}", (0.018 if s > 0 else 0.02, 0.2, 0.004), (p.x + side.x * s * 0.18, p.y + side.y * s * 0.18, 0.765), SILVER)
        c.rotation_euler.z = angle + pi / 2
    n = box(f"{prefix}Napkin", (0.12, 0.08, 0.02), (p.x, p.y, 0.785), LINEN, bevel=0.008)
    n.rotation_euler.z = angle + 0.3


TABLES = [("T6", (1.25, 0.95)), ("T2", (-1.7, 2.6)), ("T3", (1.6, 3.6)), ("T4", (-0.6, 4.8)), ("T5", (-3.4, 4.3)), ("T7", (-3.0, 1.2))]
for name, (x, y) in TABLES:
    tablecloth(f"{name}Cloth", (x, y, 0))
    for k, a in enumerate((0.0, pi)):
        cpos = Vector((x + cos(a) * 0.78, y + sin(a) * 0.78, 0))
        chair(f"{name}Chair{k}", cpos, a + pi / 2)        # chair back (local -y) faces away
        place_setting(f"{name}S{k}{'b' if k else 'a'}", Vector((x, y, 0)), a)
    # Candle in a glass holder, and a bud vase with roses.
    cyl(f"{name}Holder", 0.035, 0.07, (x - 0.06, y - 0.05, 0.795), GLASS, verts=32)
    cyl(f"{name}Candle", 0.02, 0.06, (x - 0.06, y - 0.05, 0.79), WAX, verts=24)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.008, location=(x - 0.06, y - 0.05, 0.835))
    fl = bpy.context.active_object
    fl.scale.z = 2.0
    fl.data.materials.append(FLAME)
    point(f"{name}CandleLight", (x - 0.06, y - 0.05, 0.86), 4.0, (1.0, 0.6, 0.3), 0.01)
    cyl(f"{name}Vase", 0.022, 0.14, (x + 0.08, y + 0.06, 0.83), GLASS, verts=24)
    for r in range(3):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=0.022, location=(x + 0.08 + rng.uniform(-0.03, 0.03), y + 0.06 + rng.uniform(-0.03, 0.03), 0.93 + r * 0.02))
        bpy.context.active_object.data.materials.append(ROSE)
        bpy.ops.object.shade_smooth()
    # Brass pendant with an opal glass globe over each table.
    cyl(f"{name}Cord", 0.004, 1.15, (x, y, 2.88), INK, verts=8)
    cyl(f"{name}Cap", 0.05, 0.06, (x, y, 2.29), BRASS, verts=24)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.13, location=(x, y, 2.14), segments=32, ring_count=16)
    globe = bpy.context.active_object
    globe.data.materials.append(GLOBE)
    bpy.ops.object.shade_smooth()
    point(f"{name}Pendant", (x, y, 1.95), 80, (1.0, 0.7, 0.42), 0.2)

# Table 6 card.
card = box("T6Card", (0.09, 0.004, 0.06), (1.42, 0.78, 0.795), CARD, rot=(radians(-12), 0, radians(20)))
bpy.ops.object.text_add(location=(1.42, 0.776, 0.79), rotation=(radians(90 - 12), 0, radians(20)))
num = bpy.context.active_object
num.data.body = "6"
num.data.size = 0.04
num.data.align_x = "CENTER"
num.data.extrude = 0.0005
num.data.materials.append(INK)

# Soft cool fill from the windows and a very dim warm world.
area = bpy.data.lights.new("WindowFill", "AREA")
area.size, area.size_y, area.energy, area.color = 3, 2, 45, (0.6, 0.72, 1.0)
a = link(bpy.data.objects.new("WindowFill", area))
a.location, a.rotation_euler = (-2.4, 6.7, 2.2), (radians(90), 0, radians(180))
world = bpy.data.worlds.new("World")
scene.world = world
try:
    world.use_nodes = True
except AttributeError:
    pass
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.03, 0.02, 0.015, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.12

# ---------- camera: Table 6 sharp, right of frame; the room soft on the left ----------
focus = link(bpy.data.objects.new("Focus", None))
focus.location = (1.2, 0.95, 0.82)
aim = link(bpy.data.objects.new("Aim", None))
aim.location = (0.45, 2.4, 0.95)
cd = bpy.data.cameras.new("Cam")
cd.lens = 32
cd.dof.use_dof = True
cd.dof.focus_object = focus
cd.dof.aperture_fstop = 2.0
cam = link(bpy.data.objects.new("Cam", cd))
cam.location = (-0.25, -1.9, 1.38)
tc = cam.constraints.new("TRACK_TO")
tc.target, tc.track_axis, tc.up_axis = aim, "TRACK_NEGATIVE_Z", "UP_Y"
scene.camera = cam

# ---------- render ----------
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = 24 if PREVIEW else 160
scene.cycles.use_adaptive_sampling = True
scene.cycles.adaptive_threshold = 0.05 if PREVIEW else 0.015
scene.cycles.use_denoising = True
scene.cycles.max_bounces = 8
scene.cycles.transmission_bounces = 8
scene.cycles.caustics_reflective = scene.cycles.caustics_refractive = False
scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
scene.render.resolution_percentage = 30 if PREVIEW else 85
scene.view_settings.view_transform = "AgX"
try:
    scene.view_settings.look = "AgX - Medium High Contrast"
except TypeError:
    pass
scene.view_settings.exposure = 0.0
scene.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print("RENDER_DONE", OUT)
