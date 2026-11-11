"""Studio product shots for the ingredient and tool cards (web/assets/items/<ID>.png).

Every item is modelled in code at real-world scale, placed on the same warm seamless
backdrop under the same three lights, and framed automatically from its bounding box.
  blender --background --factory-startup --python item_cards.py -- <out_dir> [ID ID ...]
"""
import bpy, bmesh, os, sys, random
from math import pi, cos, sin, radians, tan, atan2
from mathutils import Vector, Matrix

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0] if argv else os.path.join(os.path.dirname(__file__), "..", "web", "assets", "items")
ONLY = set(argv[1:])
os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
rng = random.Random(3)


# ---------- helpers ----------
def material(name, color=(0.8, 0.8, 0.8), rough=0.5, metal=0.0, **extra):
    m = bpy.data.materials.get(name)
    if m:
        return m
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


def noisy(name, base, rough, scale, strength, metal=0.0, **extra):
    """A material with a fine bump so surfaces don't read as plastic."""
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = material(name, base, rough, metal, **extra)
    nt = m.node_tree
    n = nt.nodes.new("ShaderNodeTexNoise")
    n.inputs["Scale"].default_value = scale
    n.inputs["Detail"].default_value = 6
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = strength
    bump.inputs["Distance"].default_value = 0.001
    nt.links.new(n.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], nt.nodes["Principled BSDF"].inputs["Normal"])
    return m


ITEM = None   # collection for the current item


def keep(o):
    for c in o.users_collection:
        c.objects.unlink(o)
    ITEM.objects.link(o)
    return o


def finish(o, mat=None, smooth=True, bevel=0.0, sub=0):
    if mat:
        o.data.materials.clear()
        o.data.materials.append(mat)
    if smooth and o.type == "MESH":
        for p in o.data.polygons:
            p.use_smooth = True
    if bevel:
        m = o.modifiers.new("Bevel", "BEVEL")
        m.width, m.segments = bevel, 3
    if sub:
        m = o.modifiers.new("Sub", "SUBSURF")
        m.levels = m.render_levels = sub
    return keep(o)


def from_bm(name, bm, mat=None, **kw):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    scene.collection.objects.link(o)
    return finish(o, mat, **kw)


def box(name, size, loc, mat, bevel=0.0, rot=(0, 0, 0), sub=0):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1)
    for v in bm.verts:
        v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2]))
    o = from_bm(name, bm, mat, smooth=bool(bevel or sub), bevel=bevel, sub=sub)
    o.location, o.rotation_euler = loc, rot
    return o


def lathe(name, prof, mat, loc=(0, 0, 0), rot=(0, 0, 0), steps=64, sub=0):
    bm = bmesh.new()
    vs = [bm.verts.new((r, 0, z)) for r, z in prof]
    es = [bm.edges.new((vs[i], vs[i + 1])) for i in range(len(vs) - 1)]
    bmesh.ops.spin(bm, geom=vs + es, cent=(0, 0, 0), axis=(0, 0, 1), angle=2 * pi, steps=steps)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o = from_bm(name, bm, mat, sub=sub)
    o.location, o.rotation_euler = loc, rot
    return o


def cyl(name, r, h, loc, mat, rot=(0, 0, 0), verts=48, bevel=0.0):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=h, location=loc, rotation=rot)
    return finish(bpy.context.active_object, mat, bevel=bevel)


def sphere(name, r, loc, mat, scale=(1, 1, 1), sub=2):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=sub, radius=r, location=loc)
    o = bpy.context.active_object
    o.scale = scale
    return finish(o, mat)


def tube(name, pts, r, mat):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = r
    cu.bevel_resolution = 3
    sp = cu.splines.new("NURBS")
    sp.points.add(len(pts) - 1)
    for p, c in zip(sp.points, pts):
        p.co = (*c, 1)
    sp.use_endpoint_u = True
    sp.order_u = min(4, len(pts))
    o = bpy.data.objects.new(name, cu)
    scene.collection.objects.link(o)
    o.data.materials.append(mat)
    return keep(o)


# ---------- shared materials ----------
STEEL = noisy("Steel", (0.82, 0.82, 0.83), 0.22, 600, 0.05, metal=1.0)
IRON = noisy("Iron", (0.025, 0.023, 0.022), 0.6, 900, 0.25, Coat_Weight=0.12, Coat_Roughness=0.45)
CERAMIC = material("Ceramic", (0.92, 0.91, 0.88), 0.18, Coat_Weight=0.6)
GLASS = material("Glass", (1, 1, 1), 0.0, Transmission_Weight=1.0, IOR=1.47)
WOOD = noisy("Wood", (0.42, 0.26, 0.14), 0.45, 80, 0.2)
DARKWOOD = noisy("DarkWood", (0.18, 0.1, 0.05), 0.4, 80, 0.2)
BLACK = material("BlackPlastic", (0.02, 0.02, 0.02), 0.35)
LINEN = noisy("Linen", (0.9, 0.88, 0.82), 0.85, 400, 0.3, Sheen_Weight=0.5)


def egg(name, loc, rot=0.0):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=1, location=loc)
    o = bpy.context.active_object
    for v in o.data.vertices:
        t = 1 - 0.12 * v.co.x
        v.co = Vector((v.co.x * 0.029, v.co.y * 0.021 * t, v.co.z * 0.021 * t))
    o.data.update()
    o.rotation_euler.z = rot
    o.location.z = 0.021
    return finish(o, noisy("Shell", (0.74, 0.5, 0.31), 0.55, 1400, 0.15, Subsurface_Weight=0.15, Subsurface_Scale=0.004))


