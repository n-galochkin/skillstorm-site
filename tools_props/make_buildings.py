"""Harbour-town buildings: white houses with red tile roofs, a lighthouse,
a stone watchtower and a stilt hut over the water.

Front faces -Y in Blender (= +Z after export). Base sits at z = 0.
"""
import math
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import propslib as pl
from propslib import Build, P, shade

TAU = math.pi * 2


# ----------------------------------------------------------------- pieces
def roof(b, x0, x1, y0, y1, zb, zt, col=P["roof"], over=0.26, thick=0.16,
         bands=4, ridge=True, gable=P["wall"]):
    """Pitched roof with an overhang. The slopes are split into horizontal bands
    of alternating shade, which is what makes the tiles read without a texture."""
    xa, xb = x0 - over, x1 + over
    ya, yb = y0 - over, y1 + over
    ym = (ya + yb) * 0.5
    light = shade(col, 1.10)
    dark = shade(col, 0.80)

    for side, yedge in ((-1, ya), (1, yb)):
        base = col if side < 0 else shade(col, 0.84)
        for k in range(bands):
            t0, t1 = k / bands, (k + 1) / bands
            yy0 = yedge + (ym - yedge) * t0
            yy1 = yedge + (ym - yedge) * t1
            zz0 = zb + (zt - zb) * t0
            zz1 = zb + (zt - zb) * t1
            c = shade(base, 1.0 if k % 2 == 0 else 0.90)
            quad = [(xa, yy0, zz0), (xb, yy0, zz0), (xb, yy1, zz1), (xa, yy1, zz1)]
            b.face(quad if side < 0 else list(reversed(quad)), c)
        # underside of the eave
        q = [(xa, yedge, zb - thick), (xa, ym, zt - thick), (xb, ym, zt - thick), (xb, yedge, zb - thick)]
        b.face(q if side < 0 else list(reversed(q)), dark)
        # fascia along the eave
        q = [(xa, yedge, zb), (xb, yedge, zb), (xb, yedge, zb - thick), (xa, yedge, zb - thick)]
        b.face(q if side < 0 else list(reversed(q)), light)
    # gable ends
    for xx, flip in ((xa, False), (xb, True)):
        for (ye, ) in ((ya, ), (yb, )):
            pts = [(xx, ye, zb), (xx, ym, zt), (xx, ym, zt - thick), (xx, ye, zb - thick)]
            b.face(pts if flip == (ye == ya) else list(reversed(pts)), shade(col, 0.72))
    if ridge:
        b.box((xa - 0.02, ym - 0.10, zt - 0.03), (xb + 0.02, ym + 0.10, zt + 0.11),
              light, top=shade(col, 1.16))
    if gable is not None:
        # the triangle of wall under each slope; without it you see into the house
        for xx, flip in ((x0, True), (x1, False)):
            tri = [(xx, y0, zb - thick - 0.02), (xx, y1, zb - thick - 0.02),
                   (xx, (y0 + y1) * 0.5, zt - thick * 0.6)]
            b.face(tri if flip else list(reversed(tri)), gable)
        # and a thin slab joining them so the gable has thickness
        b.box((x0, y0, zb - thick - 0.02), (x1, y1, zb - thick + 0.03), gable,
              top=shade(gable, 0.9))
    return b


def hip_roof(b, x0, x1, y0, y1, zb, zt, col=P["thatch"], over=0.30, bands=3):
    """Four-sided pyramid-ish roof for the stilt hut."""
    xa, xb, ya, yb = x0 - over, x1 + over, y0 - over, y1 + over
    cx, cy = (xa + xb) * 0.5, (ya + yb) * 0.5
    rx, ry = (xb - xa) * 0.5, (yb - ya) * 0.5
    for k in range(bands):
        t0, t1 = k / bands, (k + 1) / bands
        c = shade(col, 1.04 if k % 2 == 0 else 0.86)
        for i, (sx, sy) in enumerate(((0, -1), (1, 0), (0, 1), (-1, 0))):
            cc = shade(c, (1.10, 0.94, 0.84, 0.94)[i])

            def corner(t, a, bq):
                return (cx + a * rx * (1 - t) * 0.999, cy + bq * ry * (1 - t) * 0.999,
                        zb + (zt - zb) * t)
            if sy:
                p0 = corner(t0, -1, sy)
                p1 = corner(t0, 1, sy)
                p2 = corner(t1, 1, sy)
                p3 = corner(t1, -1, sy)
            else:
                p0 = corner(t0, sx, 1)
                p1 = corner(t0, sx, -1)
                p2 = corner(t1, sx, -1)
                p3 = corner(t1, sx, 1)
            quad = [p0, p1, p2, p3]
            n = (sx, sy)
            if (n == (0, -1)) or (n == (-1, 0)):
                quad = list(reversed(quad))
            b.face(quad, cc)
    return b


