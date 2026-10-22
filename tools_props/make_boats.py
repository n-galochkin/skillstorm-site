"""Three wooden sailing boats, modelled after the key art's longboat.

Bow points -Y in Blender, i.e. +Z once exported. Waterline is z = 0.
"""
import bpy
import math
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import propslib as pl
from propslib import Build, P, shade


def lit_back(col, f=1.30):
    """Reverse-side albedo for cloth. Brighter AND warmer: the shaded side of a
    sail is lit almost entirely by blue sky, so a neutral cream albedo there comes
    back cold grey. Taking the blue down pulls it back to cloth."""
    c = shade(col, f)
    return (min(1.0, c[0] * 1.02), c[1] * 0.96, c[2] * 0.74)

TAU = math.pi * 2


def smoothstep(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def hull(b, L=7.0, beam=2.25, draft=0.60, free=0.62, sheer=0.46, bow_extra=0.26,
         ns=11, planks=(P["woodPale"], P["woodLight"], P["wood"])):
    """Lofted clinker hull. Returns (bow_top, stern_top) reference points."""
    rings = []
    inner = []
    for s in range(ns):
        u = s / (ns - 1.0)             # 0 = stern, 1 = bow
        t = 2 * u - 1
        y = (0.5 - u) * L
        # fullness: nearly parallel-sided amidships, fine only at the very ends,
        # which is what makes it read as a beamy boat and not a canoe
        f = max(0.10, (1 - abs(t) ** 3.0) ** 0.5 * (1 - 0.10 * t))
        w = beam * 0.5 * f
        zk = -draft * (1 - 0.80 * t * t)                 # keel rocker
        zs = free + sheer * t * t + bow_extra * max(0.0, t) ** 3
        h = zs - zk

        def lvl(fx, fz):
            return (fx * w, y, zk + fz * h)

        # round-bilge box section: near-vertical topsides, a soft turn, flat floor
        side = [lvl(1.00, 1.00), lvl(0.995, 0.66), lvl(0.86, 0.33), lvl(0.44, 0.07)]
        ring = [(x, yy, zz) for (x, yy, zz) in side]
        ring = ring + [(0.0, y, zk)] + [(-x, yy, zz) for (x, yy, zz) in reversed(side)]
        rings.append(ring)
        iw = 0.86
        inner.append([(x * iw, yy, zz if abs(x) > 1e-6 else zk + 0.30 * h)
                      for (x, yy, zz) in ring])

    def strake(k, i, col):
        # i indexes around the ring: 0..3 starboard top-down, 4 keel, 5..8 port.
        # Each lane is a plank band, light at the gunwale and dark at the keel,
        # which is what gives the hull its clinker stripes without any texture.
        lane = i if i < 4 else (8 - i)
        c = planks[min(lane, len(planks) - 1)]
        if lane >= 3:
            c = shade(planks[-1], 0.90)
        return shade(c, 1.04 if i < 4 else 0.92)

    b.loft(rings, P["wood"], close=False, shade_fn=strake)

    # inner shell: rail lip down to a floor, dark so the boat reads open
    b.loft(inner, shade(P["woodDark"], 0.78), close=False,
           shade_fn=lambda k, i, c: shade(c, 1.0 + 0.06 * (0 if i < 4 else 1)))
    # rail strip between outer gunwale and inner lip
    for k in range(ns - 1):
        for idx in (0, len(rings[0]) - 1):
            a0, a1 = rings[k][idx], rings[k + 1][idx]
            i0, i1 = inner[k][idx], inner[k + 1][idx]
            quad = [a0, a1, i1, i0] if idx == 0 else [i0, i1, a1, a0]
            b.face(quad, P["woodPale"])
    # close the hull ends (bow / stern transom) and the floor
    b.face(list(reversed(rings[0])), shade(P["wood"], 0.92))
    b.face(rings[-1], shade(P["wood"], 0.92))
    b.face([(p[0], p[1], p[2]) for p in inner[0]], shade(P["woodDark"], 0.95))
    b.face(list(reversed(inner[-1])), shade(P["woodDark"], 0.95))

    bow_y = -L * 0.5
    stern_y = L * 0.5
    bow_z = free + sheer + bow_extra
    stern_z = free + sheer
    return (0.0, bow_y, bow_z), (0.0, stern_y, stern_z)


def post(b, base, reach, height, col, r0=0.16, r1=0.095, lean=0.78, steps=7):
    """Carved stem/stern post as a quadratic Bezier: leaves the hull vertically,
    then leans out by `reach` to a tip `height` above the gunwale. Controlling the
    horizontal reach directly is what keeps it a stem and not a fishing rod."""
    import mathutils
    V = mathutils.Vector
    P0 = V(base)
    P2 = V((base[0], base[1] + reach, base[2] + height))
    P1 = V((base[0], base[1] + reach * 0.08, base[2] + height * lean))

    def bez(t):
        return (1 - t) ** 2 * P0 + 2 * (1 - t) * t * P1 + t * t * P2

    rings = []
    for i in range(steps + 1):
        t = i / steps
        p = bez(t)
        d = bez(min(1.0, t + 0.02)) - bez(max(0.0, t - 0.02))
        d = d.normalized() if d.length > 1e-6 else V((0, 0, 1))
        r = r0 + (r1 - r0) * (t ** 0.75)
        ly, lz = d.y * r * 1.45, d.z * r * 1.45
        rings.append([
            (p.x - r * 0.50, p.y - ly, p.z - lz), (p.x + r * 0.50, p.y - ly, p.z - lz),
            (p.x + r * 0.50, p.y + ly, p.z + lz), (p.x - r * 0.50, p.y + ly, p.z + lz),
        ])
    b.loft(rings, col, close=True,
           shade_fn=lambda k, i, c: shade(c, (1.10, 0.92, 0.82, 1.00)[i]))
    b.face(rings[-1], shade(col, 1.12))
    return (P2.x, P2.y, P2.z)


def square_sail(b, x_half, z_top, z_bot, belly=0.0, nx=5, nz=4, col=P["sail"],
                foot_scoop=0.10, y0=0.0):
    """Bellied square sail hanging from a yard, bulging toward -Y (forward)."""
    grid = []
    for j in range(nz + 1):
        tz = j / nz
        row = []
        for i in range(nx + 1):
            tx = i / nx
            x = (tx - 0.5) * 2 * x_half
            z = z_top + (z_bot - z_top) * tz
            z += foot_scoop * math.sin(math.pi * tx) * smoothstep(tz)
            # one clean barrel-shaped belly: full across the width, easing in at
            # the head so the cloth still touches the yard
            bl = -belly * math.sin(math.pi * tx) ** 0.75 * smoothstep(min(1.0, tz * 1.9))
            row.append((x * (1.0 + 0.13 * tz), y0 + bl, z))
        grid.append(row)
    for j in range(nz):
        for i in range(nx):
            q = [grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]]
            # flat shading already gives the belly its gradient; tinting on top of
            # it is what turned the cloth into patchwork
            b.face2(q, col, back=lit_back(col))
    return grid