# ---------- items (Z up, sitting on the floor at z = 0) ----------
def i_spaghetti():
    """A tied bundle: strands pinched at the twine, fanning out flat at both ends."""
    pasta = material("DryPasta", (0.85, 0.47, 0.02), 0.45)
    L = 0.13
    for i in range(220):
        a, r = rng.uniform(0, 2 * pi), 0.0065 * rng.random() ** 0.5          # position in the tied middle
        mid = Vector((rng.uniform(-0.002, 0.002), r * cos(a), 0.0075 + r * sin(a)))
        spread_y, spread_z = rng.gauss(0, 1), rng.gauss(0, 1)
        ends = []
        for sgn in (-1, 1):
            # Ends fan out sideways (and settle down under gravity), more for outer strands.
            fy = mid.y * 3.2 + spread_y * 0.006 * (0.6 + rng.random())
            fz = max(0.0011, mid.z * 0.55 + abs(spread_z) * 0.002)
            ends.append(Vector((sgn * (L + rng.uniform(-0.004, 0.004)), fy, fz)))
        tube(f"Strand{i}", [tuple(ends[0]), tuple(mid.lerp(ends[0], 0.35)), tuple(mid), tuple(mid.lerp(ends[1], 0.35)), tuple(ends[1])], 0.00085, pasta)
    twine = noisy("Twine", (0.62, 0.48, 0.32), 0.85, 900, 0.6)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.0085, minor_radius=0.0009, location=(0, 0, 0.0075), rotation=(0, pi / 2, 0))
    finish(bpy.context.active_object, twine)
    for sgn in (-1, 1):                                   # a little bow on top
        tube(f"Loop{sgn}", [(0, 0, 0.016), (sgn * 0.008, 0.004, 0.022), (sgn * 0.014, 0.0, 0.019), (sgn * 0.006, -0.002, 0.0165), (0, 0, 0.016)], 0.0008, twine)
        tube(f"Tail{sgn}", [(0, 0, 0.016), (sgn * 0.004, -0.006, 0.018), (sgn * 0.01, -0.016, 0.012), (sgn * 0.012, -0.024, 0.004)], 0.0007, twine)
    for o in ITEM.objects:                               # lie diagonally so the bundle fills the square card
        o.matrix_world = Matrix.Rotation(-0.75, 4, "Z") @ o.matrix_world