def window(b, cx, cz, w=0.46, h=0.62, face=-1, y=0.0, depth=0.09,
           frame=P["wallShade"], pane=P["glass"], sill=True, shutters=None):
    """Framed window on a wall facing -Y (face=-1) or +Y (face=1).

    The frame is a shallow box standing proud of the wall and the dark pane sits
    just in FRONT of its outer face -- put the pane inside the frame box and the
    glass disappears, which is exactly what the first pass did."""
    s = face
    out = y + s * depth                      # outer face of the frame
    pane_y = out + s * 0.004                 # a hair proud of it
    b.push_trs(loc=(cx, 0, cz))
    lo = (-w / 2 - 0.08, min(y, out), -h / 2 - 0.08)
    hi = (w / 2 + 0.08, max(y, out), h / 2 + 0.08)
    b.box(lo, hi, frame, top=frame, bottom=frame)
    pts = [(-w / 2, pane_y, -h / 2), (w / 2, pane_y, -h / 2),
           (w / 2, pane_y, h / 2), (-w / 2, pane_y, h / 2)]
    b.face(pts if s < 0 else list(reversed(pts)), pane)
    # glazing bars, standing proud of the pane
    bar = pane_y + s * 0.004
    b.box((-w / 2, min(bar, bar), -0.022), (w / 2, max(bar, bar), 0.022), frame)
    b.box((-0.022, min(bar, bar), -h / 2), (0.022, max(bar, bar), h / 2), frame)
    if sill:
        b.box((-w / 2 - 0.15, min(y, out + s * 0.09), -h / 2 - 0.17),
              (w / 2 + 0.15, max(y, out + s * 0.09), -h / 2 - 0.08), P["stoneLight"])
    if shutters:
        for sx in (-1, 1):
            b.box((sx * (w / 2 + 0.08), min(out, out + s * 0.05),
                   -h / 2 - 0.06),
                  (sx * (w / 2 + 0.08 + w * 0.52), max(out, out + s * 0.05),
                   h / 2 + 0.06), shutters, top=shade(shutters, 0.8))
    b.pop()


def door(b, cx, w=0.72, h=1.55, face=-1, y=0.0, col=P["wood"], step=True):
    s = face
    b.push_trs(loc=(cx, 0, 0))
    b.box((-w / 2 - 0.08, y - 0.06 * -s if s < 0 else y - 0.02, 0),
          (w / 2 + 0.08, y + 0.02 if s < 0 else y + 0.08, h + 0.09),
          P["wallShade"], top=P["wallShade"])
    yy = y - 0.08 if s < 0 else y + 0.08
    pts = [(-w / 2, yy, 0), (w / 2, yy, 0), (w / 2, yy, h), (-w / 2, yy, h)]
    b.face(pts if s < 0 else list(reversed(pts)), col)
    b.box((-w / 2, yy - 0.015 * s, h * 0.55), (w / 2, yy - 0.015 * s, h * 0.60), shade(col, 0.76))
    if step:
        b.box((-w / 2 - 0.22, min(yy, y) - 0.30, 0), (w / 2 + 0.22, max(yy, y), 0.11), P["stoneLight"])
    b.pop()


def chimney(b, x, y, ztop, h=0.95, r=0.19, col=P["wallShade"]):
    b.box((x - r, y - r, ztop - 0.4), (x + r, y + r, ztop + h), col, top=shade(col, 0.9))
    b.box((x - r - 0.07, y - r - 0.07, ztop + h), (x + r + 0.07, y + r + 0.07, ztop + h + 0.14),
          P["roofDark"], top=P["dark"])


def plinth(b, x0, x1, y0, y1, h=0.22, col=P["stoneLight"]):
    b.box((x0 - 0.07, y0 - 0.07, 0), (x1 + 0.07, y1 + 0.07, h), col, top=shade(col, 1.06))


def walls(b, x0, x1, y0, y1, z0, z1, col=P["wall"]):
    b.box((x0, y0, z0), (x1, y1, z1), col, top=shade(col, 0.95))