def tri_sail(b, luff_top, luff_bot, clew, belly=0.22, n=4, col=P["sail"],
             axis=(0.0, -1.0, 0.0)):
    """Triangular sail (jib / lateen) between three points, bellied along -Y."""
    import mathutils
    A, B, C = [mathutils.Vector(p) for p in (luff_top, luff_bot, clew)]

    def pt(a, bb):
        """Barycentric point, pushed to -Y by a bubble that is zero on all three
        edges and fullest in the middle: one clean belly, no crumple."""
        p = A + (B - A) * a + (C - A) * bb
        g = 1.0 - a - bb
        k = belly * 6.75 * max(0.0, a) * max(0.0, bb) * max(0.0, g)
        return (p.x + axis[0] * k, p.y + axis[1] * k, p.z + axis[2] * k)

    for j in range(n):
        a0, a1 = j / n, (j + 1) / n
        for i in range(n - j):
            s0, s1 = i / n, (i + 1) / n
            bk = lit_back(col)
            b.face2([pt(a0, s0), pt(a1, s0), pt(a0, s1)], col, back=bk)
            if i < n - j - 1:
                b.face2([pt(a1, s0), pt(a1, s1), pt(a0, s1)], col, back=bk)
    return None


def pennant(b, top, length=1.15, col=P["red"]):
    x, y, z = top
    pts = [
        (x, y, z), (x, y - length * 0.18, z + 0.30), (x, y - length, z + 0.18),
        (x, y - length * 0.92, z - 0.02), (x, y - length * 0.2, z - 0.22), (x, y, z - 0.30),
    ]
    b.face2(pts, col, back=lit_back(col, 1.22))
    # a small fold so it is not a dead-flat card
    b.face2([(x, y - length * 0.2, z - 0.22), (x, y - length * 0.92, z - 0.02),
             (x + 0.0, y - length * 0.55, z - 0.30)], shade(col, 0.78))