def tofu_material():
    """Cream bean curd: pitted sides, a cheesecloth weave pressed into the top and bottom."""
    m = material("Tofu", (0.74, 0.65, 0.47), 0.75, Subsurface_Weight=0.15, Subsurface_Radius=(1.0, 0.85, 0.6), Subsurface_Scale=0.002)
    nt = m.node_tree
    N = nt.nodes.new
    L = nt.links.new
    tc = N("ShaderNodeTexCoord")
    vor = N("ShaderNodeTexVoronoi")
    vor.inputs["Scale"].default_value = 160
    L(tc.outputs["Object"], vor.inputs["Vector"])
    pits = N("ShaderNodeValToRGB")                        # sparse little pits
    pits.color_ramp.elements[0].position = 0.05
    pits.color_ramp.elements[0].color = (0, 0, 0, 1)
    pits.color_ramp.elements[1].position = 0.16
    L(vor.outputs["Distance"], pits.inputs["Fac"])
    noise = N("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 500
    noise.inputs["Detail"].default_value = 8
    L(tc.outputs["Object"], noise.inputs["Vector"])
    waves = []
    for axis in ("X", "Y"):
        w = N("ShaderNodeTexWave")
        w.bands_direction = axis
        w.inputs["Scale"].default_value = 110
        w.inputs["Distortion"].default_value = 0.6
        L(tc.outputs["Object"], w.inputs["Vector"])
        waves.append(w)
    weave = N("ShaderNodeMath"); weave.operation = "MULTIPLY"
    L(waves[0].outputs["Fac"], weave.inputs[0]); L(waves[1].outputs["Fac"], weave.inputs[1])
    geo = N("ShaderNodeNewGeometry")
    sep = N("ShaderNodeSeparateXYZ")
    L(geo.outputs["Normal"], sep.inputs["Vector"])
    top = N("ShaderNodeMath"); top.operation = "ABSOLUTE"
    L(sep.outputs["Z"], top.inputs[0])
    mask = N("ShaderNodeMath"); mask.operation = "POWER"; mask.inputs[1].default_value = 6
    L(top.outputs[0], mask.inputs[0])
    wtop = N("ShaderNodeMath"); wtop.operation = "MULTIPLY"
    L(weave.outputs[0], wtop.inputs[0]); L(mask.outputs[0], wtop.inputs[1])
    h1 = N("ShaderNodeMath"); h1.operation = "MULTIPLY_ADD"
    L(noise.outputs["Fac"], h1.inputs[0]); h1.inputs[1].default_value = 0.4; L(pits.outputs["Color"], h1.inputs[2])
    h = N("ShaderNodeMath"); h.operation = "MULTIPLY_ADD"
    L(wtop.outputs[0], h.inputs[0]); h.inputs[1].default_value = 0.7; L(h1.outputs[0], h.inputs[2])
    bump = N("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 1.0
    bump.inputs["Distance"].default_value = 0.0006
    L(h.outputs[0], bump.inputs["Height"])
    b = nt.nodes["Principled BSDF"]
    L(bump.outputs["Normal"], b.inputs["Normal"])
    tint = N("ShaderNodeMix"); tint.data_type = "RGBA"
    tint.inputs["A"].default_value = (0.5, 0.4, 0.24, 1)
    tint.inputs["B"].default_value = (0.64, 0.53, 0.33, 1)
    L(pits.outputs["Color"], tint.inputs["Factor"])
    L(tint.outputs["Result"], b.inputs["Base Color"])
    return m


def tofu_block(name, size, loc, rot, mat):
    o = box(name, size, loc, mat, bevel=0.0028, rot=rot)
    o.modifiers["Bevel"].segments = 4
    sub = o.modifiers.new("Dense", "SUBSURF")
    sub.subdivision_type = "SIMPLE"
    sub.levels = sub.render_levels = 4
    tex = bpy.data.textures.new(name + "Lumps", "CLOUDS")
    tex.noise_scale = 0.007
    d = o.modifiers.new("Lumps", "DISPLACE")
    d.texture, d.texture_coords, d.strength, d.mid_level = tex, "OBJECT", 0.0018, 0.5
    return o


def i_tofu():
    tofu = tofu_material()
    tofu_block("Lower", (0.1, 0.07, 0.036), (0, 0, 0.018), (0, 0, 0), tofu)
    tofu_block("Upper", (0.092, 0.066, 0.034), (-0.004, 0.006, 0.0535), (0, 0, 0.12), tofu)


def i_eggs():
    egg("E1", (0, 0, 0), 0.3)
    egg("E2", (0.05, 0.012, 0), -0.5)
    egg("E3", (0.024, 0.045, 0), 1.2)


def crumbly(o, strength, scale, levels=4):
    """Dense mesh + cloud displacement so cut cheese faces break up like the real thing."""
    sub = o.modifiers.new("Dense", "SUBSURF")
    sub.subdivision_type = "SIMPLE"
    sub.levels = sub.render_levels = levels
    tex = bpy.data.textures.new(o.name + "Crumb", "CLOUDS")
    tex.noise_scale, tex.noise_depth = scale, 4
    d = o.modifiers.new("Crumb", "DISPLACE")
    d.texture, d.texture_coords, d.strength = tex, "OBJECT", strength


def i_pecorino():
    """A piece cut from the wheel (black rind on the curve) and a shard broken off beside it."""
    paste = noisy("Pecorino", (0.66, 0.55, 0.3), 0.62, 420, 1.0, Subsurface_Weight=0.2, Subsurface_Scale=0.003)
    rind = noisy("Rind", (0.012, 0.012, 0.011), 0.42, 350, 0.8, Coat_Weight=0.3, Coat_Roughness=0.3)
    R0, R1, H, half = 0.035, 0.11, 0.072, radians(36)
    bm = bmesh.new()
    vs = [bm.verts.new((R0 * cos(-half), R0 * sin(-half), z)) if r == R0 else bm.verts.new((R1 * cos(-half), R1 * sin(-half), z))
          for r, z in [(R0, 0), (R1, 0), (R1, H), (R0, H)]]
    f = bm.faces.new(vs)
    bmesh.ops.spin(bm, geom=[f] + vs + list(f.edges), cent=(0, 0, 0), axis=(0, 0, 1), angle=2 * half, steps=40)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.ops.subdivide_edges(bm, edges=[e for e in bm.edges if abs(e.verts[0].co.z - e.verts[1].co.z) > 0.01 or
                                         abs(e.verts[0].co.xy.length - e.verts[1].co.xy.length) > 0.01], cuts=8, use_grid_fill=True)
    wedge = from_bm("Wheel", bm, paste)
    wedge.data.materials.append(rind)
    for q in wedge.data.polygons:                      # black rind on the curved outer face
        c = q.center
        q.material_index = 1 if c.xy.length > R1 - 0.002 and 0.001 < c.z < H - 0.001 else 0
    crumbly(wedge, 0.0024, 0.005, levels=2)
    wedge.rotation_euler.z = radians(-12)
    wedge.location = (-0.04, 0.03, 0)
    # The broken shard: a convex hull of jittered points in a tall thin wedge, roughened.
    sh = bmesh.new()
    for i in range(40):
        t = rng.random()
        z = 0.004 + t * 0.095
        w = 0.034 * (1 - t) ** 0.8 + 0.004
        sh.verts.new((rng.uniform(-w, w), rng.uniform(-0.012, 0.012) * (1 - 0.6 * t), z))
    bmesh.ops.convex_hull(sh, input=sh.verts)
    for v in sh.verts:
        if v.co.z < 0.012:
            v.co.z = 0
    shard = from_bm("Shard", sh, paste, smooth=False)
    crumbly(shard, 0.0022, 0.005)
    shard.location = (-0.024, -0.03, 0)                     # standing just beside the wedge, broad face to camera
    shard.rotation_euler = (radians(6), 0, radians(45))


def i_pepper():
    """A loose heap of whole black peppercorns: wrinkled, slightly irregular, mixed browns."""
    tones = [noisy(f"Peppercorn{k}", c, 0.42, 2600, 1.6) for k, c in enumerate(
        [(0.018, 0.013, 0.01), (0.035, 0.024, 0.016), (0.075, 0.048, 0.03), (0.12, 0.085, 0.06)])]
    weights = [0.45, 0.3, 0.17, 0.08]
    meshes = [bmesh.new() for _ in tones]
    R0, H = 0.045, 0.042
    placed = []
    tries = 0
    while len(placed) < 460 and tries < 20000:
        tries += 1
        h = H * (1 - rng.random() ** 0.55)                          # more corns low down
        rad = R0 * (1 - h / H) * rng.random() ** 0.5
        a = rng.uniform(0, 2 * pi)
        r = rng.uniform(0.0022, 0.0029)
        c = Vector((rad * cos(a), rad * sin(a), h + r))
        if any((c - q).length < (r + qr) * 0.92 for q, qr in placed[-120:]):
            continue                                                 # keep corns from sinking into each other
        placed.append((c, r))
        k = rng.choices(range(len(tones)), weights)[0]
        m = Matrix.Translation(c) @ Matrix.Rotation(rng.uniform(0, pi), 4, Vector((rng.random(), rng.random(), rng.random())).normalized())
        m = m @ Matrix.Diagonal((r * rng.uniform(0.92, 1.06), r * rng.uniform(0.92, 1.06), r * rng.uniform(0.88, 1.0), 1))
        bmesh.ops.create_icosphere(meshes[k], subdivisions=2, radius=1.0, matrix=m)
    for k, bm in enumerate(meshes):
        from_bm(f"Corns{k}", bm, tones[k])
    for i in range(6):                                               # a few strays rolled away from the heap
        a, d = rng.uniform(0, 2 * pi), rng.uniform(0.047, 0.056)
        sphere(f"Stray{i}", 0.0025, (d * cos(a), d * sin(a), 0.0025), tones[rng.randrange(3)], sub=2)


def i_salt():
    lathe("Cellar", [(0, 0), (0.03, 0), (0.035, 0.005), (0.04, 0.035), (0.037, 0.036), (0.033, 0.008), (0, 0.007)], CERAMIC)
    crystal = material("Salt", (0.97, 0.97, 0.97), 0.2, Transmission_Weight=0.6, IOR=1.54)
    for i in range(60):
        a, r = rng.uniform(0, 2 * pi), 0.03 * rng.random() ** 0.5
        box(f"Xtal{i}", (0.004, 0.004, 0.004), (r * cos(a), r * sin(a), 0.02 + rng.uniform(0, 0.012) * (1 - r / 0.03)),
            crystal, rot=(rng.random() * 3, rng.random() * 3, rng.random() * 3))


def i_oil():
    """A tall square glass cruet of golden olive oil with a steel pour spout in a black collar."""
    C, T = 0.0368, 0.0028                                    # square body: corner radius, wall (along the diagonal)
    body = lathe("Bottle", [(0, 0), (C - 0.002, 0), (C, 0.003), (C, 0.168), (0.03, 0.18), (0.0162, 0.192),
                            (0.0162 - T, 0.192), (0.03 - T, 0.18), (C - T, 0.168), (C - T, 0.0045), (0, 0.0045)],
                 GLASS, rot=(0, 0, pi / 4), steps=4)
    bv = body.modifiers.new("Round", "BEVEL")
    bv.width, bv.segments, bv.limit_method, bv.angle_limit = 0.0035, 4, "ANGLE", radians(30)
    oil = material("OliveOil", (0.9, 0.62, 0.02), 0.03, Transmission_Weight=0.9, IOR=1.47)
    o = lathe("Oil", [(0, 0.0046), (C - T - 0.0002, 0.0046), (C - T - 0.0002, 0.158), (0, 0.158)], oil, rot=(0, 0, pi / 4), steps=4)
    bv = o.modifiers.new("Round", "BEVEL")
    bv.width, bv.segments, bv.limit_method, bv.angle_limit = 0.0028, 4, "ANGLE", radians(30)
    lathe("Neck", [(0.0118, 0.19), (0.0118, 0.214), (0.0095, 0.214), (0.0095, 0.19)], GLASS)
    lathe("Collar", [(0, 0.207), (0.0128, 0.207), (0.0131, 0.212), (0.0128, 0.226), (0.0085, 0.229), (0, 0.229)], BLACK)
    lathe("Spout", [(0, 0.228), (0.0062, 0.228), (0.0058, 0.236), (0.0032, 0.268), (0.0028, 0.27), (0, 0.27)], STEEL)
    tube("AirTube", [(0.0045, 0.0, 0.229), (0.0052, 0.0, 0.233), (0.0058, 0.0, 0.236)], 0.0009, STEEL)


def i_soy():
    """A tall dark soy sauce bottle: red shrink-wrapped cap and a plain red label with gold trim."""
    R = 0.028
    lathe("SoyBottle", [(0, 0), (R - 0.002, 0), (R, 0.003), (R, 0.115), (0.024, 0.135), (0.014, 0.155), (0.0115, 0.165),
                        (0.0115, 0.2), (0.0128, 0.203), (0.0128, 0.207), (0.0105, 0.208), (0.0105, 0.2), (0.0095, 0.165),
                        (0.012, 0.155), (0.022, 0.135), (R - 0.0015, 0.115), (R - 0.0015, 0.0035), (0, 0.0035)], GLASS)
    sauce = material("SoySauce", (0.02, 0.006, 0.002), 0.03, Transmission_Weight=0.2, IOR=1.36)
    lathe("Sauce", [(0, 0.0036), (R - 0.0016, 0.0036), (R - 0.0016, 0.115), (0.0218, 0.135), (0.0118, 0.155), (0.0094, 0.168), (0, 0.168)], sauce)
    red = material("SoyRed", (0.42, 0.012, 0.008), 0.3, Coat_Weight=0.5)
    lathe("Cap", [(0, 0.211), (0.0132, 0.211), (0.0134, 0.2), (0.0122, 0.182), (0.0123, 0.172), (0.0122, 0.172)], red, steps=96)
    lathe("CapBand", [(0.0124, 0.181), (0.0126, 0.184)], material("Gold", (0.83, 0.6, 0.22), 0.3, metal=1.0))
    lathe("Label", [(R + 0.0002, 0.022), (R + 0.0002, 0.098)], red, steps=128)
    gold = material("Gold", (0.83, 0.6, 0.22), 0.3, metal=1.0)
    for z in (0.024, 0.0955):
        lathe(f"Trim{z}", [(R + 0.0003, z), (R + 0.0003, z + 0.0012)], gold, steps=128)


def i_paprika():
    """A glass spice jar of deep rust-red smoked paprika with a black lid and a blank white label."""
    powder = noisy("SmokedPaprika", (0.24, 0.045, 0.018), 0.95, 1400, 0.7)
    lathe("Jar", [(0, 0), (0.023, 0), (0.0245, 0.003), (0.0245, 0.078), (0.021, 0.086), (0.019, 0.089), (0.019, 0.094),
                  (0.0175, 0.094), (0.0175, 0.09), (0.0195, 0.086), (0.0225, 0.078), (0.0225, 0.0035), (0, 0.0035)], GLASS)
    lathe("Powder", [(0, 0.0036), (0.0222, 0.0036), (0.0222, 0.072), (0.012, 0.075), (0, 0.0755)], powder)
    lid = noisy("JarLid", (0.02, 0.02, 0.02), 0.45, 120, 0.05)
    lathe("Lid", [(0, 0.089), (0.0205, 0.089), (0.0208, 0.106), (0.019, 0.108), (0, 0.108)], lid)
    for i in range(36):                                              # knurled grip on the lid
        a = i / 36 * 2 * pi
        box(f"Rib{i}", (0.0012, 0.0012, 0.015), (0.0208 * cos(a), 0.0208 * sin(a), 0.098), lid, rot=(0, 0, a))
    label = noisy("Label", (0.93, 0.91, 0.86), 0.85, 300, 0.05)
    lathe("Label", [(0.0247, 0.022), (0.0247, 0.062)], label, steps=96)


INK_LABEL = material("LabelInk", (0.05, 0.04, 0.035), 0.6)


def i_guanciale():
    m = material("Guanciale", (0.6, 0.2, 0.18), 0.45, Subsurface_Weight=0.3, Subsurface_Scale=0.004)
    nt = m.node_tree
    wave = nt.nodes.new("ShaderNodeTexWave")
    wave.bands_direction = "Z"
    wave.inputs["Scale"].default_value = 18
    wave.inputs["Distortion"].default_value = 6
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.55, 0.14, 0.1, 1)
    ramp.color_ramp.elements[1].position = 0.55
    ramp.color_ramp.elements[1].color = (0.95, 0.9, 0.82, 1)
    coord = nt.nodes.new("ShaderNodeTexCoord")
    nt.links.new(coord.outputs["Object"], wave.inputs["Vector"])
    nt.links.new(wave.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], nt.nodes["Principled BSDF"].inputs["Base Color"])
    box("Slab", (0.12, 0.08, 0.035), (0, 0, 0.0175), m, bevel=0.004)
    for i in range(4):
        box(f"Lardon{i}", (0.014, 0.01, 0.01), (0.085 + i % 2 * 0.018, -0.02 + i * 0.012, 0.005), m, bevel=0.0015, rot=(0, 0, i))


