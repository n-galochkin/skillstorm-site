"""Assemble the props into a harbour diorama and render it from a low 3/4 angle,
which is the only honest test of whether they belong in the reference painting.

    blender --background --python render_scene.py
"""
import bpy
import math
import os
import random
from mathutils import Vector

ROOT = os.path.dirname(os.path.abspath(__file__))
PROPS = os.path.normpath(os.path.join(ROOT, "..", "site", "assets", "props"))
RENDERS = os.path.join(ROOT, "renders")

CACHE = {}


def load(name):
    if name in CACHE:
        return CACHE[name]
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(PROPS, name + ".glb"))
    new = [o for o in bpy.data.objects if o not in before]
    meshes = [o for o in new if o.type == "MESH"]
    me = meshes[0].data
    for o in new:
        bpy.data.objects.remove(o, do_unlink=True)
    CACHE[name] = me
    return me


def put(name, x, y, z=0.0, rot=0.0, scale=1.0, tilt=0.0):
    """x,y,z are in the SITE's frame (Y up, +Z forward); Blender gets x, -z, y."""
    me = load(name)
    ob = bpy.data.objects.new(name + "_i", me)
    bpy.context.collection.objects.link(ob)
    ob.location = (x, -z, y)
    ob.rotation_euler = (tilt, 0, -rot)
    ob.scale = (scale, scale, scale)
    return ob


def world():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE"
    sc.render.resolution_x = 1280
    sc.render.resolution_y = 720
    sc.view_settings.view_transform = "Standard"
    sc.render.image_settings.file_format = "PNG"
    try:
        sc.eevee.taa_render_samples = 48
        sc.eevee.use_shadows = True
    except Exception:
        pass

    w = bpy.data.worlds.new("w")
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.26, 0.47, 0.70, 1.0)
    bg.inputs[1].default_value = 0.42
    sc.world = w

    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sun.data.energy = 2.6
    sun.data.angle = math.radians(5)
    sun.data.color = (1.0, 0.95, 0.86)
    sun.rotation_euler = (math.radians(50), 0, math.radians(-38))
    bpy.context.collection.objects.link(sun)

    fill = bpy.data.objects.new("fill", bpy.data.lights.new("fill", "SUN"))
    fill.data.energy = 0.35
    fill.data.color = (0.74, 0.86, 1.0)
    fill.rotation_euler = (math.radians(58), 0, math.radians(-60))
    bpy.context.collection.objects.link(fill)


