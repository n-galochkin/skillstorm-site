"""Forest props.

Conifers and palms are taken from the Kenney Nature Kit (CC0) where the silhouette
is already right, recoloured into our palette, pivoted to the base and scaled to a
real height. The kit's glTF export mangles its greens, so colour comes from the
material NAME, not from the imported material colour -- the same trick site/kit.js
uses. Trees the kit does not cover are built from scratch here.
"""
import bpy
import bmesh
import math
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import propslib as pl
from propslib import Build, P, shade, hx

KIT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", "site", "assets", "kit"))

# Kenney material name -> our palette
MAP = {
    "leafsGreen": P["green"],
    "leafsDark": P["conifer"],
    "leafsFall": hx(0xD08A3A),
    "woodBark": P["wood"],
    "woodBarkDark": P["woodDark"],
    "wood": P["wood"],
    "woodDark": P["woodDark"],
    "woodInner": P["woodPale"],
    "stone": P["stone"],
    "stoneDark": P["stoneDark"],
    "dirt": P["stoneDark"],
    "dirtDark": P["woodDark"],
    "grass": P["green"],
    "colorRed": P["red"],
    "colorYellow": hx(0xE8B445),
    "_defaultMat": P["green"],
}

# name -> (kit file, palette override per material, target height in metres)
CONIFERS = {
    "conifer_xl": ("tree_pineTallA", {"leafsGreen": P["coniferDark"], "leafsDark": P["coniferDark"]}, 9.5),
    "conifer_l": ("tree_pineTallC", {"leafsGreen": P["conifer"], "leafsDark": P["conifer"]}, 7.2),
    "conifer_m": ("tree_pineDefaultA", {"leafsGreen": P["conifer"], "leafsDark": P["conifer"]}, 5.4),
    "conifer_s": ("tree_pineSmallB", {"leafsGreen": shade(P["conifer"], 1.04),
                                      "leafsDark": shade(P["conifer"], 1.04)}, 3.4),
    "conifer_round": ("tree_pineRoundA", {"leafsGreen": P["conifer"], "leafsDark": P["conifer"]}, 6.0),
}
PALM_BARK = {"woodBark": P["woodLight"], "woodBarkDark": P["wood"],
             "wood": P["woodLight"], "woodDark": P["wood"]}
PALMS = {
    "palm_tall": ("tree_palmDetailedTall",
                  dict(PALM_BARK, leafsGreen=P["green"], leafsDark=P["green"]), 7.4),
    "palm_bend": ("tree_palmBend",
                  dict(PALM_BARK, leafsGreen=P["green"], leafsDark=P["green"]), 6.0),
    "palm_short": ("tree_palmShort",
                   dict(PALM_BARK, leafsGreen=shade(P["green"], 1.08),
                        leafsDark=shade(P["green"], 1.08)), 4.3),
}
SHRUBS = {
    "rock_mossy": ("rock_largeA", {}, 1.5),
}


def convert(src, overrides, height, name):
    """Import a kit model, bake its material names to vertex colours, drop the
    pivot to the base of the trunk, and scale it to `height` metres."""
    pl.clear()
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(KIT, src + ".glb"))
    meshes = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
    if not meshes:
        print("MISSING", src)
        return None

    build = Build()
    for ob in meshes:
        ob.data.calc_loop_triangles()
        mw = ob.matrix_world
        mats = ob.data.materials
        for poly in ob.data.polygons:
            mi = poly.material_index
            mname = mats[mi].name.split(".")[0] if mi < len(mats) and mats[mi] else "_defaultMat"
            col = overrides.get(mname) or MAP.get(mname) or P["green"]
            pts = [tuple(mw @ ob.data.vertices[v].co) for v in poly.vertices]
            # a touch of variation per face so a flat canopy still has facets
            n = poly.normal
            f = 1.0 + 0.085 * max(-1.0, min(1.0, (n.z * 0.55 - n.y * 0.45)))
            build.face(pts, shade(col, f))

    ob = pl.finish(build, name, quiet=True)
    # pivot to base, centred on the trunk, scaled to the target height
    me = ob.data
    zs = [v.co.z for v in me.vertices]
    xs = [v.co.x for v in me.vertices]
    ys = [v.co.y for v in me.vertices]
    z0 = min(zs)
    h = max(zs) - z0
    k = height / h if h > 1e-4 else 1.0
    cx = (min(xs) + max(xs)) * 0.5
    cy = (min(ys) + max(ys)) * 0.5
    for v in me.vertices:
        v.co.x = (v.co.x - cx) * k
        v.co.y = (v.co.y - cy) * k
        v.co.z = (v.co.z - z0) * k
    return ob


def own_conifer(height=7.0, tiers=4, name="conifer_spire", trunk_r=0.17,
                r_base=1.55, col=P["conifer"], droop=0.14):
    """Our own stacked-cone conifer, for the dense dark forests in the painting.
    The kit's pines are rounder and read as oaks at a distance."""
    b = Build()
    b.frustum(0, height * 0.30, trunk_r * 1.35, trunk_r * 0.9, 6, P["woodDark"],
              cap_bot=P["woodDark"])
    z = height * 0.17
    span = height - z
    for t in range(tiers):
        u = t / (tiers - 1.0) if tiers > 1 else 0.0
        z0 = z + span * (t / tiers) * 0.88
        z1 = z0 + span * (1.0 / tiers) * 1.45
        r = r_base * (1.0 - 0.72 * u)
        c = shade(col, 1.0 + 0.09 * (t % 2) - 0.03 * u)
        # a skirt that flares down, which is what gives a fir its layered edge
        b.frustum(z0, z0 - span * droop * (1 - 0.5 * u), r, r * 0.62, 7, shade(c, 0.86),
                  phase=t * 0.4)
        b.frustum(z0 - span * droop * (1 - 0.5 * u), z0, r * 0.62, r, 7, shade(c, 0.86),
                  phase=t * 0.4, cap_bot=None)
        b.frustum(z0, z1, r, 0.0, 7, c, phase=t * 0.4)
    return b, name