def i_cream():
    carton = noisy("Carton", (0.95, 0.95, 0.93), 0.6, 200, 0.05)
    box("Body", (0.07, 0.07, 0.15), (0, 0, 0.075), carton, bevel=0.002)
    box("Band", (0.0705, 0.0705, 0.04), (0, 0, 0.1), material("Blue", (0.15, 0.35, 0.7), 0.5))
    bm = bmesh.new()
    for v in [(-0.035, -0.035, 0.15), (0.035, -0.035, 0.15), (0, -0.035, 0.19), (-0.035, 0.035, 0.15), (0.035, 0.035, 0.15), (0, 0.035, 0.19)]:
        bm.verts.new(v)
    bm.verts.ensure_lookup_table()
    v = bm.verts
    for f in [(0, 1, 2), (3, 5, 4), (0, 2, 5, 3), (1, 4, 5, 2)]:
        bm.faces.new([v[i] for i in f])
    from_bm("Gable", bm, carton, smooth=False)
    box("Fin", (0.004, 0.072, 0.02), (0, 0, 0.198), carton)


def i_garlic():
    skin = noisy("GarlicSkin", (0.93, 0.88, 0.85), 0.55, 120, 0.4, Subsurface_Weight=0.3, Subsurface_Scale=0.005)
    for i in range(8):
        a = i / 8 * 2 * pi
        o = sphere(f"Lobe{i}", 0.018, (0.012 * cos(a), 0.012 * sin(a), 0.022), skin, (0.75, 0.75, 1.15))
        o.rotation_euler = (0.3 * sin(a), -0.3 * cos(a), 0)
    tube("Stem", [(0, 0, 0.04), (0, 0, 0.05), (0.002, 0, 0.058)], 0.003, skin)
    sphere("Clove", 0.009, (0.05, -0.02, 0.008), skin, (1.4, 0.8, 0.9))