# ------------------------------------------------------------- buildings
def house_a():
    """One-storey fisherman's house: the harbour town's basic unit."""
    b = Build()
    x0, x1, y0, y1 = -2.1, 2.1, -1.6, 1.6
    wall_h = 2.55
    plinth(b, x0, x1, y0, y1, 0.24)
    walls(b, x0, x1, y0, y1, 0.20, wall_h)
    roof(b, x0, x1, y0, y1, wall_h - 0.06, wall_h + 1.30, over=0.30, bands=4)
    door(b, -0.95, face=-1, y=y0)
    window(b, 0.75, 1.55, face=-1, y=y0, shutters=P["roofDark"])
    window(b, 1.70, 1.55, face=-1, y=y0, shutters=P["roofDark"])
    window(b, -0.3, 1.55, face=1, y=y1)
    window(b, 1.3, 1.55, face=1, y=y1)
    chimney(b, 1.45, 0.0, wall_h + 1.05, h=0.7)
    return b, "house_white_a"


def house_b():
    """L-plan house with a lower annex — breaks up a row of identical boxes."""
    b = Build()
    x0, x1, y0, y1 = -1.75, 1.75, -1.5, 1.5
    wall_h = 2.95
    plinth(b, x0, x1, y0, y1, 0.26)
    walls(b, x0, x1, y0, y1, 0.22, wall_h)
    roof(b, x0, x1, y0, y1, wall_h - 0.06, wall_h + 1.42, over=0.30, bands=4)

    ax0, ax1, ay0, ay1 = 1.62, 4.05, -1.52, 1.45
    ah = 2.05
    plinth(b, ax0, ax1, ay0, ay1, 0.20)
    walls(b, ax0, ax1, ay0, ay1, 0.16, ah, col=P["wallWarm"])
    roof(b, ax0, ax1, ay0, ay1, ah - 0.05, ah + 0.86, over=0.26, bands=3,
         gable=P["wallWarm"])

    door(b, -0.55, face=-1, y=y0, h=1.6)
    window(b, 0.85, 1.75, face=-1, y=y0, shutters=P["roofDark"])
    window(b, -1.15, 1.75, face=-1, y=y0, shutters=P["roofDark"])
    window(b, 0.0, 1.9, face=1, y=y1)
    window(b, 2.35, 1.15, w=0.44, h=0.56, face=-1, y=ay0, shutters=P["roofDark"])
    door(b, 3.35, w=0.66, h=1.45, face=-1, y=ay0)
    chimney(b, -1.25, 0.1, wall_h + 1.10, h=0.85)
    # outside stone stair up to a first-floor door on the annex, which is what
    # gives this one its own silhouette instead of a second generic box
    sx0, sx1 = ax1 - 0.1, ax1 + 1.05
    for k in range(6):
        t = k / 6.0
        b.box((sx0 + (sx1 - sx0) * t, ay1 - 0.95, 0),
              (sx0 + (sx1 - sx0) * (t + 1 / 6.0) + 0.02, ay1 - 0.15, 0.30 + 1.62 * t),
              P["stoneLight"], top=shade(P["stone"], 1.08))
    b.box((ax1 - 0.06, ay1 - 1.0, 1.72), (ax1 + 0.02, ay1 - 0.1, 2.46),
          P["wood"], top=P["woodDark"])
    return b, "house_white_b"


def house_c():
    """Two-storey town house with a balcony, for the dense part of the harbour."""
    b = Build()
    x0, x1, y0, y1 = -1.6, 1.6, -1.45, 1.45
    h1, h2 = 2.45, 4.75
    plinth(b, x0, x1, y0, y1, 0.28, col=P["stone"])
    walls(b, x0, x1, y0, y1, 0.24, h2, col=P["wall"])
    # a string course marking the floor line
    b.box((x0 - 0.08, y0 - 0.08, h1), (x1 + 0.08, y1 + 0.08, h1 + 0.12), P["wallShade"])
    roof(b, x0, x1, y0, y1, h2 - 0.06, h2 + 1.25, over=0.30, bands=4)

    door(b, -0.7, face=-1, y=y0, h=1.7)
    window(b, 0.75, 1.55, face=-1, y=y0, shutters=P["roofDark"])
    window(b, -0.75, 3.55, face=-1, y=y0, shutters=P["roofDark"])
    window(b, 0.75, 3.55, face=-1, y=y0, shutters=P["roofDark"])
    window(b, 0.0, 1.6, face=1, y=y1)
    window(b, 0.0, 3.55, face=1, y=y1)
    window(b, 0.0, 3.4, face=-1, y=x1, w=0.4, h=0.5, sill=False)

    # balcony on the front, first floor
    by = y0 - 0.55
    b.box((-1.25, by, 2.78), (1.25, y0 + 0.02, 2.92), P["woodLight"], top=P["woodPale"])
    for sx in (-1.22, 1.22):
        b.strut((sx, by + 0.03, 2.92), (sx, y0, 2.92), 0.05, P["woodPale"], n=4)
    b.strut((-1.25, by + 0.03, 3.52), (1.25, by + 0.03, 3.52), 0.05, P["woodPale"], n=4)
    for i in range(7):
        xx = -1.18 + i * 0.393
        b.strut((xx, by + 0.03, 2.92), (xx, by + 0.03, 3.52), 0.035, P["woodPale"], n=4)
    for sx in (-1.15, 1.15):
        b.strut((sx, by + 0.06, 2.80), (sx, y0 + 0.02, 2.20), 0.05, P["woodLight"], n=4)
    chimney(b, -1.15, 0.2, h2 + 1.00, h=0.9)
    return b, "house_white_c"