def mat(name, rgb, rough=1.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    return m


def site_box(x0, x1, z0, z1, y0, y1, m):
    """A box given in SITE coordinates (Y up, +Z away), built in Blender space."""
    bpy.ops.mesh.primitive_cube_add(size=1)
    ob = bpy.context.active_object
    ob.location = ((x0 + x1) / 2, -(z0 + z1) / 2, (y0 + y1) / 2)
    ob.scale = (x1 - x0, z1 - z0, y1 - y0)
    ob.data.materials.append(m)
    return ob


def terrain():
    """Water in front, a sandy shore at z = 10 and a green headland behind it, so
    the boats float, the pier crosses the waterline and the town stands on land."""
    sand = mat("sand", (0.84, 0.72, 0.44))
    grass = mat("grass", (0.150, 0.34, 0.120))
    grass2 = mat("grass2", (0.110, 0.27, 0.095))
    rock = mat("rock", (0.33, 0.36, 0.40))

    bpy.ops.mesh.primitive_plane_add(size=900, location=(0, 0, 0))
    sea = bpy.context.active_object
    sea.data.materials.append(mat("sea", (0.018, 0.135, 0.225), 0.18))

    # beach: a wedge rising out of the water between z = 8 and z = 14
    bpy.ops.mesh.primitive_cube_add(size=1)
    w = bpy.context.active_object
    w.location = (0, -11.0, 0.70)
    w.scale = (190, 6.0, 1.40)
    w.rotation_euler = (math.radians(-11), 0, 0)
    w.data.materials.append(sand)

    site_box(-95, 95, 13.0, 30.0, 0.0, 1.45, sand)
    site_box(-95, 95, 19.0, 120.0, 0.0, 4.15, grass)
    site_box(-95, 95, 34.0, 120.0, 0.0, 7.0, grass2)
    # the hill the conifers stand on
    bpy.ops.mesh.primitive_cone_add(vertices=9, radius1=34, radius2=12, depth=22.0,
                                    location=(-2, -58, 10.0))
    bpy.context.active_object.data.materials.append(grass2)
    # a rock headland for the watchtower
    bpy.ops.mesh.primitive_cone_add(vertices=7, radius1=15, radius2=10, depth=16.0,
                                    location=(-40, -40, 6.0))
    bpy.context.active_object.data.materials.append(rock)


def camera(loc, look, lens=45):
    cd = bpy.data.cameras.new("cam")
    cd.lens = lens
    cam = bpy.data.objects.new("cam", cd)
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    cam.location = loc
    d = (Vector(look) - Vector(loc)).normalized()
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return cam


def build():
    rnd = random.Random(12)
    terrain()

    # --- harbour: a pier walking from the beach out over the water
    deck = 1.55
    for i in range(7):
        z = 11.0 - 2.0 * i
        put("pier_end" if i == 6 else "pier_straight", 2.0, deck, z, rot=0.0)
        if i in (2, 4):
            put("mooring_post" if i == 2 else "mooring_post_stone",
                2.85, deck, z + 0.2, rot=rnd.uniform(0, 6))
    put("boat_sail_a", -2.2, 0, 3.0, rot=math.radians(186))
    put("boat_sail_c", 6.3, 0, 0.5, rot=math.radians(8))
    put("boat_sail_b", -13.0, 0, -8.0, rot=math.radians(214))
    put("boat_sail_c", 17.0, 0, -12.0, rot=math.radians(150), scale=0.95)

    # --- the town along the shore
    for (x, z, nm, r, s) in ((-8.5, 17.5, "house_white_a", 178, 1.0),
                             (-2.0, 20.5, "house_white_b", 168, 0.95),
                             (7.5, 18.0, "house_white_c", 194, 1.0),
                             (15.0, 21.0, "house_white_a", 160, 0.92),
                             (-16.0, 21.5, "house_white_a", 192, 0.9),
                             (23.0, 24.5, "house_white_b", 150, 0.88),
                             (-25.0, 25.0, "house_white_c", 205, 0.9)):
        put(nm, x, 1.42, z, rot=math.radians(r), scale=s)
    put("lighthouse", 26.0, 1.42, 12.0, rot=math.radians(150))
    put("watchtower", -40.0, 13.6, 40.0, rot=math.radians(210), scale=1.05)
    put("stilt_hut", 14.0, 1.30, 4.0, rot=math.radians(192))
    put("stilt_hut", 19.0, 1.30, 1.0, rot=math.radians(178), scale=0.92)

    # --- ruins on the rise behind the town
    for (x, z, nm, r) in ((-33, 30, "ruin_arch", 22), (-39.0, 32, "ruin_column", 0),
                          (-28.0, 33.5, "ruin_column_broken", 50),
                          (-36, 36.0, "ruin_wall", 100)):
        put(nm, x, 4.15, z, rot=math.radians(r))

    # --- palms along the sand, conifers up the hill
    for i in range(18):
        x = rnd.uniform(-60, 60)
        if abs(x - 2) < 7:
            continue
        z = rnd.uniform(14.5, 19.0)
        put(rnd.choice(["palm_tall", "palm_bend", "palm_short",
                        "palm_fan_tall", "palm_fan_mid", "palm_fan_short"]),
            x, 1.42, z, rot=rnd.uniform(0, 6.28), scale=rnd.uniform(0.85, 1.2))
    for i in range(90):
        a = rnd.uniform(0, 6.28)
        r = rnd.uniform(3, 30)
        x = -2 + math.sin(a) * r
        z = 58 + math.cos(a) * r
        d = math.hypot(x + 2, z - 58)
        h = 21.0 - max(0.0, d - 12) * 0.52
        if h < 7.5 or d > 33:
            continue
        nm = rnd.choice(["conifer_spire_xl", "conifer_spire_l", "conifer_spire_m",
                         "conifer_spire_s", "conifer_xl", "conifer_l",
                         "conifer_m", "conifer_round"])
        put(nm, x, h, z, rot=rnd.uniform(0, 6.28), scale=rnd.uniform(0.8, 1.2))
    for i in range(34):
        x = rnd.uniform(-55, 55)
        z = rnd.uniform(15, 40)
        y = 1.42 if z < 19 else (4.15 if z < 34 else 7.0)
        put(rnd.choice(["bush_round", "bush_small", "rock_mossy"]),
            x, y, z, rot=rnd.uniform(0, 6.28), scale=rnd.uniform(0.7, 1.4))


def main():
    world()
    build()
    os.makedirs(RENDERS, exist_ok=True)
    shots = [
        ("scene_harbour", (14, 30, 11), (0, -18, 3), 50),
        ("scene_low", (-22, 9, 3.2), (8, -14, 3.2), 46),
        ("scene_wide", (52, 46, 34), (-4, -34, 6), 40),
        ("scene_boats", (-4, 22, 5.0), (-3, -4, 2.2), 62),
    ]
    for (nm, loc, look, lens) in shots:
        camera(loc, look, lens)
        bpy.context.scene.render.filepath = os.path.join(RENDERS, nm + ".png")
        bpy.ops.render.render(write_still=True)
        print("SCENE", nm)


main()