def i_butter():
    """A block of butter with two slices cut off, on crinkled parchment, a few curls beside it."""
    from mathutils import noise
    paper = material("Parchment", (0.86, 0.82, 0.72), 0.65, Subsurface_Weight=0.3, Subsurface_Scale=0.002)
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=60, y_segments=48, size=0.07)
    for v in bm.verts:
        v.co.y *= 0.8
        edge = max(abs(v.co.x) / 0.07, abs(v.co.y) / 0.056)
        v.co.z = 0.0006 + 0.0012 * noise.noise(v.co * 70) + 0.0005 * noise.noise(v.co * 260) + 0.004 * max(0, edge - 0.8) ** 2 * 25
    paper_o = from_bm("Paper", bm, paper)
    paper_o.rotation_euler.z = 0.12
    butter = noisy("Butter", (0.92, 0.58, 0.09), 0.32, 40, 0.08, Subsurface_Weight=0.35, Subsurface_Radius=(1.0, 0.8, 0.4), Subsurface_Scale=0.006)
    H, W = 0.042, 0.052
    box("Block", (0.07, W, H), (0.022, 0, H / 2 + 0.0015), butter, bevel=0.003)
    box("Slice1", (0.016, W, H), (-0.028, 0.002, H / 2 + 0.0015), butter, bevel=0.0025, rot=(0, radians(-4), 0.03))
    box("Slice2", (0.016, W, H), (-0.054, 0.004, H / 2 + 0.0015), butter, bevel=0.0025, rot=(0, radians(-9), 0.06))
    for i, (x, y, rz) in enumerate([(-0.055, -0.045, 0.4), (-0.015, -0.05, 2.0), (0.045, -0.045, -0.5)]):
        pts = []
        for k in range(14):
            t = k / 13
            ang = t * 2 * pi * 1.05
            r = 0.009 * (1 - 0.5 * t)
            pts.append((0.006 * t, r * cos(ang), r * sin(ang) + 0.0095))
        o = tube(f"Curl{i}", pts, 0.0016, butter)
        o.data.bevel_resolution = 1
        o.scale = (2.2, 1, 1)
        o.location = (x, y, 0.0)
        o.rotation_euler = (0, 0, rz)
    bpy.context.view_layer.update()
    for o in ITEM.objects:
        o.matrix_world = Matrix.Rotation(-0.3, 4, "Z") @ o.matrix_world


def leaflet(name, L, mat, curl, seed):
    """Flat-leaf parsley leaflet: a three-lobed wedge with toothed edges, cupped slightly."""
    from mathutils import noise
    bm = bmesh.new()
    span, n, rings = 1.25, 72, 5
    centre = bm.verts.new((0, 0, 0))
    grid = []
    for j in range(1, rings + 1):
        f = j / rings
        row = []
        for i in range(n + 1):
            u = -1 + 2 * i / n
            phi = u * span
            lobe = 0.62 + 0.38 * (0.5 + 0.5 * cos(2 * pi * u / 0.62)) ** 1.5
            teeth = 1 + 0.045 * abs(sin(pi * u * 7)) if j == rings else 1
            r = L * lobe * (1 - u * u) ** 0.45 * teeth * f
            x, y = r * cos(phi), r * sin(phi)
            z = curl * (y * y) / L - 0.15 * curl * r + 0.0006 * noise.noise(Vector((x, y, seed)) * 300)
            row.append(bm.verts.new((x, y, z)))
        grid.append(row)
    for i in range(n):
        bm.faces.new((centre, grid[0][i], grid[0][i + 1]))
    for j in range(rings - 1):
        for i in range(n):
            bm.faces.new((grid[j][i], grid[j + 1][i], grid[j + 1][i + 1], grid[j][i + 1]))
    o = from_bm(name, bm, mat)
    m = o.modifiers.new("Solid", "SOLIDIFY")
    m.thickness = 0.00025
    return o


def i_parsley():
    """A tied bunch of flat-leaf parsley: stems gathered at the twine, leaves fanning out."""
    green = material("Parsley", (0.025, 0.24, 0.01), 0.52, Subsurface_Weight=0.12, Subsurface_Radius=(0.3, 1.0, 0.2), Subsurface_Scale=0.002)
    light = material("ParsleyLight", (0.06, 0.36, 0.02), 0.5, Subsurface_Weight=0.12, Subsurface_Scale=0.002)
    stem = material("Stem", (0.1, 0.36, 0.03), 0.4)
    tie = Vector((-0.06, 0, 0.006))
    for i in range(34):
        a = max(-0.8, min(0.8, rng.gauss(0, 0.4)))
        length = rng.uniform(0.05, 0.085)
        h = 0.006 + 0.03 * (1 - (a / 0.85) ** 2) * rng.uniform(0.35, 1.0)    # leaves pile up into a dome
        tail = tie + Vector((-0.06 + rng.uniform(-0.006, 0.004), rng.uniform(-0.004, 0.004) + a * 0.012, -0.002))
        tip = tie + Vector((length * cos(a), length * sin(a), h))
        knee = tie.lerp(tip, 0.5) + Vector((0, 0, h * 0.3))
        tube(f"Stem{i}", [tuple(tail), tuple(tie + Vector((0, a * 0.004, 0))), tuple(knee), tuple(tip)], 0.0011, stem)
        for j in range(3):                                                   # each stem forks into sprigs...
            b2 = a + (j - 1) * 0.6 + rng.uniform(-0.25, 0.25)
            fork = tip + Vector((0.016 * cos(b2), 0.016 * sin(b2), rng.uniform(-0.004, 0.012)))
            tube(f"Sprig{i}{j}", [tuple(tip), tuple(tip.lerp(fork, 0.5) + Vector((0, 0, 0.002))), tuple(fork)], 0.0007, stem)
            for k, da in enumerate((-0.75, 0.0, 0.75)):                      # ...each ending in three leaflets
                d = b2 + da + rng.uniform(-0.25, 0.25)
                lf = leaflet(f"Leaf{i}{j}{k}", rng.uniform(0.018, 0.027), green if rng.random() < 0.65 else light,
                             rng.uniform(0.1, 0.25), i * 9 + j * 3 + k)
                lf.location = fork + Vector((0.003 * cos(d), 0.003 * sin(d), 0))
                lf.rotation_euler = (rng.uniform(-1.0, 1.0), rng.uniform(-0.7, 0.35), d)
    twine = noisy("Twine", (0.78, 0.68, 0.5), 0.85, 900, 0.6)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.0066, minor_radius=0.0011, location=tuple(tie), rotation=(0, pi / 2, 0))
    finish(bpy.context.active_object, twine)
    for sgn in (-1, 1):
        tube(f"TwineEnd{sgn}", [(tie.x, 0, tie.z + 0.006), (tie.x + sgn * 0.004, -0.008, tie.z + 0.004), (tie.x + sgn * 0.006, -0.026, 0.001)], 0.0009, twine)
    bpy.context.view_layer.update()
    for o in ITEM.objects:
        o.matrix_world = Matrix.Rotation(0.6, 4, "Z") @ o.matrix_world