def lighthouse():
    """Slim white tower with red bands, gallery and lantern — the harbour marker."""
    b = Build()
    n = 10
    # rock footing
    b.frustum(-0.10, 0.55, 1.95, 1.58, 7, P["stone"], cap_top=None, phase=0.3)
    b.frustum(0.55, 0.85, 1.58, 1.44, 7, P["stoneDark"], phase=0.3)

    top = 8.2
    segs = [(0.85, 2.60, 1.34, 1.18, P["wall"]),
            (2.60, 3.45, 1.18, 1.10, P["roof"]),
            (3.45, 5.60, 1.10, 0.96, P["wall"]),
            (5.60, 6.40, 0.96, 0.90, P["roof"]),
            (6.40, top, 0.90, 0.82, P["wall"])]
    for (z0, z1, r0, r1, c) in segs:
        b.frustum(z0, z1, r0, r1, n, c)

    # gallery: a ring deck on corbels with a railing
    gz = top
    b.frustum(gz, gz + 0.14, 1.30, 1.30, n, P["stoneDark"], cap_top=P["stone"])
    for i in range(n):
        a = i * TAU / n + TAU / (2 * n)
        b.strut((math.cos(a) * 0.82, math.sin(a) * 0.82, gz - 0.42),
                (math.cos(a) * 1.22, math.sin(a) * 1.22, gz), 0.075, P["stoneDark"], n=4)
    for i in range(n):
        a = i * TAU / n
        b.strut((math.cos(a) * 1.18, math.sin(a) * 1.18, gz + 0.14),
                (math.cos(a) * 1.18, math.sin(a) * 1.18, gz + 0.70), 0.05, P["iron"], n=4)
    b.frustum(gz + 0.62, gz + 0.72, 1.21, 1.21, n, P["iron"])

    # lantern room
    lz = gz + 0.14
    b.frustum(lz, lz + 0.18, 0.86, 0.86, 8, P["iron"], cap_top=None, phase=0.39)
    b.frustum(lz + 0.18, lz + 1.42, 0.80, 0.80, 8, P["glassLit"], phase=0.39)
    for i in range(8):
        a = i * TAU / 8 + 0.39
        b.strut((math.cos(a) * 0.80, math.sin(a) * 0.80, lz + 0.18),
                (math.cos(a) * 0.80, math.sin(a) * 0.80, lz + 1.42), 0.055, P["iron"], n=4)
    b.frustum(lz + 1.42, lz + 1.58, 0.94, 0.90, 8, P["iron"], phase=0.39)
    b.frustum(lz + 1.58, lz + 2.45, 0.90, 0.02, 8, P["roof"], phase=0.39)
    b.strut((0, 0, lz + 2.40), (0, 0, lz + 2.85), 0.045, P["iron"], n=4)

    door(b, 0.0, w=0.68, h=1.5, face=-1, y=-1.30, col=P["wood"])
    for (zz, aa) in ((2.0, 0.0), (4.3, 0.0), (6.9, 0.0)):
        rr = 1.26 - (zz - 0.85) * 0.055
        b.push_trs(loc=(0, 0, 0), rot=(0, 0, aa))
        window(b, 0.0, zz, w=0.34, h=0.52, face=-1, y=-rr, sill=False, frame=P["stoneLight"])
        b.pop()
    return b, "lighthouse"


