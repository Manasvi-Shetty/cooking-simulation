"""Downsizes the HDRI the Blender renders use so the web kitchen can light itself the same way.
Writes a 1k Radiance .hdr; the page loads it base64-encoded (the artifact host doesn't serve .hdr)."""
import bpy, sys, os, base64
src, out = sys.argv[sys.argv.index("--") + 1:][:2]
img = bpy.data.images.load(src)
img.scale(1024, 512)
# Mostly neutral: the warm cast is fine under Cycles' white area lights, but on its own in
# real time it turns the whole kitchen orange. Keep a hint of warmth.
import numpy as np
px = np.array(img.pixels[:], dtype=np.float32).reshape(-1, 4)
lum = px[:, :3] @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
px[:, :3] = lum[:, None] + (px[:, :3] - lum[:, None]) * 0.6
mean = px[:, :3].mean(0)
px[:, :3] *= (mean.mean() / mean) * np.array([1.03, 1.0, 0.96], dtype=np.float32)   # white-balance, slightly warm
print("ENV_MEAN", px[:, :3].mean(0))
img.pixels[:] = px.ravel()
img.filepath_raw = out
img.file_format = "HDR"
img.save()
with open(out, "rb") as f:
    data = base64.b64encode(f.read()).decode()
with open(out + ".b64.txt", "w") as f:
    f.write(data)
os.remove(out)
print("ENV_DONE", len(data))