def skillet(scale=1.0, loc=(0, 0, 0)):
    s = scale
    lathe("Skillet", [(r * s, z * s) for r, z in [(0, 0.006), (0.104, 0.006), (0.117, 0.012), (0.127, 0.045), (0.1325, 0.0515),
                                                   (0.1375, 0.047), (0.1265, 0.011), (0.116, 0.001), (0, 0)]], IRON, loc=loc, sub=1)
    box("Handle", (0.16 * s, 0.03 * s, 0.014 * s), (loc[0] + 0.205 * s, loc[1], loc[2] + 0.045 * s), IRON, bevel=0.004 * s, rot=(0, radians(-9), 0))


def t_skillet():
    skillet()


def t_pot():
    lathe("Pot", [(0, 0), (0.105, 0), (0.11, 0.006), (0.11, 0.15), (0.114, 0.152), (0.104, 0.152), (0.104, 0.006), (0, 0.006)], STEEL)
    for sgn in (-1, 1):
        tube(f"PotHandle{sgn}", [(sgn * 0.11, -0.02, 0.13), (sgn * 0.13, -0.015, 0.135), (sgn * 0.13, 0.015, 0.135), (sgn * 0.11, 0.02, 0.13)], 0.004, STEEL)
    lathe("Lid", [(0, 0.158), (0.115, 0.152), (0.118, 0.155), (0.06, 0.168), (0, 0.17)], STEEL)
    sphere("LidKnob", 0.012, (0, 0, 0.178), BLACK)


def t_knife():
    box("Board", (0.3, 0.2, 0.02), (0, 0, 0.01), WOOD, bevel=0.004)
    bm = bmesh.new()
    pts = [(0, 0), (0.17, 0.005), (0.2, 0.02), (0.17, 0.04), (0, 0.04)]
    vs = [bm.verts.new((x, y, 0)) for x, y in pts]
    f = bm.faces.new(vs)
    r = bmesh.ops.extrude_face_region(bm, geom=[f])
    for v in [e for e in r["geom"] if isinstance(e, bmesh.types.BMVert)]:
        v.co.z = 0.002
    blade = from_bm("Blade", bm, STEEL, smooth=False)
    rz = 0.25
    blade.location = (-0.11, -0.05, 0.021)
    blade.rotation_euler.z = rz
    # The handle runs straight on from the blade's heel (the middle of its back edge), joined by a steel
    # bolster, so knife and handle read as one piece.
    c, s = cos(rz), sin(rz)
    hx, hy = -0.11 - 0.02 * s, -0.05 + 0.02 * c          # heel midpoint
    box("Bolster", (0.012, 0.03, 0.014), (hx - 0.004 * c, hy - 0.004 * s, 0.028), STEEL, bevel=0.003, rot=(0, 0, rz))
    box("KnifeHandle", (0.11, 0.024, 0.018), (hx - 0.064 * c, hy - 0.064 * s, 0.029), BLACK, bevel=0.006, rot=(0, 0, rz))


def t_towels():
    stripe = material("Towel", (0.92, 0.9, 0.85), 0.9, Sheen_Weight=0.4)
    nt = stripe.node_tree
    wave = nt.nodes.new("ShaderNodeTexWave")
    wave.inputs["Scale"].default_value = 3
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.interpolation = "CONSTANT"
    ramp.color_ramp.elements[0].color = (0.92, 0.9, 0.85, 1)
    ramp.color_ramp.elements[1].position = 0.85
    ramp.color_ramp.elements[1].color = (0.25, 0.35, 0.55, 1)
    nt.links.new(wave.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], nt.nodes["Principled BSDF"].inputs["Base Color"])
    box("Towel1", (0.18, 0.12, 0.022), (0, 0, 0.011), stripe, bevel=0.008)
    box("Towel2", (0.18, 0.12, 0.022), (0.01, 0.01, 0.033), stripe, bevel=0.008, rot=(0, 0, 0.12))


def t_grater():
    holes = noisy("GraterSteel", (0.8, 0.8, 0.82), 0.25, 0, 0.0, metal=1.0)
    nt = holes.node_tree
    vor = nt.nodes.new("ShaderNodeTexVoronoi")
    vor.inputs["Scale"].default_value = 70
    vor.feature = "F1"
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.12
    ramp.color_ramp.elements[0].color = (0.02, 0.02, 0.02, 1)
    ramp.color_ramp.elements[1].position = 0.16
    nt.links.new(vor.outputs["Distance"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], nt.nodes["Principled BSDF"].inputs["Base Color"])
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1)
    for v in bm.verts:
        t = v.co.z + 0.5
        v.co = Vector((v.co.x * (0.1 - 0.035 * t), v.co.y * (0.075 - 0.025 * t), v.co.z * 0.22))
    g = from_bm("Grater", bm, holes, smooth=False)
    g.location.z = 0.11
    tube("GraterHandle", [(0, -0.025, 0.22), (0, -0.02, 0.26), (0, 0.02, 0.26), (0, 0.025, 0.22)], 0.006, BLACK)


