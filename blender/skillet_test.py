"""Look-test scene: cast-iron skillet on a butcher-block counter.

Run headless:
  blender --background --factory-startup --python skillet_test.py -- <out.png> <out.blend>
"""
import bpy, bmesh, os, sys
from math import pi, radians, cos, sin

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT_PNG = argv[0] if len(argv) > 0 else "//skillet_test.png"
OUT_BLEND = argv[1] if len(argv) > 1 else None
HDRI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "hdri", "blinds_2k.hdr")
HDRI_ROTATION = radians(float(argv[2])) if len(argv) > 2 else 0.0

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene


# ---------- helpers ----------
def link(obj):
    scene.collection.objects.link(obj)
    return obj


def mesh_obj(name, bm):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    return link(bpy.data.objects.new(name, me))


def lathe(name, profile, steps=128):
    """Spin an (r, z) profile around Z into a smooth solid of revolution."""
    bm = bmesh.new()
    verts = [bm.verts.new((r, 0, z)) for r, z in profile]
    edges = [bm.edges.new((verts[i], verts[i + 1])) for i in range(len(verts) - 1)]
    bmesh.ops.spin(bm, geom=verts + edges, cent=(0, 0, 0), axis=(0, 0, 1),
                   angle=2 * pi, steps=steps, use_duplicate=False)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f in bm.faces:
        f.smooth = True
    return mesh_obj(name, bm)


def subsurf(obj, levels=2):
    m = obj.modifiers.new("Subsurf", "SUBSURF")
    m.levels, m.render_levels = 1, levels
    return m


def material(name):
    mat = bpy.data.materials.new(name)
    try:
        mat.use_nodes = True
    except AttributeError:
        pass
    nt = mat.node_tree
    return mat, nt, nt.nodes["Principled BSDF"]


def node(nt, kind, **props):
    n = nt.nodes.new(kind)
    for k, v in props.items():
        setattr(n, k, v)
    return n


def bump(nt, bsdf, height_socket, strength, distance):
    b = node(nt, "ShaderNodeBump")
    b.inputs["Strength"].default_value = strength
    b.inputs["Distance"].default_value = distance
    nt.links.new(height_socket, b.inputs["Height"])
    nt.links.new(b.outputs["Normal"], bsdf.inputs["Normal"])


def ramp(nt, a, b, pos=(0.0, 1.0)):
    r = node(nt, "ShaderNodeValToRGB")
    els = r.color_ramp.elements
    els[0].position, els[0].color = pos[0], (*a, 1)
    els[1].position, els[1].color = pos[1], (*b, 1)
    return r


# ---------- materials ----------
def cast_iron():
    mat, nt, bsdf = material("CastIron")
    # Seasoning = polymerized oil over iron: dark base under a thin glossy coat.
    bsdf.inputs["Base Color"].default_value = (0.018, 0.017, 0.016, 1)
    bsdf.inputs["Metallic"].default_value = 0.0
    bsdf.inputs["Coat Weight"].default_value = 0.6
    bsdf.inputs["Coat Roughness"].default_value = 0.22
    # Patchy seasoning: roughness varies across the surface.
    patches = node(nt, "ShaderNodeTexNoise")
    patches.inputs["Scale"].default_value = 18
    patches.inputs["Detail"].default_value = 6
    rough = node(nt, "ShaderNodeMapRange")
    rough.inputs["To Min"].default_value = 0.22
    rough.inputs["To Max"].default_value = 0.48
    nt.links.new(patches.outputs["Fac"], rough.inputs["Value"])
    nt.links.new(rough.outputs["Result"], bsdf.inputs["Roughness"])
    # Fine sand-cast grain.
    grain = node(nt, "ShaderNodeTexNoise")
    grain.inputs["Scale"].default_value = 900
    grain.inputs["Detail"].default_value = 4
    bump(nt, bsdf, grain.outputs["Fac"], 0.25, 0.0004)
    return mat


