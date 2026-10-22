"""Blender headless: render one model from the four glTF axis directions, to learn
which side of a generated model faces the camera of its source image.

Run: blender -b -P probe_front.py -- <glb> <out_dir>
"""
import math
import os
import sys

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
GLB, OUT = argv[0], argv[1]
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)
meshes = [o for o in bpy.data.objects if o.type == "MESH"]
mn = Vector((1e9,) * 3)
mx = Vector((-1e9,) * 3)
for o in meshes:
    for c in o.bound_box:
        w = o.matrix_world @ Vector(c)
        for i in range(3):
            mn[i] = min(mn[i], w[i])
            mx[i] = max(mx[i], w[i])
centre, radius = (mn + mx) / 2, max(mx - mn) / 2

scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 360
scene.render.resolution_y = 260
world = bpy.data.worlds.new("w")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[1].default_value = 0.8
scene.world = world
scene.view_settings.view_transform = "Standard"
sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", type="SUN"))
sun.data.energy = 2.2
sun.rotation_euler = (math.radians(40), 0, math.radians(30))
scene.collection.objects.link(sun)
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
scene.collection.objects.link(cam)
scene.camera = cam

# Blender frame after glTF import: glTF +Z -> Blender -Y, glTF -Z -> Blender +Y
DIRS = {"gltf_plusZ": Vector((0, -1, 0)), "gltf_minusZ": Vector((0, 1, 0)),
        "gltf_plusX": Vector((1, 0, 0)), "gltf_minusX": Vector((-1, 0, 0))}
for name, d in DIRS.items():
    cam.location = centre + (d * math.cos(math.radians(30)) + Vector((0, 0, math.sin(math.radians(30))))) * radius * 4.2
    cam.rotation_euler = (centre - cam.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = os.path.join(OUT, "front_%s.png" % name)
    bpy.ops.render.render(write_still=True)
