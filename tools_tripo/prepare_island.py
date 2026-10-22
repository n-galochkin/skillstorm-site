"""Blender headless: turn a generated island into one the site can use.

A model as it comes back is an arbitrary size, floating in nowhere, with a texture
far larger than a web page should carry. This puts it in metres, drops it to the
waterline, shrinks the texture and, so that trees, houses and fighters can stand
on it, measures its surface into a heightmap.

Run: blender -b -P prepare_island.py -- <glb> <out_dir> <id> <radius> [waterline] [tex]
"""
import json
import math
import os
import struct
import sys
import zlib

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
GLB, OUT, ISLAND_ID = argv[0], argv[1], argv[2]
RADIUS = float(argv[3])
WATERLINE = float(argv[4]) if len(argv) > 4 else 0.07   # share of the height sunk
TEX = int(argv[5]) if len(argv) > 5 else 1024
MAX_TRIS = int(argv[6]) if len(argv) > 6 else 0     # 0 = leave the mesh alone
KEEP = float(argv[7]) if len(argv) > 7 else 1.0     # share of the depth to keep, from the image's left
RES = 256

os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)

meshes = [o for o in bpy.data.objects if o.type == "MESH"]
for o in bpy.data.objects:
    o.select_set(o.type == "MESH")
bpy.context.view_layer.objects.active = meshes[0]
if len(meshes) > 1:
    bpy.ops.object.join()
obj = bpy.context.view_layer.objects.active
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

# A generated model sometimes carries a neighbour that stood beside it in the
# painting. Image left is glTF +Z, which is Blender -Y; faces beyond the kept share
# of that axis are dropped.
if KEEP < 1.0:
    import bmesh
    ys = [v.co.y for v in obj.data.vertices]
    cut = min(ys) + (max(ys) - min(ys)) * KEEP
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    drop = [f for f in bm.faces if f.calc_center_median().y > cut]
    bmesh.ops.delete(bm, geom=drop, context="FACES")
    bm.to_mesh(obj.data)
    bm.free()

mn = Vector((1e9, 1e9, 1e9))
mx = Vector((-1e9, -1e9, -1e9))
for v in obj.data.vertices:
    for i in range(3):
        mn[i] = min(mn[i], v.co[i])
        mx[i] = max(mx[i], v.co[i])
size = mx - mn

# metres: the island's widest horizontal half-extent becomes the radius asked for
# the radius is the island's half-width in the painting; the model's front faces
# glTF +X, so the painting's horizontal runs along glTF Z, which is Blender Y
scale = RADIUS / (size.y / 2.0)
# centre it horizontally, and put the waterline a little above the flat underside
# so the shore meets the sea instead of hovering over it
cx, cy = (mx.x + mn.x) / 2.0, (mx.y + mn.y) / 2.0
z0 = mn.z    # the real waterline is found later, from the beach
for v in obj.data.vertices:
    v.co = Vector(((v.co.x - cx) * scale, (v.co.y - cy) * scale, (v.co.z - z0) * scale))
obj.data.update()

mn = Vector((1e9, 1e9, 1e9))
mx = Vector((-1e9, -1e9, -1e9))
for v in obj.data.vertices:
    for i in range(3):
        mn[i] = min(mn[i], v.co[i])
        mx[i] = max(mx[i], v.co[i])

for img in bpy.data.images:
    if img.size[0] > TEX:
        img.scale(TEX, TEX)

# a page cannot carry twenty full-detail islands, so each one is cut down to what
# its size on screen can actually show
obj.data.calc_loop_triangles()
before = len(obj.data.loop_triangles)
if MAX_TRIS and before > MAX_TRIS:
    mod = obj.modifiers.new("decimate", "DECIMATE")
    mod.ratio = MAX_TRIS / float(before)
    bpy.ops.object.modifier_apply(modifier=mod.name)

obj.data.calc_loop_triangles()
tris = len(obj.data.loop_triangles)

# ---- heightmap: drop a ray on every cell of the island's bounding square -----
span = max(mx.x - mn.x, mx.y - mn.y)
span = span * 1.06                       # a little air around the coast
depth = mn.z - 1.0
grid = []
lo, hi = 1e9, -1e9
deps = bpy.context.evaluated_depsgraph_get()
top = mx.z + 10.0
for row in range(RES):
    line = []
    for col in range(RES):
        x = -span / 2 + col / (RES - 1) * span
        # rows run along glTF +Z, and glTF Z is Blender -Y, so walk Y downward
        y = span / 2 - row / (RES - 1) * span
        hit, loc, _, _ = obj.ray_cast(Vector((x, y, top)), Vector((0, 0, -1)),
                                      depsgraph=deps)
        h = loc.z if hit else None
        line.append(h)
    grid.append(line)

# The waterline. A fixed share of the model's height drowns a flat sandy island
# whose mesas make it tall, so the sea is set from the land itself: the lowest
# stretch of its top surface is the beach, and the water sits just under that.
hits = sorted(h for line in grid for h in line if h is not None)
beach = hits[int(len(hits) * 0.08)] if hits else mn.z
shift = beach - 0.012 * RADIUS          # beach a hand's breadth above the sea, in proportion
for v in obj.data.vertices:
    v.co.z -= shift
obj.data.update()
under = mn.z - shift - 1.0
for line in grid:
    for i, h in enumerate(line):
        line[i] = (h - shift) if h is not None else under
        lo = min(lo, line[i])
        hi = max(hi, line[i])

span_h = max(hi - lo, 1e-6)
rows = []
for line in grid:
    px = bytearray()
    for h in line:
        v = int(round((h - lo) / span_h * 65535))
        px += struct.pack(">H", max(0, min(65535, v)))
    rows.append(bytes(px))


def png16(path, rows, res):
    def chunk(tag, data):
        c = tag + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c))
    raw = b"".join(b"\x00" + r for r in rows)
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n")
        f.write(chunk(b"IHDR", struct.pack(">IIBBBBB", res, res, 16, 0, 0, 0, 0)))
        f.write(chunk(b"IDAT", zlib.compress(raw, 9)))
        f.write(chunk(b"IEND", b""))


png16(os.path.join(OUT, ISLAND_ID + "_height.png"), rows, RES)

bpy.ops.object.select_all(action="DESELECT")
obj.select_set(True)
bpy.ops.export_scene.gltf(
    filepath=os.path.join(OUT, ISLAND_ID + ".glb"),
    export_format="GLB", use_selection=True,
    export_image_format="JPEG", export_jpeg_quality=86,
    export_texture_dir="", export_yup=True,
    export_apply=True, export_normals=True,
    export_materials="EXPORT", export_cameras=False, export_lights=False,
    # Draco turns the vertex data into a fraction of its size; nineteen islands
    # do not fit in a web page without it
    export_draco_mesh_compression_enable=True,
    export_draco_mesh_compression_level=7,
    export_draco_position_quantization=12,
    export_draco_normal_quantization=8,
    export_draco_texcoord_quantization=12,
)

entry = {
    "id": ISLAND_ID,
    "radius": round(RADIUS, 2),
    "size": round(span, 3),
    "maxHeight": round(hi, 3),
    "minHeight": round(lo, 3),
    "triangles": tris,
    "kind": "generated",
    "mesh": ISLAND_ID + ".glb",
    "height": ISLAND_ID + "_height.png",
    "textured": True,
}
print("PREPARED " + json.dumps(entry))