def shields(b, L, beam, free, sheer, ys, col_a=P["red"], col_b=P["sail"]):
    for k, yy in enumerate(ys):
        t = 2 * ((0.5 - yy / L)) - 1
        f = max(0.085, (1 - t * t) ** 0.42 * (1 - 0.14 * t))
        w = beam * 0.5 * f
        z = free + sheer * t * t * 0.6 + 0.02
        for sx in (1, -1):
            b.push_trs(loc=(sx * (w + 0.02), yy, z), rot=(0, 0, math.pi / 2 if sx > 0 else -math.pi / 2))
            c = col_a if (k + (sx > 0)) % 2 == 0 else col_b
            b.disc(0.36, 10, c, rim=P["iron"], thick=0.08)
            b.push_trs(loc=(0, -0.01, 0))
            b.disc(0.095, 6, P["iron"], thick=0.07)
            b.pop()
            b.pop()


def crates(b, spots):
    for (x, y, z, s, rot) in spots:
        b.push_trs(loc=(x, y, z), rot=(0, 0, rot))
        b.box((-s, -s, 0), (s, s, s * 1.75), P["woodLight"], top=P["woodPale"])
        b.box((-s * 1.04, -s * 1.04, s * 0.72), (s * 1.04, s * 1.04, s * 0.92), P["woodDark"])
        b.pop()


def oars(b, ys, w, z):
    for yy in ys:
        for sx in (1, -1):
            b.strut((sx * w, yy, z), (sx * (w + 1.5), yy + 0.55, z - 0.55), 0.045, P["woodLight"], n=4)
            b.push_trs(loc=(sx * (w + 1.45), yy + 0.52, z - 0.52), rot=(0, 0, 0.38 * -sx))
            b.box((-0.03, -0.30, -0.14), (0.03, 0.30, 0.14), P["woodPale"])
            b.pop()


# ---------------------------------------------------------------- variants
def boat_a():
    """The key-art longboat: single mast, square cream sail, red pennant, shields."""
    b = Build()
    L, beam, free, sheer = 7.2, 2.95, 0.82, 0.42
    bow, stern = hull(b, L=L, beam=beam, draft=0.55, free=free, sheer=sheer, bow_extra=0.30)

    bow_tip = post(b, bow, reach=-0.46, height=1.42, col=P["woodLight"], r0=0.19, r1=0.105)
    stern_tip = post(b, stern, reach=0.40, height=1.20, col=P["woodLight"], r0=0.19, r1=0.105)

    # thwarts
    for yy in (-1.6, -0.1, 1.4):
        b.box((-0.92, yy - 0.10, 0.44), (0.92, yy + 0.10, 0.56), P["woodLight"], top=P["woodPale"])

    my = -0.30
    mast_top = 5.20
    b.push_trs(loc=(0, my, 0))
    b.frustum(0.30, mast_top, 0.135, 0.085, 6, P["woodLight"], cap_top=P["woodPale"],
              off1=(0, -0.05), phase=math.pi / 6)
    b.pop()
    b.box((-0.24, my - 0.26, 0.26), (0.24, my + 0.26, 0.62), P["woodDark"], top=P["wood"])

    # yard across the beam — thick, and wider than the hull like in the key art
    yard_z = 4.42
    yard_half = 1.78
    b.strut((-yard_half, my - 0.05, yard_z - 0.03), (yard_half, my - 0.05, yard_z + 0.03),
            0.085, P["woodPale"], n=6)
    for sx in (1, -1):   # end knobs
        b.push_trs(loc=(sx * yard_half, my - 0.05, yard_z))
        b.frustum(-0.07, 0.07, 0.11, 0.11, 6, P["woodPale"], cap_top=P["woodPale"],
                  cap_bot=P["woodPale"])
        b.pop()
    # cross-brace block below the yard (the key art's mast cross)
    b.box((-0.19, my - 0.22, yard_z + 0.10), (0.19, my + 0.16, yard_z + 0.34), P["woodPale"])

    square_sail(b, x_half=1.66, z_top=yard_z - 0.12, z_bot=1.38, belly=0.72,
                nx=6, nz=5, y0=my - 0.12, foot_scoop=0.22)

    pennant(b, (0.0, my - 0.08, mast_top - 0.10), length=1.25)

    head = (0.0, my - 0.06, mast_top - 0.30)
    b.strut(head, (0.0, bow_tip[1] + 0.05, bow_tip[2] - 0.08), 0.030, P["rope"], n=3)
    b.strut(head, (0.0, stern_tip[1] - 0.05, stern_tip[2] - 0.08), 0.030, P["rope"], n=3)
    for sx in (1, -1):
        b.strut(head, (sx * 1.00, my + 0.70, free + 0.44), 0.028, P["rope"], n=3)
        b.strut((sx * (yard_half - 0.04), my - 0.05, yard_z), (sx * 0.95, my + 1.75, free + 0.34),
                0.022, P["rope"], n=3)

    shields(b, L, beam, free, sheer, ys=(0.85, 1.75, 2.55))
    return b, "boat_sail_a"


