"""Bake the counter's wood grain and glue seams, and the backsplash's tile and grout relief, into
tangent-space normal maps for the web kitchen (glTF dropped the procedural bump).
Same UVs as the exported kitchen (plain 0-1 planes), so three.js just adds them as normalMap.
  blender --background --factory-startup --python bake_normals.py -- <out_dir>
"""
import bpy, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
os.environ["SCENE_ONLY"] = "1"
base = os.path.join(HERE, "skillet_test.py")
exec(compile(open(base).read(), base, "exec"), {"__file__": base, "__name__": "base_scene"})
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0] if argv else os.path.join(HERE, "..", "web", "assets")
scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = 4
scene.render.image_settings.file_format = "JPEG"
scene.render.image_settings.quality = 90

for name, size in (("Counter", 2048), ("Backsplash", 1024)):
    obj = bpy.data.objects[name]
    nt = obj.data.materials[0].node_tree
    img = bpy.data.images.new(f"{name}_normal", size, size, float_buffer=False)
    img.colorspace_settings.name = "Non-Color"
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    nt.nodes.active = tex
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.bake(type="NORMAL", normal_space="TANGENT", margin=4)
    path = os.path.join(OUT, f"{name}_normal.jpg")
    img.save_render(path, scene=scene)
    print("BAKED", path, os.path.getsize(path))