def watchtower():
    """Square stone watchtower with crenellations, like the ones on the headlands.
    Weathered on purpose: even courses, uneven merlons and one broken off."""
    b = Build()
    top = 6.4
    # rocky footing, not a clean plinth
    for (ox, oy, rr, hh, nn) in ((-1.5, -1.2, 1.15, 0.52, 6), (1.6, -0.9, 0.95, 0.44, 5),
                                 (0.9, 1.7, 1.05, 0.40, 6), (-1.7, 1.4, 0.85, 0.34, 5)):
        b.push_trs(loc=(ox, oy, -0.1), rot=(0, 0, ox + oy))
        b.frustum(0, hh, rr, rr * 0.72, nn, P["stoneDark"], cap_top=P["stone"])
        b.pop()
    b.box((-2.00, -2.00, 0), (2.00, 2.00, 0.50), P["stoneDark"], top=P["stone"])

    # body in visible courses, battered, with a slight jitter per course
    steps = 9
    rings = []
    for i in range(steps + 1):
        t = i / steps
        jit = 0.022 * math.sin(i * 2.4) 
        sz = 1.66 - 0.21 * t + jit
        z = 0.42 + (top - 0.42) * t
        rings.append([(-sz, -sz, z), (sz, -sz, z), (sz, sz, z), (-sz, sz, z)])
    b.loft(rings, P["stone"], close=True,
           shade_fn=lambda k, i, c: shade(shade(c, (1.12, 0.88, 0.80, 0.99)[i]),
                                          1.0 if k % 2 == 0 else 0.925))
    s = 1.45
    # corbelled parapet
    b.box((-s - 0.28, -s - 0.28, top), (s + 0.28, s + 0.28, top + 0.28), P["stoneLight"])
    b.box((-s - 0.22, -s - 0.22, top + 0.28), (s + 0.22, s + 0.22, top + 0.38),
          P["stoneDark"], top=P["stoneDark"])
    # crenellations: alternating merlons of uneven height, one knocked out
    m = s + 0.26
    step = (2 * m) / 7.0
    missing = {("S", 4), ("E", 2)}
    for side, build in (("S", lambda a0, a1, d: ((a0, -m), (a1, -m + 0.36))),
                        ("N", lambda a0, a1, d: ((a0, m - 0.36), (a1, m))),
                        ("W", lambda a0, a1, d: ((-m, a0), (-m + 0.36, a1))),
                        ("E", lambda a0, a1, d: ((m - 0.36, a0), (m, a1)))):
        for i in range(7):
            if i % 2:
                continue
            a0 = -m + i * step
            a1 = a0 + step
            lo, hi = build(a0, a1, 0)
            hgt = 0.74 + 0.05 * math.sin(i * 1.9 + len(side))
            if (side, i) in missing:
                hgt = 0.24          # knocked off in some old siege
            b.box((lo[0], lo[1], top + 0.38), (hi[0], hi[1], top + 0.38 + hgt),
                  P["stoneLight"], top=shade(P["stone"], 0.92))

    # arrow slits
    for z in (2.2, 4.1):
        for rot in (0, math.pi, math.pi / 2):
            b.push_trs(rot=(0, 0, rot))
            yy = -(1.66 - 0.21 * ((z - 0.42) / (top - 0.42))) - 0.03
            b.box((-0.13, yy, z), (0.13, yy + 0.10, z + 0.78), P["dark"])
            b.box((-0.23, yy - 0.03, z - 0.10), (0.23, yy + 0.02, z + 0.88),
                  P["stoneLight"])
            b.box((-0.11, yy - 0.04, z), (0.11, yy + 0.02, z + 0.74), P["dark"])
            b.pop()
    door(b, 0.0, w=0.80, h=1.72, face=-1, y=-1.64, col=P["woodDark"])
    # arch over the door
    b.box((-0.55, -1.72, 1.72), (0.55, -1.58, 1.94), P["stoneLight"])
    # weathered wooden hoarding on one side
    b.push_trs(loc=(0, 1.50, 4.45))
    b.box((-0.95, 0, 0), (0.95, 0.56, 1.15), P["woodLight"], top=P["woodDark"])
    b.box((-0.95, 0.52, -0.16), (0.95, 0.62, 0.02), P["woodDark"])
    b.pop()
    return b, "watchtower"


