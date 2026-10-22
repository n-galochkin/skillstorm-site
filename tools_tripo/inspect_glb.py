"""Blender headless: load a generated model, report its numbers, render a few views.

Run: blender -b -P inspect_glb.py -- <glb> <out_dir> [name]
"""
import math
import os
import sys

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
GLB, OUT = argv[0], argv[1]
NAME = argv[2] if len(argv) > 2 else os.path.splitext(os.path.basename(GLB))[0]
os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)

meshes = [o for o in bpy.data.objects if o.type == "MESH"]
tris = 0
for o in meshes:
    o.data.calc_loop_triangles()
    tris += len(o.data.loop_triangles)

mn = Vector((1e9, 1e9, 1e9))
mx = Vector((-1e9, -1e9, -1e9))
for o in meshes:
    for c in o.bound_box:
        w = o.matrix_world @ Vector(c)
        for i in range(3):
            mn[i] = min(mn[i], w[i])
            mx[i] = max(mx[i], w[i])
size = mx - mn
centre = (mx + mn) / 2
radius = max(size) / 2

print("INSPECT objects=%d tris=%d" % (len(meshes), tris))
print("INSPECT size=%.3f %.3f %.3f" % (size.x, size.y, size.z))
print("INSPECT images=%s" % [(i.name, tuple(i.size)) for i in bpy.data.images])
print("INSPECT materials=%s" % [m.name for m in bpy.data.materials])

scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 700
scene.render.resolution_y = 560
scene.render.film_transparent = False
world = bpy.data.worlds.new("w")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.83, 0.88, 0.93, 1)
world.node_tree.nodes["Background"].inputs[1].default_value = 0.8
scene.world = world
scene.view_settings.view_transform = "Standard"

light_data = bpy.data.lights.new("sun", type="SUN")
light_data.energy = 2.2
light = bpy.data.objects.new("sun", light_data)
light.rotation_euler = (math.radians(50), 0, math.radians(35))
scene.collection.objects.link(light)

cam_data = bpy.data.cameras.new("cam")
cam_data.lens = 50
cam = bpy.data.objects.new("cam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam

VIEWS = {
    "persp": (math.radians(62), math.radians(35)),
    "top": (math.radians(2), math.radians(0)),
    "side": (math.radians(88), math.radians(100)),
}
for label, (polar, azim) in VIEWS.items():
    d = radius * 4.6
    cam.location = centre + Vector((
        d * math.sin(polar) * math.cos(azim),
        d * math.sin(polar) * math.sin(azim),
        d * math.cos(polar),
    ))
    direction = centre - cam.location
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = os.path.join(OUT, "%s_%s.png" % (NAME, label))
    bpy.ops.render.render(write_still=True)
    print("INSPECT wrote", scene.render.filepath)
