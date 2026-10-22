"""Render every .glb in site/assets/props from a 3/4 view, then tile the frames
into contact sheets so they can be looked at next to the reference painting.

    blender --background --python render_sheet.py -- [name ...]
"""
import bpy
import sys
import os
import math
import glob
from mathutils import Vector

ROOT = os.path.dirname(os.path.abspath(__file__))
PROPS = os.path.normpath(os.path.join(ROOT, "..", "site", "assets", "props"))
RENDERS = os.path.join(ROOT, "renders")
SIZE = 460


def clear_all():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def setup_world():
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE"
    sc.render.resolution_x = SIZE
    sc.render.resolution_y = SIZE
    sc.render.film_transparent = False
    sc.view_settings.view_transform = "Standard"
    sc.render.image_settings.file_format = "PNG"
    try:
        sc.eevee.taa_render_samples = 32
    except Exception:
        pass

    world = bpy.data.worlds.new("w")
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.52, 0.62, 0.72, 1.0)   # neutral sky, no colour cast
    bg.inputs[1].default_value = 0.30
    bpy.context.scene.world = world

    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sun.data.energy = 2.25
    sun.data.angle = math.radians(8)
    sun.data.color = (1.0, 0.96, 0.88)
    sun.rotation_euler = (math.radians(52), 0, math.radians(38))
    bpy.context.collection.objects.link(sun)

    fill = bpy.data.objects.new("fill", bpy.data.lights.new("fill", "SUN"))
    fill.data.energy = 0.32
    fill.data.color = (0.82, 0.88, 1.0)
    fill.rotation_euler = (math.radians(60), 0, math.radians(-150))
    bpy.context.collection.objects.link(fill)

    # ground plane so the silhouette sits on something
    bpy.ops.mesh.primitive_plane_add(size=400)
    gp = bpy.context.active_object
    gp.name = "Plane"
    m = bpy.data.materials.new("ground")
    m.use_nodes = True
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.42, 0.58, 0.40, 1)
    m.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 1.0
    gp.data.materials.append(m)
    return gp


def frame_object(objs, grounded=True):
    """3/4 camera framing the combined bounds."""
    pts = []
    for ob in objs:
        for c in ob.bound_box:
            pts.append(ob.matrix_world @ Vector(c))
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    centre = (lo + hi) * 0.5
    radius = max((hi - lo).length * 0.5, 0.4)

    cam_data = bpy.data.cameras.new("cam")
    cam_data.lens = 58
    cam = bpy.data.objects.new("cam", cam_data)
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam

    az = math.radians(-35)
    el = math.radians(26)
    dist = radius * 3.05
    d = Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)))
    cam.location = centre + d * dist
    look = (centre - cam.location).normalized()
    cam.rotation_euler = look.to_track_quat("-Z", "Y").to_euler()
    return cam, lo, hi


def render_one(path, out):
    clear_all()
    setup_world()
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
    if not new:
        print("no mesh in", path)
        return None
    # The importer does not always wire COLOR_0 into the shader; force a material
    # that shows exactly what the site will show.
    vcm = bpy.data.materials.new("vc")
    vcm.use_nodes = True
    nt = vcm.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    ca = nt.nodes.new("ShaderNodeVertexColor")
    layer = None
    for o in new:
        if o.data.color_attributes:
            layer = o.data.color_attributes[0].name
            break
    ca.layer_name = layer or "Color"
    nt.links.new(ca.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.95
    bsdf.inputs["Metallic"].default_value = 0.0
    for o in new:
        o.data.materials.clear()
        o.data.materials.append(vcm)
    tris = sum(len(o.data.loop_triangles) if o.data.loop_triangles else
               sum(len(p.vertices) - 2 for p in o.data.polygons) for o in new)
    for o in new:
        o.data.calc_loop_triangles()
    tris = sum(len(o.data.loop_triangles) for o in new)
    cam, lo, hi = frame_object(new)
    # Drop the ground to the model's lowest point: pier decks sit at z = 0 and a
    # ground plane at z = 0 swallows them whole.
    gp = bpy.data.objects.get("Plane")
    if gp:
        gp.location.z = min(0.0, lo.z) - 0.02
    bpy.context.scene.render.filepath = out
    bpy.ops.render.render(write_still=True)
    return tris


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    os.makedirs(RENDERS, exist_ok=True)
    files = sorted(glob.glob(os.path.join(PROPS, "*.glb")))
    if args:
        files = [f for f in files if os.path.splitext(os.path.basename(f))[0] in args]
    counts = {}
    for f in files:
        name = os.path.splitext(os.path.basename(f))[0]
        out = os.path.join(RENDERS, name + ".png")
        t = render_one(f, out)
        counts[name] = t
        print("RENDER %-26s tris=%s" % (name, t))
    print("TRICOUNTS " + repr(counts))


main()