def t_bowl():
    lathe("Bowl", [(0, 0.007), (0.035, 0.008), (0.054, 0.018), (0.066, 0.036), (0.07, 0.052), (0.0725, 0.0545), (0.0745, 0.053),
                   (0.072, 0.034), (0.059, 0.012), (0.042, 0.002), (0.038, 0), (0, 0)], CERAMIC, sub=1)
    # The whisk leans in the bowl: wire loops inside, clear of the bowl's floor and wall, and the handle
    # resting on the rim (touching it, not passing through it). Axis from the loops' tip A up to the rim.
    ax, az = -0.03, 0.028
    th = atan2(0.0632 - az, 0.0725 - ax)
    def onaxis(s, y, zp):
        return (ax + s * cos(th) - zp * sin(th), y, az + s * sin(th) + zp * cos(th))
    for k in range(6):
        a = k / 6 * pi
        pts = [onaxis(0.07 * (1 - cos(t)) / 2, 0.022 * sin(t) * cos(a), 0.022 * sin(t) * sin(a))
               for t in [i / 12 * pi for i in range(13)]]
        tube(f"Wire{k}", pts, 0.0008, STEEL)
    cyl("WhiskHandle", 0.008, 0.11, onaxis(0.125, 0, 0), STEEL, rot=(0, pi / 2 - th, 0))


def t_slotted():
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=1)
    for v in bm.verts:
        v.co = Vector((v.co.x * 0.04, v.co.y * 0.028, min(v.co.z, 0) * 0.012 + 0.012))
    b = from_bm("SpoonBowl", bm, STEEL)
    for i in range(3):
        box(f"Slot{i}", (0.025, 0.003, 0.004), (0, -0.008 + i * 0.008, 0.0025), BLACK)
    box("SpoonHandle", (0.2, 0.012, 0.003), (0.13, 0, 0.012), STEEL, bevel=0.0012, rot=(0, radians(-6), 0))


def t_tongs():
    for sgn in (-1, 1):
        box(f"Arm{sgn}", (0.24, 0.016, 0.0025), (0, sgn * 0.012, 0.012), STEEL, bevel=0.001, rot=(0, 0, sgn * 0.04))
        box(f"Tip{sgn}", (0.03, 0.02, 0.004), (-0.12, sgn * 0.017, 0.012), STEEL, bevel=0.0015, rot=(0, 0, sgn * 0.04))
    cyl("Hinge", 0.012, 0.03, (0.12, 0, 0.012), STEEL, rot=(pi / 2, 0, 0))


def t_mug():
    mugmat = material("MugGlaze", (0.24, 0.35, 0.42), 0.25, Coat_Weight=0.8)
    lathe("Mug", [(0, 0), (0.032, 0), (0.034, 0.075), (0.031, 0.075), (0.029, 0.006), (0, 0.006)], mugmat)
    tube("MugHandle", [(0.032, 0, 0.06), (0.05, 0, 0.055), (0.05, 0, 0.025), (0.032, 0, 0.02)], 0.005, mugmat)
    lathe("LadleBowl", [(0, 0), (0.025, 0.004), (0.035, 0.018), (0.036, 0.03), (0.033, 0.03), (0.032, 0.019), (0.023, 0.007), (0, 0.003)],
          STEEL, loc=(-0.08, 0.03, 0))
    tube("LadleHandle", [(-0.08 + 0.034, 0.03, 0.03), (-0.02, 0.06, 0.06), (0.06, 0.09, 0.07)], 0.0035, STEEL)


def t_colander():
    perf = material("Perforated", (0.8, 0.8, 0.82), 0.25, 1.0)
    nt = perf.node_tree
    vor = nt.nodes.new("ShaderNodeTexVoronoi")
    vor.inputs["Scale"].default_value = 90
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.1
    ramp.color_ramp.elements[0].color = (0.02, 0.02, 0.02, 1)
    ramp.color_ramp.elements[1].position = 0.14
    nt.links.new(vor.outputs["Distance"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], nt.nodes["Principled BSDF"].inputs["Base Color"])
    lathe("Colander", [(0, 0.015), (0.05, 0.017), (0.09, 0.05), (0.11, 0.1), (0.114, 0.102), (0.106, 0.098), (0.086, 0.052), (0.048, 0.022), (0, 0.02)], perf)
    lathe("Foot", [(0.04, 0), (0.05, 0), (0.05, 0.017), (0.04, 0.017)], STEEL)


def t_blender():
    lathe("Base", [(0, 0), (0.07, 0), (0.07, 0.08), (0.05, 0.1), (0, 0.1)], BLACK)
    lathe("Jar", [(0, 0.1), (0.045, 0.1), (0.065, 0.28), (0.062, 0.28), (0.042, 0.103), (0, 0.103)], GLASS)
    cyl("JarLid", 0.066, 0.02, (0, 0, 0.29), BLACK)
    cyl("Dial", 0.012, 0.01, (0, -0.07, 0.04), STEEL, rot=(pi / 2, 0, 0))


def t_tray():
    tray = noisy("TraySteel", (0.62, 0.62, 0.62), 0.38, 200, 0.05, metal=1.0)
    box("TrayBase", (0.3, 0.2, 0.004), (0, 0, 0.002), tray)
    for x, y, sx, sy in [(0, 0.1, 0.304, 0.004), (0, -0.1, 0.304, 0.004), (0.15, 0, 0.004, 0.2), (-0.15, 0, 0.004, 0.2)]:
        box(f"Rim{x}{y}", (sx, sy, 0.02), (x, y, 0.01), tray)


def e_weight():
    skillet(0.75)


def e_timer():
    lathe("TimerBody", [(0, 0), (0.035, 0), (0.038, 0.01), (0.036, 0.035), (0.025, 0.055), (0, 0.06)], material("TimerRed", (0.7, 0.12, 0.08), 0.3, Coat_Weight=0.6))
    lathe("TimerTop", [(0, 0.035), (0.034, 0.035), (0.03, 0.05), (0.02, 0.06), (0, 0.062)], material("TimerWhite", (0.95, 0.95, 0.93), 0.3, Coat_Weight=0.6), loc=(0, 0, 0.002))
    box("Pointer", (0.004, 0.012, 0.003), (0, -0.03, 0.05), BLACK, rot=(radians(35), 0, 0))


ITEMS = {
    "I-SPAGHETTI": i_spaghetti, "I-TOFU": i_tofu, "I-EGGS": i_eggs, "I-PECORINO": i_pecorino, "I-PEPPER": i_pepper,
    "I-SALT": i_salt, "I-OIL": i_oil, "I-SOY": i_soy, "I-PAPRIKA": i_paprika, "I-GUANCIALE": i_guanciale,
    "I-CREAM": i_cream, "I-GARLIC": i_garlic, "I-BUTTER": i_butter, "I-PARSLEY": i_parsley,
    "T-POT": t_pot, "T-SKILLET": t_skillet, "T-KNIFE": t_knife, "T-TOWELS": t_towels, "T-GRATER": t_grater,
    "T-BOWL": t_bowl, "T-SLOTTED": t_slotted, "T-TONGS": t_tongs, "T-MUG": t_mug, "T-COLANDER": t_colander,
    "T-BLENDER": t_blender, "T-TRAY": t_tray, "E-WEIGHT": e_weight, "E-TIMER": e_timer,
}