def own_palm(height=6.4, name="palm_fan", lean=0.30, fronds=9, col=P["green"]):
    """Hand-built palm. Each frond is a drooping strip, not a flat kite: fronds
    that rise from the crown read as a star, which is what the first pass did."""
    b = Build()
    segs = 7
    rings = []
    for i in range(segs + 1):
        t = i / segs
        r = 0.21 - 0.095 * t
        x = lean * (t ** 1.7) * height * 0.22
        z = height * 0.78 * t
        rings.append([(x + math.cos(a * math.tau / 6) * r,
                       math.sin(a * math.tau / 6) * r, z) for a in range(6)])
    b.loft(rings, P["woodLight"], close=True,
           shade_fn=lambda k, i, c: shade(P["woodLight"] if k % 2 else P["woodPale"],
                                          1.0 + 0.10 * math.cos(i * math.tau / 6 + 1.6)))
    top = rings[-1]
    tx = sum(p[0] for p in top) / 6
    tz = top[0][2]
    b.face(top, P["woodPale"])
    # crown knuckle, so the fronds do not sprout out of a bare pole
    b.push_trs(loc=(tx, 0, tz - 0.08))
    b.frustum(0, 0.30, 0.26, 0.17, 6, P["woodLight"], cap_top=P["woodPale"])
    b.pop()

    L = height * 0.50
    nsg = 4
    for f in range(fronds):
        a = f * math.tau / fronds + 0.27
        ca, sa = math.cos(a), math.sin(a)
        px, py = -sa, ca
        rise = 0.17 + 0.07 * ((f % 3) - 1)      # some fronds arch higher than others
        c = shade(col, 0.84 + 0.24 * ((f % 3) / 2.0))
        # the rib arcs up then falls away past the horizontal
        def spine(t):
            s_ = t * L * (1.0 - 0.14 * t)
            return (tx + ca * s_, sa * s_,
                    tz + 0.20 + L * (rise * t - (rise + 0.72) * t * t))
        prev = None
        for k in range(nsg + 1):
            t = k / nsg
            w = (L * 0.30) * math.sin(math.pi * min(1.0, 0.30 + t * 0.68)) * (1 - 0.28 * t)
            cx, cy, cz = spine(t)
            cur = ((cx + px * w, cy + py * w, cz - w * 0.25),
                   (cx, cy, cz),
                   (cx - px * w, cy - py * w, cz - w * 0.25))
            if prev:
                cc = shade(c, 1.0 - 0.07 * k)
                b.face2([prev[0], cur[0], cur[1], prev[1]], cc)
                b.face2([prev[1], cur[1], cur[2], prev[2]], shade(cc, 0.90))
            prev = cur
        b.strut(spine(0.0), spine(0.55), 0.032, shade(P["wood"], 1.12), n=3)
    for (dx, dy) in ((0.24, 0.11), (-0.15, 0.24), (0.05, -0.26)):
        b.push_trs(loc=(tx + dx, dy, tz - 0.30))
        b.frustum(0, 0.23, 0.125, 0.105, 6, P["woodDark"], cap_top=P["woodDark"],
                  cap_bot=P["woodDark"])
        b.pop()
    return b, name


def own_bush(name="bush_round", r=0.62, lobes=3):
    """A clump of leafy lobes. The kit's bushLarge opens like a cup from above."""
    b = Build()
    for k in range(lobes):
        a = k * math.tau / lobes + 0.4
        rr = r * (0.78 + 0.30 * ((k % 2)))
        cx, cy = math.cos(a) * r * 0.46, math.sin(a) * r * 0.46
        c = shade(P["green"] if k % 2 else P["greenDark"], 1.0 + 0.06 * k)
        b.push_trs(loc=(cx, cy, 0))
        b.frustum(0.0, rr * 0.55, rr * 0.80, rr, 7, c, phase=a)
        b.frustum(rr * 0.55, rr * 1.25, rr, rr * 0.26, 7, shade(c, 1.08),
                  cap_top=shade(c, 1.14), phase=a)
        b.pop()
    return b, name


def main():
    for name, (src, ov, h) in list(CONIFERS.items()) + list(PALMS.items()) + list(SHRUBS.items()):
        ob = convert(src, ov, h, name)
        if ob:
            pl.export(ob, name)
    for (h, tiers, nm, rb) in ((9.8, 5, "conifer_spire_xl", 1.75),
                               (6.9, 4, "conifer_spire_l", 1.50),
                               (4.6, 4, "conifer_spire_m", 1.18),
                               (2.9, 3, "conifer_spire_s", 0.88)):
        pl.clear()
        b, nmm = own_conifer(height=h, tiers=tiers, name=nm, r_base=rb,
                             trunk_r=0.10 + h * 0.012)
        pl.emit(b, nmm)
    for (h, nm, ln, nf) in ((7.8, "palm_fan_tall", 0.42, 10), (5.8, "palm_fan_mid", 0.20, 9),
                            (4.2, "palm_fan_short", 0.62, 8)):
        pl.clear()
        b, nmm = own_palm(height=h, name=nm, lean=ln, fronds=nf)
        pl.emit(b, nmm)
    for (nm, rr, lb) in (("bush_round", 0.70, 3), ("bush_small", 0.44, 3)):
        pl.clear()
        b, nmm = own_bush(name=nm, r=rr, lobes=lb)
        pl.emit(b, nmm)


main()