def boat_b():
    """Bigger trader: raised stern deck, square mainsail plus a jib, deck cargo."""
    b = Build()
    L, beam, free, sheer = 9.0, 3.35, 0.80, 0.50
    bow, stern = hull(b, L=L, beam=beam, draft=0.78, free=free, sheer=sheer,
                      bow_extra=0.34, ns=11)

    bow_tip = post(b, bow, reach=-0.58, height=1.70, col=P["woodLight"], r0=0.21, r1=0.115)
    stern_tip = post(b, stern, reach=0.44, height=1.08, col=P["woodLight"], r0=0.21, r1=0.115)

    # raised stern deck with a rail
    b.box((-0.95, 2.05, 0.74), (0.95, 3.45, 0.92), P["woodLight"], top=P["woodPale"])
    for sx in (1, -1):
        b.strut((sx * 0.92, 2.10, 0.92), (sx * 0.92, 3.35, 0.92), 0.05, P["woodPale"], n=4)
        for yy in (2.2, 2.8, 3.3):
            b.strut((sx * 0.92, yy, 0.74), (sx * 0.92, yy, 0.96), 0.045, P["woodPale"], n=4)

    my = -0.20
    mast_top = 6.10
    b.push_trs(loc=(0, my, 0))
    b.frustum(0.25, mast_top, 0.135, 0.082, 6, P["woodLight"], cap_top=P["woodPale"], off1=(0, -0.08))
    b.pop()
    b.box((-0.24, my - 0.24, 0.20), (0.24, my + 0.24, 0.52), P["woodDark"])

    yard_z = 5.15
    b.strut((-1.95, my - 0.09, yard_z), (1.95, my - 0.09, yard_z), 0.075, P["woodPale"], n=5)
    square_sail(b, x_half=1.82, z_top=yard_z - 0.10, z_bot=1.75, belly=0.68,
                nx=5, nz=4, y0=my - 0.12, foot_scoop=0.20)
    # crow's nest: a ring sitting on cross-braces, not a cup stuck to the mast
    nest_z = 5.35
    for sx in (1, -1):
        b.strut((0, my, nest_z - 0.50), (sx * 0.40, my, nest_z + 0.04), 0.045, P["woodLight"], n=4)
        b.strut((0, my, nest_z - 0.50), (0, my + sx * 0.40, nest_z + 0.04), 0.045, P["woodLight"], n=4)
    b.push_trs(loc=(0, my, nest_z))
    b.frustum(0, 0.06, 0.42, 0.42, 8, P["woodLight"], cap_bot=P["woodDark"], cap_top=P["wood"])
    b.frustum(0.06, 0.38, 0.42, 0.46, 8, P["woodPale"], cap_top=P["woodPale"])
    b.pop()
    pennant(b, (0.0, my - 0.10, mast_top - 0.14), length=1.3)

    head = (0.0, my - 0.08, mast_top - 0.55)
    fore = (0.0, bow_tip[1] + 0.06, bow_tip[2] - 0.06)
    b.strut(head, fore, 0.028, P["rope"], n=3)
    b.strut(head, (0.0, stern_tip[1] - 0.06, stern_tip[2] - 0.05), 0.028, P["rope"], n=3)
    for sx in (1, -1):
        b.strut(head, (sx * 1.05, my + 0.75, free + 0.60), 0.026, P["rope"], n=3)

    # jib on the forestay
    # jib: a modest foresail whose luff lies on the forestay, set ahead of the mast
    def on_stay(t):
        return tuple(head[i] + (fore[i] - head[i]) * t for i in range(3))
    tri_sail(b, luff_top=on_stay(0.30), luff_bot=on_stay(0.92),
             clew=(0.30, my - 1.55, 1.70), belly=0.34, n=4, axis=(0.35, -0.94, 0.0))

    crates(b, [(-0.38, 1.25, 0.30, 0.26, 0.2), (0.36, 1.52, 0.30, 0.22, -0.4),
               (-0.08, 0.55, 0.30, 0.24, 0.6)])
    # barrels
    for (x, y) in ((0.46, 0.62), (-0.48, 1.92)):
        b.push_trs(loc=(x, y, 0.30))
        b.frustum(0, 0.52, 0.22, 0.22, 8, P["wood"], cap_top=P["woodPale"])
        b.cyl(0.10, 0.16, 0.235, 8, P["iron"])
        b.cyl(0.36, 0.42, 0.235, 8, P["iron"])
        b.pop()

    shields(b, L, beam, free, sheer, ys=(0.4, 1.4, 2.4), col_a=P["red"], col_b=P["stone"])
    return b, "boat_sail_b"


