"""Food look-test: carbonara in the skillet (spaghetti, clinging sauce, guanciale, pepper, pecorino).

Builds on skillet_test.py's scene. Run headless:
  blender --background --factory-startup --python food_test.py -- <out.png> <out.blend> <hdri_rot_deg>
Set QUICK=1 in the environment for a fast low-res preview.
"""
import bpy, bmesh, os, random, sys
import numpy as np
from math import pi, cos, sin, atan2, hypot
from mathutils import Matrix, Vector, noise

HERE = os.path.dirname(os.path.abspath(__file__))
os.environ["SCENE_ONLY"] = "1"
base = os.path.join(HERE, "skillet_test.py")
exec(compile(open(base).read(), base, "exec"), {"__file__": base, "__name__": "base_scene"})

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT_PNG = argv[0] if len(argv) > 0 else "//food_test.png"
OUT_BLEND = argv[1] if len(argv) > 1 and argv[1] != "-" else None
QUICK = os.environ.get("QUICK") == "1"

scene = bpy.context.scene
rng = random.Random(4)

PAN_FLOOR = 0.006       # top of the skillet's cooking surface
PILE_R = 0.108          # how far the food spreads
STRAND_R = 0.0011       # ~2.2 mm cooked spaghetti
COAT = 0.00045          # sauce film thickness over a lone strand


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


def set_inputs(bsdf, **values):
    for k, v in values.items():
        bsdf.inputs[k.replace("_", " ")].default_value = v


# ---------- materials ----------
def pasta_mat():
    # Cooked durum-wheat pasta is slightly translucent; the sauce skin supplies the gloss.
    mat, nt, bsdf = material("Spaghetti")
    set_inputs(bsdf, Roughness=0.4, Subsurface_Weight=0.25, Subsurface_Radius=(1.0, 0.6, 0.25),
               Subsurface_Scale=0.001)
    n = node(nt, "ShaderNodeTexNoise")
    n.inputs["Scale"].default_value = 90
    mix = node(nt, "ShaderNodeMix", data_type="RGBA")
    mix.inputs["A"].default_value = (0.84, 0.58, 0.23, 1)
    mix.inputs["B"].default_value = (0.9, 0.68, 0.3, 1)
    nt.links.new(n.outputs["Fac"], mix.inputs["Factor"])
    nt.links.new(mix.outputs["Result"], bsdf.inputs["Base Color"])
    return mat


def sauce_skin_mat():
    """Thin emulsion of yolk, pecorino and pasta water: glossy, creamy, partly see-through."""
    mat, nt, bsdf = material("SauceSkin")
    # The skin hides the pasta, so its colour is "sauce-coated pasta": golden, with
    # paler creamy patches where the emulsion sits thicker.
    set_inputs(bsdf, Roughness=0.12, Subsurface_Weight=0.35, Subsurface_Radius=(1.0, 0.65, 0.3),
               Subsurface_Scale=0.0012, Coat_Weight=0.6, Coat_Roughness=0.05)
    n = node(nt, "ShaderNodeTexNoise")
    n.inputs["Scale"].default_value = 140
    n.inputs["Detail"].default_value = 3
    m = node(nt, "ShaderNodeMapRange")
    m.inputs["From Min"].default_value = 0.45
    m.inputs["From Max"].default_value = 0.7
    nt.links.new(n.outputs["Fac"], m.inputs["Value"])
    mix = node(nt, "ShaderNodeMix", data_type="RGBA")
    mix.inputs["A"].default_value = (0.82, 0.55, 0.2, 1)
    mix.inputs["B"].default_value = (0.95, 0.78, 0.45, 1)
    nt.links.new(m.outputs["Result"], mix.inputs["Factor"])
    nt.links.new(mix.outputs["Result"], bsdf.inputs["Base Color"])
    return mat


def sauce_pool_mat():
    mat, nt, bsdf = material("SaucePool")
    set_inputs(bsdf, Base_Color=(0.92, 0.64, 0.24, 1), Roughness=0.1,
               Subsurface_Weight=0.4, Subsurface_Radius=(1.0, 0.75, 0.4), Subsurface_Scale=0.003,
               Coat_Weight=0.5, Coat_Roughness=0.04)
    return mat


