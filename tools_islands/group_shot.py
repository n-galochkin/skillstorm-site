"""A wide shot of several islands at their archipelago positions, to compare the
whole thing against the reference painting rather than island by island."""
import math
import os
import sys

import bpy
from mathutils import Vector

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import island_lib as L  # noqa: E402
import build_islands as B  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
SHOTS = os.path.join(HERE, "renders")

# id -> (x, z) in site metres, from archipelago.js, shifted into one frame
PLACE = [
    ('combat',   (0, 0)),
    ('landing',  (-86, -34)),
    ('skills',   (82, -60)),
    ('devlog',   (-10, 86)),
    ('islet_01', (-42, -92)),
    ('islet_05', (-78, 58)),
    ('islet_03', (120, 4)),
    ('islet_06', (28, -98)),
    ('islet_08', (62, 78)),
    ('storm',    (176, -104)),
]

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()
L.setup_scene(samples=int(sys.argv[-1]) if sys.argv[-1].isdigit() else 64, res=(1440, 820))

for ident, (px, pz) in PLACE:
    spec = next(s for s in B.SPECS if s['id'] == ident)
    obj, tris, rings = L.build_island(spec, ident + "_g")
    obj.location = (px, -pz, 0)

cam_data = bpy.data.cameras.get("Cam") or bpy.data.cameras.new("Cam")
cam_data.lens = 55
cam = bpy.data.objects.get("CamObj") or bpy.data.objects.new("CamObj", cam_data)
if cam.name not in bpy.context.scene.objects:
    bpy.context.scene.collection.objects.link(cam)
bpy.context.scene.camera = cam
e, a, d = math.radians(33), math.radians(72), 330.0
target = Vector((30, -10, 0))
cam.location = target + Vector((math.cos(e) * math.cos(a) * d,
                                math.cos(e) * math.sin(a) * d,
                                math.sin(e) * d))
cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
bpy.context.scene.render.filepath = os.path.join(SHOTS, "_archipelago.png")
bpy.ops.render.render(write_still=True)
print("[group] done")