def boat_c():
    """Small fishing sloop with a lateen sail — the white triangles in the painting."""
    b = Build()
    L, beam, free, sheer = 6.1, 2.35, 0.62, 0.34
    bow, stern = hull(b, L=L, beam=beam, draft=0.52, free=free, sheer=sheer,
                      bow_extra=0.20, ns=9,
                      planks=(shade(P["woodPale"], 1.06), P["woodPale"], P["woodLight"]))

    bow_tip = post(b, bow, reach=-0.36, height=1.00, col=P["woodPale"], r0=0.15, r1=0.09)
    post(b, stern, reach=0.30, height=0.74, col=P["woodPale"], r0=0.15, r1=0.09)

    for yy in (-1.2, 0.25, 1.5):
        b.box((-0.66, yy - 0.08, 0.22), (0.66, yy + 0.08, 0.31), P["woodLight"], top=P["woodPale"])

    my = -0.1
    mast_top = 4.15
    b.push_trs(loc=(0, my, 0))
    b.frustum(0.18, mast_top, 0.095, 0.060, 6, P["woodPale"], cap_top=P["woodPale"], off1=(0, -0.10))
    b.pop()
    b.box((-0.17, my - 0.17, 0.14), (0.17, my + 0.17, 0.36), P["woodDark"])

    # slanted lateen yard
    # the boom is swung out to starboard, as it would be on a reach: that cants the
    # sail plane so it catches the light instead of reading as an edge-on fin
    yA = (-0.12, my - 2.05, 0.98)
    yB = (0.0, my + 0.70, 4.08)
    clew = (1.05, my + 2.00, 1.08)
    b.strut(yA, yB, 0.062, P["woodPale"], n=5)
    tri_sail(b, luff_top=yB, luff_bot=yA, clew=clew, belly=0.46, n=5,
             axis=(0.62, -0.78, 0.0))
    # boom along the foot
    b.strut(yA, clew, 0.048, P["woodPale"], n=4)

    pennant(b, (0.0, my - 0.10, mast_top - 0.10), length=0.85, col=P["red"])
    head = (0.0, my - 0.08, mast_top - 0.30)
    b.strut(head, (0.0, bow_tip[1] + 0.04, bow_tip[2] - 0.04), 0.022, P["rope"], n=3)
    for sx in (1, -1):
        b.strut(head, (sx * 0.78, my + 0.50, free + 0.30), 0.020, P["rope"], n=3)
    b.strut(clew, (0.72, my + 2.35, free + 0.22), 0.018, P["rope"], n=3)

    # fishing clutter: a net roll and two crates
    crates(b, [(-0.30, 1.45, 0.24, 0.20, 0.3), (0.34, 1.80, 0.24, 0.17, -0.5)])
    b.push_trs(loc=(0.34, -1.45, 0.30), rot=(math.pi / 2, 0, 0.18))
    b.frustum(0, 0.40, 0.19, 0.19, 7, P["rope"], cap_top=shade(P["rope"], 0.8),
              cap_bot=shade(P["rope"], 0.8))
    b.pop()
    return b, "boat_sail_c"


def main():
    for fn in (boat_a, boat_b, boat_c):
        pl.clear()
        b, name = fn()
        pl.emit(b, name)


main()