def butcher_block():
    mat, nt, bsdf = material("ButcherBlock")
    coord = node(nt, "ShaderNodeTexCoord")
    # Butcher block = long strips glued side by side; each strip gets its own tone.
    strips = node(nt, "ShaderNodeTexBrick")
    strips.inputs["Scale"].default_value = 1.0
    strips.inputs["Brick Width"].default_value = 0.9
    strips.inputs["Row Height"].default_value = 0.045
    strips.inputs["Mortar Size"].default_value = 0.0006
    strips.inputs["Bias"].default_value = 0.0
    strips.inputs["Color1"].default_value = (1.0, 1.0, 1.0, 1)
    strips.inputs["Color2"].default_value = (0.55, 0.55, 0.55, 1)
    strips.inputs["Mortar"].default_value = (0.25, 0.25, 0.25, 1)
    strips.offset = 0.37
    nt.links.new(coord.outputs["Object"], strips.inputs["Vector"])
    # Grain: wave bands running along X, stretched and warped.
    mapping = node(nt, "ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (0.15, 1, 1)
    nt.links.new(coord.outputs["Object"], mapping.inputs["Vector"])
    wave = node(nt, "ShaderNodeTexWave")
    wave.wave_type = "BANDS"
    wave.bands_direction = "Y"
    wave.inputs["Scale"].default_value = 14
    wave.inputs["Distortion"].default_value = 11
    wave.inputs["Detail"].default_value = 3
    wave.inputs["Detail Scale"].default_value = 1.4
    nt.links.new(mapping.outputs["Vector"], wave.inputs["Vector"])
    col = ramp(nt, (0.2, 0.1, 0.045), (0.36, 0.2, 0.095), (0.1, 0.9))
    nt.links.new(wave.outputs["Fac"], col.inputs["Fac"])
    tone = node(nt, "ShaderNodeMix", data_type="RGBA", blend_type="MULTIPLY")
    tone.inputs["Factor"].default_value = 1.0
    nt.links.new(col.outputs["Color"], tone.inputs["A"])
    nt.links.new(strips.outputs["Color"], tone.inputs["B"])
    nt.links.new(tone.outputs["Result"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.38
    height = node(nt, "ShaderNodeMath", operation="SUBTRACT")  # glue seams sink in
    nt.links.new(wave.outputs["Fac"], height.inputs[0])
    nt.links.new(strips.outputs["Fac"], height.inputs[1])
    bump(nt, bsdf, height.outputs["Value"], 0.12, 0.002)
    return mat


def subway_tile():
    mat, nt, bsdf = material("SubwayTile")
    coord = node(nt, "ShaderNodeTexCoord")
    brick = node(nt, "ShaderNodeTexBrick")
    brick.inputs["Color1"].default_value = (0.86, 0.86, 0.83, 1)
    brick.inputs["Color2"].default_value = (0.82, 0.83, 0.8, 1)
    brick.inputs["Mortar"].default_value = (0.42, 0.41, 0.39, 1)
    brick.inputs["Scale"].default_value = 6
    brick.inputs["Mortar Size"].default_value = 0.012
    brick.inputs["Brick Width"].default_value = 1.0
    brick.inputs["Row Height"].default_value = 0.5
    nt.links.new(coord.outputs["Object"], brick.inputs["Vector"])
    nt.links.new(brick.outputs["Color"], bsdf.inputs["Base Color"])
    rough = node(nt, "ShaderNodeMapRange")
    rough.inputs["To Min"].default_value = 0.08
    rough.inputs["To Max"].default_value = 0.85
    nt.links.new(brick.outputs["Fac"], rough.inputs["Value"])
    nt.links.new(rough.outputs["Result"], bsdf.inputs["Roughness"])
    bump(nt, bsdf, brick.outputs["Fac"], 0.4, 0.002)
    return mat


def eggshell():
    mat, nt, bsdf = material("Eggshell")
    bsdf.inputs["Base Color"].default_value = (0.74, 0.5, 0.31, 1)
    bsdf.inputs["Roughness"].default_value = 0.55
    bsdf.inputs["Subsurface Weight"].default_value = 0.15
    bsdf.inputs["Subsurface Scale"].default_value = 0.004
    speck = node(nt, "ShaderNodeTexNoise")
    speck.inputs["Scale"].default_value = 1400
    bump(nt, bsdf, speck.outputs["Fac"], 0.15, 0.0002)
    return mat


def yolk():
    mat, nt, bsdf = material("Yolk")
    bsdf.inputs["Base Color"].default_value = (0.95, 0.3, 0.008, 1)
    bsdf.inputs["Roughness"].default_value = 0.12
    bsdf.inputs["Coat Weight"].default_value = 1.0
    bsdf.inputs["Coat Roughness"].default_value = 0.03
    bsdf.inputs["Subsurface Weight"].default_value = 0.25
    bsdf.inputs["Subsurface Radius"].default_value = (1.0, 0.3, 0.05)
    bsdf.inputs["Subsurface Scale"].default_value = 0.006
    return mat


def ceramic():
    mat, nt, bsdf = material("Ceramic")
    bsdf.inputs["Base Color"].default_value = (0.9, 0.89, 0.85, 1)
    bsdf.inputs["Roughness"].default_value = 0.2
    bsdf.inputs["Coat Weight"].default_value = 0.6
    bsdf.inputs["Coat Roughness"].default_value = 0.05
    return mat


IRON, WOOD, TILE, SHELL, YOLK, CERAMIC = (
    cast_iron(), butcher_block(), subway_tile(), eggshell(), yolk(), ceramic())


# ---------- geometry ----------
def plane(name, size, loc, rot, mat):
    bpy.ops.mesh.primitive_plane_add(size=1, location=loc, rotation=rot)
    o = bpy.context.active_object
    o.name = name
    o.scale = (*size, 1)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)  # texture coords in meters
    o.data.materials.append(mat)
    return o


plane("Counter", (2.4, 1.6), (0, 0.1, 0), (0, 0, 0), WOOD)
plane("Backsplash", (2.4, 1.2), (0, 0.55, 0.6), (radians(90), 0, 0), TILE)

# Skillet body (meters): ~27 cm across, 5 cm deep, ~6 mm walls.
pan = lathe("Skillet", [
    (0.0, 0.006), (0.104, 0.006), (0.112, 0.0075), (0.117, 0.012),
    (0.127, 0.045), (0.1295, 0.0495), (0.1325, 0.0515), (0.1355, 0.0505),
    (0.1375, 0.047), (0.1265, 0.011), (0.122, 0.004), (0.116, 0.001),
    (0.109, 0.0), (0.0, 0.0),
])
pan.data.materials.append(IRON)
subsurf(pan)

# Main handle: a swept cross-section along a gently rising path, flaring where it
# meets the pan and rounding off at the tip (built as rings, so no booleans).
bm = bmesh.new()
rings, ring_n = 24, 16
length = 0.165
prev = None
for i in range(rings + 1):
    t = i / rings
    x = 0.128 + t * length
    z = 0.042 + 0.018 * t * t                        # slight upward sweep
    flare = max(0.0, 1 - t / 0.18) ** 2              # widens into the wall
    tip = max(0.0, (t - 0.88) / 0.12)                # rounds off the end
    w = (0.013 + 0.004 * t + 0.012 * flare) * (1 - 0.55 * tip ** 2) ** 0.5
    h = (0.0085 - 0.0015 * t + 0.004 * flare) * (1 - 0.55 * tip ** 2) ** 0.5
    ring = []
    for k in range(ring_n):
        a = 2 * pi * k / ring_n
        # Superellipse: flat top/bottom with rounded edges, like cast iron.
        cy, cz = cos(a), sin(a)
        sy = (abs(cy) ** 0.6) * (1 if cy >= 0 else -1)
        sz = (abs(cz) ** 0.6) * (1 if cz >= 0 else -1)
        ring.append(bm.verts.new((x, w * sy, z + h * sz)))
    if prev:
        for k in range(ring_n):
            bm.faces.new((prev[k], prev[(k + 1) % ring_n], ring[(k + 1) % ring_n], ring[k]))
    prev = ring
bm.faces.new(list(reversed(prev)))                   # cap the tip
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
for f in bm.faces:
    f.smooth = True
handle = mesh_obj("Handle", bm)
handle.data.materials.append(IRON)
subsurf(handle)

# Helper handle: a flattened half-moon lip opposite the main handle.
bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=0.021, depth=0.008, location=(-0.152, 0, 0.046))
lip = bpy.context.active_object
lip.name = "HelperHandle"
lip.scale.y = 1.7
lip.data.materials.append(IRON)
b2 = lip.modifiers.new("Bevel", "BEVEL")
b2.width, b2.segments = 0.003, 3
subsurf(lip)
bpy.ops.object.shade_smooth()

# Eggs, lying on the counter.
for i, (loc, rz) in enumerate([((0.21, 0.22, 0.021), 20), ((0.27, 0.15, 0.021), -35)]):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=1, location=loc)
    egg = bpy.context.active_object
    egg.name = f"Egg{i}"
    for v in egg.data.vertices:
        x = v.co.x
        taper = 1 - 0.12 * x               # pointier at +x
        v.co.x *= 0.029
        v.co.y *= 0.021 * taper
        v.co.z *= 0.021 * taper
    egg.rotation_euler = (0, 0, radians(rz))
    egg.data.materials.append(SHELL)
    bpy.ops.object.shade_smooth()