# ---------- studio ----------
bm = bmesh.new()
for i in range(25):                                   # seamless sweep: flat floor, then a curve up into a back wall
    if i <= 12:
        y, z = -1.5 + 2.3 * i / 12, 0.0
    else:
        a = (i - 12) / 12 * pi / 2
        y, z = 0.8 + 0.6 * sin(a), 0.6 * (1 - cos(a))
    bm.verts.new((-3, y, z))
    bm.verts.new((3, y, z))
bm.verts.ensure_lookup_table()
for i in range(24):
    a, b, c, d = bm.verts[2 * i], bm.verts[2 * i + 1], bm.verts[2 * i + 3], bm.verts[2 * i + 2]
    bm.faces.new((a, b, c, d))
me = bpy.data.meshes.new("Sweep")
bm.to_mesh(me)
sweep = bpy.data.objects.new("Sweep", me)
scene.collection.objects.link(sweep)
sweep.data.materials.append(material("Backdrop", (0.2, 0.17, 0.14), 0.85))
for p in sweep.data.polygons:
    p.use_smooth = True


def area(name, loc, size, power, color):
    d = bpy.data.lights.new(name, "AREA")
    d.size, d.energy, d.color = size, power, color
    o = bpy.data.objects.new(name, d)
    scene.collection.objects.link(o)
    o.location = loc
    tc = o.constraints.new("TRACK_TO")
    tc.target, tc.track_axis, tc.up_axis = target, "TRACK_NEGATIVE_Z", "UP_Y"
    return o


target = bpy.data.objects.new("Target", None)
scene.collection.objects.link(target)
key = area("Key", (-0.5, -0.6, 0.7), 0.6, 60, (1.0, 0.95, 0.88))
fill = area("Fill", (0.7, -0.4, 0.3), 0.8, 18, (0.9, 0.95, 1.0))
rim = area("Rim", (0.2, 0.6, 0.6), 0.4, 30, (1.0, 0.92, 0.85))
world = bpy.data.worlds.new("W")
scene.world = world
try:
    world.use_nodes = True
except AttributeError:
    pass
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.6, 0.55, 0.5, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.08

cd = bpy.data.cameras.new("Cam")
cd.lens = 70
cam = bpy.data.objects.new("Cam", cd)
scene.collection.objects.link(cam)
scene.camera = cam
tc = cam.constraints.new("TRACK_TO")
tc.target, tc.track_axis, tc.up_axis = target, "TRACK_NEGATIVE_Z", "UP_Y"

scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = 48
scene.cycles.use_adaptive_sampling = True
scene.cycles.adaptive_threshold = 0.03
scene.cycles.use_denoising = True
scene.cycles.max_bounces = 8
scene.cycles.transmission_bounces = 8
scene.render.resolution_x = scene.render.resolution_y = 320
scene.view_settings.view_transform = "AgX"
scene.view_settings.exposure = -0.3
scene.render.image_settings.file_format = "PNG"

CAM_DIR = {'I-OIL': (0.55, -1.0, 0.45), 'I-SOY': (0.55, -1.0, 0.45), 'I-BUTTER': (0.6, -1.0, 0.45), 'I-PARSLEY': (0.15, -0.4, 1.0), 'I-SPAGHETTI': (0.3, -0.45, 1.0)}
CAM_ZOOM = {'I-BUTTER': 0.78, 'I-PECORINO': 0.85, 'I-PARSLEY': 0.76, 'I-SPAGHETTI': 0.86, 'I-PEPPER': 0.82, 'I-PAPRIKA': 0.96}
CAM_EXPOSURE = {'I-BUTTER': -0.6, 'I-PECORINO': -0.6, 'I-TOFU': -0.8, 'I-SPAGHETTI': -1.0}

# ---------- render each item ----------
for item_id, build in ITEMS.items():
    if ONLY and item_id not in ONLY:
        continue
    ITEM = bpy.data.collections.new(item_id)
    scene.collection.children.link(ITEM)
    build()
    bpy.context.view_layer.update()
    pts = []
    for o in ITEM.objects:
        pts += [o.matrix_world @ Vector(c) for c in o.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    centre, radius = (lo + hi) / 2, (hi - lo).length / 2
    target.location = centre
    half_fov = __import__('math').atan(18 / cd.lens)            # 36 mm sensor
    dist = radius / __import__('math').sin(half_fov) * 1.08       # a little breathing room
    # Long, flat items read better from higher up and a little closer.
    direction = Vector(CAM_DIR.get(item_id, (0.55, -1.0, 0.75))).normalized()
    dist *= CAM_ZOOM.get(item_id, 1.0)
    scene.view_settings.exposure = CAM_EXPOSURE.get(item_id, -0.3)
    cd.type = "PERSP"
    if item_id.startswith("I-") and item_id != "I-SPAGHETTI":
        # Ingredients use a 2:1 dimetric view: orthographic, 45 degrees round, 30 degrees down.
        direction = Vector((1.0, -1.0, 0.8165)).normalized()
        fwd = -direction
        right = fwd.cross(Vector((0, 0, 1))).normalized()
        up = right.cross(fwd)
        xs = [(q - centre).dot(right) for q in pts]
        ys = [(q - centre).dot(up) for q in pts]
        centre = centre + right * (max(xs) + min(xs)) / 2 + up * (max(ys) + min(ys)) / 2
        target.location = centre
        cd.type = "ORTHO"
        cd.ortho_scale = max(max(xs) - min(xs), max(ys) - min(ys)) * 1.22
        dist = max(dist, radius * 4)
    cam.location = centre + direction * dist
    for l, base in ((key, Vector((-0.5, -0.6, 0.7))), (fill, Vector((0.7, -0.4, 0.3))), (rim, Vector((0.2, 0.6, 0.6)))):
        reach = max(radius * 3.5, 0.25)
        l.location = centre + base.normalized() * reach
        l.data.size = reach * 0.8
        l.data.energy = {"Key": 30, "Fill": 7, "Rim": 16}[l.name] * reach ** 2   # constant illuminance at any scale
    scene.render.filepath = os.path.join(OUT, f"{item_id}.png")
    bpy.ops.render.render(write_still=True)
    print("ITEM_DONE", item_id, round(radius, 3))
    for o in list(ITEM.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.data.collections.remove(ITEM)
print("ALL_DONE")