def guanciale_mat():
    """Layers of translucent rendered fat and dark cured meat, crisped at random."""
    mat, nt, bsdf = material("Guanciale")
    coord = node(nt, "ShaderNodeTexCoord")
    info = node(nt, "ShaderNodeObjectInfo")
    mapping = node(nt, "ShaderNodeMapping")
    nt.links.new(coord.outputs["Object"], mapping.inputs["Vector"])
    nt.links.new(info.outputs["Random"], mapping.inputs["Location"])
    wave = node(nt, "ShaderNodeTexWave")
    wave.bands_direction = "Z"
    wave.inputs["Scale"].default_value = 55
    wave.inputs["Distortion"].default_value = 9
    wave.inputs["Detail"].default_value = 4
    nt.links.new(mapping.outputs["Vector"], wave.inputs["Vector"])
    layers = node(nt, "ShaderNodeValToRGB")
    els = layers.color_ramp.elements
    els[0].position, els[0].color = 0.55, (0, 0, 0, 1)    # more meat than fat
    els[1].position, els[1].color = 0.68, (1, 1, 1, 1)
    nt.links.new(wave.outputs["Fac"], layers.inputs["Fac"])
    tissue = node(nt, "ShaderNodeMix", data_type="RGBA")
    tissue.inputs["A"].default_value = (0.34, 0.09, 0.035, 1)   # cured meat
    tissue.inputs["B"].default_value = (0.8, 0.5, 0.2, 1)       # rendered fat, turned golden
    nt.links.new(layers.outputs["Color"], tissue.inputs["Factor"])
    browning = node(nt, "ShaderNodeTexNoise")
    browning.inputs["Scale"].default_value = 180
    browning.inputs["Detail"].default_value = 8
    browning.inputs["Roughness"].default_value = 0.65
    nt.links.new(mapping.outputs["Vector"], browning.inputs["Vector"])
    brown_mask = node(nt, "ShaderNodeMapRange")
    brown_mask.inputs["From Min"].default_value = 0.2
    brown_mask.inputs["From Max"].default_value = 0.75
    nt.links.new(browning.outputs["Fac"], brown_mask.inputs["Value"])
    crisp = node(nt, "ShaderNodeMix", data_type="RGBA", blend_type="MULTIPLY")
    crisp.inputs["B"].default_value = (0.3, 0.12, 0.04, 1)
    nt.links.new(brown_mask.outputs["Result"], crisp.inputs["Factor"])
    nt.links.new(tissue.outputs["Result"], crisp.inputs["A"])
    nt.links.new(crisp.outputs["Result"], bsdf.inputs["Base Color"])
    # Fat glistens, crisped meat is matte.
    rough = node(nt, "ShaderNodeMath", operation="MULTIPLY_ADD")
    nt.links.new(brown_mask.outputs["Result"], rough.inputs[0])
    rough.inputs[1].default_value = 0.35
    rough.inputs[2].default_value = 0.22
    nt.links.new(rough.outputs["Value"], bsdf.inputs["Roughness"])
    set_inputs(bsdf, Subsurface_Weight=0.15, Subsurface_Radius=(1.0, 0.5, 0.25), Subsurface_Scale=0.0015)
    bump = node(nt, "ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.6
    bump.inputs["Distance"].default_value = 0.0005
    nt.links.new(browning.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def simple_mat(name, color, rough, sss=0.0):
    mat, nt, bsdf = material(name)
    set_inputs(bsdf, Base_Color=(*color, 1), Roughness=rough, Subsurface_Weight=sss, Subsurface_Scale=0.001)
    return mat


PASTA, SKIN, POOL, GUANCIALE = pasta_mat(), sauce_skin_mat(), sauce_pool_mat(), guanciale_mat()
PEPPER = simple_mat("BlackPepper", (0.022, 0.015, 0.01), 0.5)
PECORINO = simple_mat("Pecorino", (0.9, 0.82, 0.6), 0.5, sss=0.3)


def link_obj(name, data):
    o = bpy.data.objects.new(name, data)
    scene.collection.objects.link(o)
    return o


# ---------- sauce pooled on the pan floor ----------
bm = bmesh.new()
bmesh.ops.create_circle(bm, cap_ends=True, radius=0.114, segments=96)
bmesh.ops.triangulate(bm, faces=bm.faces)
for _ in range(3):
    bmesh.ops.subdivide_edges(bm, edges=bm.edges, cuts=1, use_grid_fill=True)
for v in bm.verts:
    v.co.z = PAN_FLOOR + 0.0025 + 0.0015 * noise.noise(v.co * 60)
for f in bm.faces:
    f.smooth = True
me = bpy.data.meshes.new("SaucePool")
bm.to_mesh(me)
bm.free()
link_obj("SaucePool", me).data.materials.append(POOL)

# ---------- spaghetti: bundles dropped one by one onto a growing height map ----------
# A cheap stand-in for physics: each strand settles on whatever is already in the
# pan, bridges over bumps, sags into gaps (limited by bending stiffness), and then
# raises the height map so later strands pile on top of it.
CELL = 0.0015
GRID = int(0.25 / CELL)
height = np.full((GRID, GRID), PAN_FLOOR, dtype=np.float32)


def cell(x, y):
    return (min(GRID - 1, max(0, int((x + 0.125) / CELL))),
            min(GRID - 1, max(0, int((y + 0.125) / CELL))))


def support(x, y):
    i, j = cell(x, y)
    return float(height[i, j])


def top(x, y):
    """Top of the food surface at (x, y), once the pile is built."""
    return support(x, y)


def settle(pts):
    """Lay a strand on the current pile; returns the settled points and stamps it in."""
    s = [support(p.x, p.y) + STRAND_R for p in pts]
    z = list(s)
    for _ in range(40):                                # stiffness: bridge, then sag a little
        for i in range(1, len(z) - 1):
            z[i] = max(s[i], 0.5 * (z[i - 1] + z[i + 1]) - 0.0008)
    # Iron out the zigzag from climbing over single strands; a little overlap is
    # hidden by the sauce skin.
    for _ in range(4):
        z = [z[0]] + [max(s[i] - 0.7 * STRAND_R, (z[i - 1] + 2 * z[i] + z[i + 1]) / 4)
                      for i in range(1, len(z) - 1)] + [z[-1]]
    out = [Vector((p.x, p.y, zi)) for p, zi in zip(pts, z)]
    for a, b in zip(out, out[1:]):
        for t in (0.0, 0.5):
            q = a.lerp(b, t)
            i, j = cell(q.x, q.y)
            for di, dj in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
                ii, jj = min(GRID - 1, max(0, i + di)), min(GRID - 1, max(0, j + dj))
                height[ii, jj] = max(height[ii, jj], q.z + STRAND_R)
    return out


STEP = 0.004
strands = []                                           # list of point lists
n_bundles = 60 if QUICK else 95
for b in range(n_bundles):
    # Tossing spreads pasta out: start each bundle at the lowest of a few candidate spots.
    best = None
    for _ in range(6):
        a = rng.uniform(0, 2 * pi)
        r0 = PILE_R * 0.85 * rng.random() ** 0.9
        c0 = (r0 * cos(a), r0 * sin(a))
        h0 = support(*c0) + 0.012 * (r0 / PILE_R) ** 2      # mild bias toward the centre
        if best is None or h0 < best[0]:
            best = (h0, c0)
    p = Vector((best[1][0], best[1][1], 0))
    heading = rng.uniform(0, 2 * pi)
    turn = rng.uniform(-0.1, 0.1)
    path = []
    for i in range(rng.randint(60, 85)):
        # Persistent turning makes the loose loops and S-bends of cooked spaghetti.
        turn = 0.93 * turn + rng.uniform(-0.06, 0.06)
        heading += turn
        p.x += STEP * cos(heading)
        p.y += STEP * sin(heading)
        r = hypot(p.x, p.y)
        if r > PILE_R:                                 # pan wall: steer back inside
            heading = atan2(-p.y, -p.x) + rng.uniform(-0.9, 0.9)
            p.x, p.y = p.x * PILE_R / r, p.y * PILE_R / r
        path.append((Vector((p.x, p.y, 0)), heading))
    count = rng.choice([1, 1, 2, 2, 2, 3])
    twist0, twist_rate = rng.uniform(0, 2 * pi), rng.choice([-1, 1]) * rng.uniform(0.06, 0.16)
    for k in range(count):
        ring = 2.15 * STRAND_R * (k - (count - 1) / 2)
        pts = []
        for i, (c, hd) in enumerate(path):
            side = Vector((-sin(hd), cos(hd), 0))
            pts.append(c + side * ring * cos(twist0 + twist_rate * i))   # strands swap sides = twist
        cut = rng.randint(0, 10)                       # stagger strand ends
        strands.append(settle(pts[cut:len(pts) - rng.randint(0, 10)]))
print("PILE_PEAK_MM", round((float(height.max()) - PAN_FLOOR) * 1000, 1))

curve = bpy.data.curves.new("Spaghetti", "CURVE")
curve.dimensions = "3D"
curve.bevel_depth = STRAND_R
curve.bevel_resolution = 2
curve.resolution_u = 3
curve.use_fill_caps = True
for pts in strands:
    sp = curve.splines.new("NURBS")
    sp.points.add(len(pts) - 1)
    for pt, co in zip(sp.points, pts):
        pt.co = (*co, 1)
    sp.order_u = 4
    sp.use_endpoint_u = True
link_obj("Spaghetti", curve).data.materials.append(PASTA)

# ---------- sauce skin: union of spheres along every strand, meshed from a volume ----------
# Where strands lie close, the inflated volumes merge, so the sauce bridges between them.
skin_pts, skin_rad = [], []
for pts in strands:
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        n = max(1, int((b - a).length / 0.0008))
        for j in range(n):
            skin_pts.append(a.lerp(b, j / n))
            # Mostly a thin film, with occasional creamy beads.
            bead = max(0.0, noise.noise(skin_pts[-1] * 260)) ** 3
            skin_rad.append(STRAND_R + COAT + 0.0014 * bead)
me = bpy.data.meshes.new("SauceSeeds")
me.from_pydata([tuple(p) for p in skin_pts], [], [])
attr = me.attributes.new("radius", "FLOAT", "POINT")
attr.data.foreach_set("value", skin_rad)
skin = link_obj("SauceSkin", me)

gn = bpy.data.node_groups.new("SauceSkinGN", "GeometryNodeTree")
gn.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
gn.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
gi, go = gn.nodes.new("NodeGroupInput"), gn.nodes.new("NodeGroupOutput")
to_pts = gn.nodes.new("GeometryNodeMeshToPoints")
rad = gn.nodes.new("GeometryNodeInputNamedAttribute")
rad.data_type = "FLOAT"
rad.inputs["Name"].default_value = "radius"
to_vol = gn.nodes.new("GeometryNodePointsToVolume")
to_vol.inputs["Resolution Mode"].default_value = "Size"
to_vol.inputs["Voxel Size"].default_value = 0.0006 if QUICK else 0.00032
to_vol.inputs["Density"].default_value = 1.0
to_mesh = gn.nodes.new("GeometryNodeVolumeToMesh")
to_mesh.inputs["Threshold"].default_value = 0.5
smooth = gn.nodes.new("GeometryNodeSetShadeSmooth")
gn.links.new(gi.outputs[0], to_pts.inputs["Mesh"])
gn.links.new(rad.outputs["Attribute"], to_pts.inputs["Radius"])
gn.links.new(to_pts.outputs["Points"], to_vol.inputs["Points"])
gn.links.new(rad.outputs["Attribute"], to_vol.inputs["Radius"])
gn.links.new(to_vol.outputs["Volume"], to_mesh.inputs["Volume"])
gn.links.new(to_mesh.outputs["Mesh"], smooth.inputs["Geometry"])
set_mat = gn.nodes.new("GeometryNodeSetMaterial")          # new geometry has no material slot
set_mat.inputs["Material"].default_value = SKIN
gn.links.new(smooth.outputs["Geometry"], set_mat.inputs["Geometry"])
gn.links.new(set_mat.outputs["Geometry"], go.inputs[0])
mod = skin.modifiers.new("SauceSkin", "NODES")
mod.node_group = gn
sm = skin.modifiers.new("Smooth", "SMOOTH")                  # rounds the bead-chain bumps
sm.factor, sm.iterations = 0.6, 6
skin.data.materials.append(SKIN)

# ---------- guanciale lardons: irregular, some half-buried ----------
lardon_tex = bpy.data.textures.new("LardonNoise", "CLOUDS")
lardon_tex.noise_scale = 0.004
for i in range(20):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    dims = (rng.uniform(0.013, 0.02), rng.uniform(0.008, 0.012), rng.uniform(0.006, 0.009))
    skew = rng.uniform(-0.25, 0.25)
    for v in bm.verts:
        x, y, z = v.co
        taper = 1 + skew * x                           # pieces are rarely true cuboids
        v.co = Vector((x * dims[0], y * dims[1] * taper, z * dims[2] * taper))
    me = bpy.data.meshes.new(f"Guanciale{i}")
    bm.to_mesh(me)
    bm.free()
    o = link_obj(f"Guanciale{i}", me)
    a, r = rng.uniform(0, 2 * pi), PILE_R * 0.92 * rng.random() ** 0.7
    x, y = r * cos(a), r * sin(a)
    o.location = (x, y, top(x, y) + rng.uniform(-0.004, 0.0))   # some sit proud, some nestle in
    o.rotation_euler = (rng.uniform(-0.6, 0.6), rng.uniform(-0.6, 0.6), rng.uniform(0, pi))
    o.data.materials.append(GUANCIALE)
    bev = o.modifiers.new("Bevel", "BEVEL")
    bev.width, bev.segments = 0.0012, 2
    sub = o.modifiers.new("Subsurf", "SUBSURF")
    sub.levels, sub.render_levels = 2, 3
    disp = o.modifiers.new("Displace", "DISPLACE")
    disp.texture, disp.strength, disp.mid_level = lardon_tex, 0.0018, 0.5
    disp.texture_coords = "GLOBAL"                     # every piece gets a different lumpiness
    for poly in me.polygons:
        poly.use_smooth = True


# ---------- scattered toppings (one mesh each, for speed) ----------
def scatter(name, mat, count, make, spread=0.55):
    bm = bmesh.new()
    for _ in range(count):
        a, r = rng.uniform(0, 2 * pi), PILE_R * rng.random() ** spread
        x, y = r * cos(a), r * sin(a)
        loc = Vector((x, y, top(x, y) + STRAND_R * 0.5 + rng.uniform(-0.0012, 0.0004)))
        rot = Matrix.Rotation(rng.uniform(0, pi), 4, Vector((rng.random(), rng.random(), rng.random())).normalized())
        make(bm, Matrix.Translation(loc) @ rot)
    for f in bm.faces:
        f.smooth = True
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    link_obj(name, me).data.materials.append(mat)


scatter("Pepper", PEPPER, 320, lambda bm, m: bmesh.ops.create_icosphere(
    bm, subdivisions=0, radius=1.0, matrix=m @ Matrix.Diagonal(
        (rng.uniform(0.0005, 0.0015), rng.uniform(0.0004, 0.001), rng.uniform(0.0002, 0.0006), 1))))
# Finely grated pecorino: tiny crumbs, concentrated near the top of the pile.
scatter("Pecorino", PECORINO, 280, lambda bm, m: bmesh.ops.create_icosphere(
    bm, subdivisions=1, radius=1.0, matrix=m @ Matrix.Diagonal(
        (rng.uniform(0.0003, 0.0008), rng.uniform(0.0002, 0.0005), rng.uniform(0.00015, 0.0003), 1))), spread=0.8)

# ---------- food-photo camera: closer, shallower focus ----------
focus = bpy.data.objects["Focus"]
focus.location = (0.0, 0.0, 0.04)
cam = bpy.data.objects["Camera"]
cam.location = (0.13, -0.3, 0.21)
cam.data.lens = 55
cam.data.dof.aperture_fstop = 3.2
back = bpy.data.lights.new("Backlight", "AREA")
back.size, back.energy, back.color = 0.25, 18, (1.0, 0.95, 0.88)
back_obj = bpy.data.objects.new("Backlight", back)
scene.collection.objects.link(back_obj)
back_obj.location = (-0.12, 0.42, 0.3)
tc = back_obj.constraints.new("TRACK_TO")
tc.target, tc.track_axis, tc.up_axis = focus, "TRACK_NEGATIVE_Z", "UP_Y"
iron = bpy.data.materials["CastIron"].node_tree.nodes["Principled BSDF"]
iron.inputs["Coat Weight"].default_value = 0.35            # less grey sheen at this close angle
scene.view_settings.exposure = -0.7
scene.cycles.samples = 32 if QUICK else 160
if QUICK:
    scene.render.resolution_percentage = 50

scene.render.filepath = OUT_PNG
if OUT_BLEND:
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
dg = bpy.context.evaluated_depsgraph_get()
skin_eval = skin.evaluated_get(dg)
print("SKIN_POLYS", len(skin_eval.data.polygons), "SEEDS", len(skin_pts), "STRANDS", len(strands))
bpy.ops.render.render(write_still=True)
print("RENDER_DONE", OUT_PNG)