# Ceramic bowl with yolks.
bowl = lathe("Bowl", [
    (0.0, 0.007), (0.035, 0.008), (0.054, 0.018), (0.066, 0.036),
    (0.07, 0.052), (0.0725, 0.0545), (0.0745, 0.053), (0.072, 0.034),
    (0.059, 0.012), (0.042, 0.002), (0.038, 0.0), (0.0, 0.0),
], steps=96)
bowl.location = (-0.24, 0.21, 0)
bowl.data.materials.append(CERAMIC)
subsurf(bowl)
for dx, dy in [(-0.012, 0.006), (0.014, 0.01), (0.002, -0.014)]:
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=0.0145,
                                         location=(-0.24 + dx, 0.21 + dy, 0.016))
    y = bpy.context.active_object
    y.scale.z = 0.62
    y.data.materials.append(YOLK)
    bpy.ops.object.shade_smooth()


# ---------- lighting ----------
def area(name, loc, size, energy, color, target):
    data = bpy.data.lights.new(name, "AREA")
    data.shape = "RECTANGLE"
    data.size, data.size_y = size
    data.energy, data.color = energy, color
    o = link(bpy.data.objects.new(name, data))
    o.location = loc
    c = o.constraints.new("TRACK_TO")
    c.target, c.track_axis, c.up_axis = target, "TRACK_NEGATIVE_Z", "UP_Y"
    return o