def stilt_hut():
    """Palm-thatched hut on piles over the shallows, with a deck and a ladder."""
    b = Build()
    deck_z = 1.55
    dx, dy = 2.35, 2.05
    posts = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            posts.append((sx * (dx - 0.26), sy * (dy - 0.26)))
    posts += [(0, -(dy - 0.26)), (0, dy - 0.26)]
    for (px, py) in posts:
        b.push_trs(loc=(px, py, 0), rot=(0, 0, 0.2 * px))
        b.frustum(-0.75, deck_z, 0.15, 0.125, 6, P["woodDark"], cap_top=P["wood"])
        b.pop()
    # cross bracing
    for sy in (-1, 1):
        b.strut((-(dx - 0.26), sy * (dy - 0.26), 0.55), (0, sy * (dy - 0.26), 0.95),
                0.055, P["woodDark"], n=4)
        b.strut((dx - 0.26, sy * (dy - 0.26), 0.55), (0, sy * (dy - 0.26), 0.95),
                0.055, P["woodDark"], n=4)

    # deck planks
    nb = 9
    for i in range(nb):
        yy0 = -dy + (2 * dy) * i / nb
        yy1 = -dy + (2 * dy) * (i + 1) / nb - 0.025
        b.box((-dx, yy0, deck_z), (dx, yy1, deck_z + 0.11),
              shade(P["woodLight"], 1.0 if i % 2 == 0 else 0.90),
              top=shade(P["woodPale"], 1.0 if i % 2 == 0 else 0.92))

    # hut: open-sided front, planked walls
    hz = deck_z + 0.11
    hx, hy = 1.55, 1.35
    wall_h = 1.85
    for (lo, hi) in ((((-hx, hy - 0.12)), (hx, hy)),
                     ((-hx, -hy), (-hx + 0.12, hy)),
                     ((hx - 0.12, -hy), (hx, hy))):
        b.box((lo[0], lo[1], hz), (hi[0], hi[1], hz + wall_h), P["woodLight"],
              top=P["wood"])
    # front: two posts and a low rail, so the inside shows
    for sx in (-1, 1):
        b.push_trs(loc=(sx * (hx - 0.08), -hy + 0.06, 0))
        b.frustum(hz, hz + wall_h, 0.11, 0.10, 5, P["woodLight"], cap_top=P["wood"])
        b.pop()
    b.box((-hx, -hy, hz), (hx, -hy + 0.1, hz + 0.75), P["wood"], top=P["woodPale"])
    # dark interior backdrop so the opening does not show the sky through
    b.face([(-hx + 0.12, hy - 0.13, hz), (hx - 0.12, hy - 0.13, hz),
            (hx - 0.12, hy - 0.13, hz + wall_h), (-hx + 0.12, hy - 0.13, hz + wall_h)],
           shade(P["dark"], 1.4))
    b.box((-hx - 0.06, -hy - 0.06, hz + wall_h), (hx + 0.06, hy + 0.06, hz + wall_h + 0.12),
          P["wood"], top=P["woodDark"])
    hip_roof(b, -hx, hx, -hy, hy, hz + wall_h + 0.10, hz + wall_h + 1.35,
             col=P["thatch"], over=0.42, bands=3)
    b.box((-0.1, -0.1, hz + wall_h + 1.30), (0.1, 0.1, hz + wall_h + 1.52),
          P["thatchDark"], top=P["thatchDark"])

    # ladder down to the water
    lx = dx + 0.1
    b.strut((lx, -0.4, deck_z + 0.1), (lx + 0.55, -0.4, -0.9), 0.055, P["woodLight"], n=4)
    b.strut((lx, 0.4, deck_z + 0.1), (lx + 0.55, 0.4, -0.9), 0.055, P["woodLight"], n=4)
    for i in range(4):
        t = (i + 0.5) / 4
        b.box((lx + 0.55 * t - 0.05, -0.4, deck_z + 0.1 - (deck_z + 1.0) * t - 0.04),
              (lx + 0.55 * t + 0.05, 0.4, deck_z + 0.1 - (deck_z + 1.0) * t + 0.04),
              P["woodPale"])
    # a net hung on the rail
    b.push_trs(loc=(-hx - 0.6, -dy + 0.2, deck_z + 0.11))
    b.frustum(0, 0.46, 0.22, 0.22, 7, P["rope"], cap_top=shade(P["rope"], 0.85))
    b.pop()
    return b, "stilt_hut"


def main():
    for fn in (house_a, house_b, house_c, lighthouse, watchtower, stilt_hut):
        pl.clear()
        b, name = fn()
        pl.emit(b, name)


main()