focus = link(bpy.data.objects.new("Focus", None))
focus.location = (0, 0.05, 0.02)
area("Window", (-0.9, -0.15, 0.85), (1.0, 0.6), 45, (1.0, 0.93, 0.84), focus)
area("Rim", (0.5, 0.75, 0.55), (0.4, 0.3), 30, (0.9, 0.95, 1.0), focus)
area("Fill", (0.6, -0.9, 0.5), (1.2, 1.2), 0, (1.0, 0.97, 0.93), focus)

world = bpy.data.worlds.new("World")
scene.world = world
try:
    world.use_nodes = True
except AttributeError:
    pass
wnt = world.node_tree
bg = wnt.nodes["Background"]
bg.inputs["Strength"].default_value = 0.7
# HDRI room: soft fill light plus the reflections that make metal read as metal.
env = wnt.nodes.new("ShaderNodeTexEnvironment")
env.image = bpy.data.images.load(HDRI)
wmap = wnt.nodes.new("ShaderNodeMapping")
wmap.inputs["Rotation"].default_value = (0, 0, HDRI_ROTATION)
wnt.links.new(wnt.nodes.new("ShaderNodeTexCoord").outputs["Generated"], wmap.inputs["Vector"])
wnt.links.new(wmap.outputs["Vector"], env.inputs["Vector"])
wnt.links.new(env.outputs["Color"], bg.inputs["Color"])

# ---------- camera ----------
cam_data = bpy.data.cameras.new("Camera")
cam_data.lens = 42
cam_data.dof.use_dof = True
cam_data.dof.focus_object = focus
cam_data.dof.aperture_fstop = 4.0
cam = link(bpy.data.objects.new("Camera", cam_data))
cam.location = (0.3, -0.52, 0.6)
tc = cam.constraints.new("TRACK_TO")
tc.target, tc.track_axis, tc.up_axis = focus, "TRACK_NEGATIVE_Z", "UP_Y"
scene.camera = cam

# ---------- render ----------
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = 96
scene.cycles.use_adaptive_sampling = True
scene.cycles.adaptive_threshold = 0.03
scene.cycles.use_denoising = True
scene.cycles.max_bounces = 6
scene.render.resolution_x, scene.render.resolution_y = 1280, 720
scene.render.filepath = OUT_PNG
scene.view_settings.view_transform = "AgX"
scene.view_settings.exposure = -0.3
try:
    scene.view_settings.look = "AgX - Medium High Contrast"
except TypeError:
    pass

# Other scripts (e.g. food_test.py) reuse this file as a base scene.
if os.environ.get("SCENE_ONLY") != "1":
    if OUT_BLEND:
        bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
    bpy.ops.render.render(write_still=True)
    print("RENDER_DONE", OUT_PNG)
