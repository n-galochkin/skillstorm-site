"""Pier modules, mooring posts and stone ruins.

Pier convention: the WALKING SURFACE is at z = 0 and the piles hang below into the
water, so segments can be laid at a constant deck height. Modules tile on a 2 m
grid: each occupies y in [-1, 1] and runs along Y (which is the site's Z).
Everything else keeps the usual base-at-zero pivot.
"""
import math
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import propslib as pl
from propslib import Build, P, shade

TAU = math.pi * 2
TILE = 2.0
HALF_W = 1.05
PILE_BOTTOM = -2.30


def planks(b, x0, x1, y0, y1, z=0.0, thick=0.11, n=7, along_x=True):
    """Deck boards with alternating tone and a hairline gap between them."""
    for i in range(n):
        t0, t1 = i / n, (i + 1) / n
        c = shade(P["woodLight"], 1.0 if i % 2 == 0 else 0.90)
        ct = shade(P["woodPale"], 1.0 if i % 2 == 0 else 0.91)
        if along_x:
            a = y0 + (y1 - y0) * t0
            bq = y0 + (y1 - y0) * t1 - 0.025
            b.box((x0, a, z - thick), (x1, bq, z), c, top=ct)
        else:
            a = x0 + (x1 - x0) * t0
            bq = x0 + (x1 - x0) * t1 - 0.025
            b.box((a, y0, z - thick), (bq, y1, z), c, top=ct)


def stringers(b, x0, x1, y0, y1, z=-0.11):
    for xx in (x0 + 0.16, x1 - 0.16):
        b.box((xx - 0.07, y0, z - 0.16), (xx + 0.07, y1, z), P["wood"])


def pile(b, x, y, top=-0.14, bottom=PILE_BOTTOM, r=0.14, tilt=0.0):
    b.push_trs(loc=(x, y, 0), rot=(tilt, 0, 0))
    b.frustum(bottom, top, r * 1.08, r, 6, P["woodDark"], cap_top=P["wood"])
    # a wet, darker band at the waterline
    b.frustum(-0.95, -0.45, r * 1.06, r * 1.04, 6, shade(P["woodDark"], 0.72))
    b.pop()


def pier_straight():
    b = Build()
    planks(b, -HALF_W, HALF_W, -TILE / 2, TILE / 2, n=7, along_x=True)
    stringers(b, -HALF_W, HALF_W, -TILE / 2, TILE / 2)
    for sx in (-1, 1):
        pile(b, sx * (HALF_W - 0.20), -TILE / 2 + 0.28)
        pile(b, sx * (HALF_W - 0.20), TILE / 2 - 0.28)
    # cross brace below deck
    for sy in (-1, 1):
        b.strut((-(HALF_W - 0.20), sy * (TILE / 2 - 0.28), -1.15),
                (HALF_W - 0.20, sy * (TILE / 2 - 0.28), -1.15), 0.055, P["woodDark"], n=4)
    return b, "pier_straight"


def pier_end():
    """Closing segment: a bumper beam, a short ladder and two bollards."""
    b = Build()
    planks(b, -HALF_W, HALF_W, -TILE / 2, TILE / 2, n=7, along_x=True)
    stringers(b, -HALF_W, HALF_W, -TILE / 2, TILE / 2)
    for sx in (-1, 1):
        pile(b, sx * (HALF_W - 0.20), -TILE / 2 + 0.28)
        pile(b, sx * (HALF_W - 0.20), TILE / 2 - 0.26)
    # end bumper
    b.box((-HALF_W, -TILE / 2 - 0.10, -0.30), (HALF_W, -TILE / 2 + 0.02, 0.06),
          P["wood"], top=P["woodPale"])
    for sx in (-1, 1):
        b.push_trs(loc=(sx * (HALF_W - 0.30), -TILE / 2 + 0.34, 0))
        b.frustum(0, 0.46, 0.115, 0.105, 7, P["woodLight"], cap_top=P["woodPale"])
        b.frustum(0.46, 0.56, 0.155, 0.13, 7, P["woodPale"], cap_top=P["woodPale"])
        b.pop()
    # ladder into the water
    for sx in (-0.26, 0.26):
        b.strut((sx, -TILE / 2 - 0.12, 0.10), (sx, -TILE / 2 - 0.34, -1.75),
                0.055, P["woodLight"], n=4)
    for i in range(4):
        t = (i + 0.4) / 4.4
        b.box((-0.26, -TILE / 2 - 0.12 - 0.22 * t - 0.04, 0.10 - 1.85 * t - 0.04),
              (0.26, -TILE / 2 - 0.12 - 0.22 * t + 0.04, 0.10 - 1.85 * t + 0.04),
              P["woodPale"])
    return b, "pier_end"


def pier_corner():
    """L junction: deck continues to +Y and to +X."""
    b = Build()
    planks(b, -HALF_W, HALF_W, -HALF_W, TILE / 2, n=6, along_x=True)
    planks(b, HALF_W, TILE / 2 + 0.95, -HALF_W, HALF_W, n=5, along_x=False)
    stringers(b, -HALF_W, HALF_W, -HALF_W, TILE / 2)
    b.box((-HALF_W + 0.09, -HALF_W + 0.09, -0.27), (TILE / 2 + 0.86, -HALF_W + 0.23, -0.11), P["wood"])
    pile(b, -(HALF_W - 0.20), TILE / 2 - 0.28)
    pile(b, HALF_W - 0.20, TILE / 2 - 0.28)
    pile(b, -(HALF_W - 0.20), -(HALF_W - 0.22))
    pile(b, TILE / 2 + 0.72, -(HALF_W - 0.22))
    pile(b, TILE / 2 + 0.72, HALF_W - 0.24)
    return b, "pier_corner"


def mooring_post():
    """A bollard that stands on the deck: base at z = 0 like every other prop."""
    b = Build()
    b.frustum(0, 1.02, 0.155, 0.135, 8, P["woodDark"], cap_top=P["wood"])
    b.frustum(1.02, 1.16, 0.215, 0.185, 8, P["woodLight"], cap_top=P["woodPale"])
    # coiled rope round the shaft
    for k in range(3):
        z = 0.42 + k * 0.105
        b.frustum(z, z + 0.08, 0.195, 0.195, 8, shade(P["rope"], 1.0 - 0.05 * k))
    b.frustum(0, 0.10, 0.26, 0.21, 8, P["stoneDark"], cap_top=P["stone"])
    return b, "mooring_post"


def mooring_post_stone():
    b = Build()
    b.frustum(0, 0.16, 0.34, 0.30, 8, P["stoneDark"], cap_top=P["stone"])
    b.frustum(0.16, 0.92, 0.26, 0.22, 8, P["stone"])
    b.frustum(0.92, 1.08, 0.31, 0.26, 8, P["stoneLight"], cap_top=P["stoneLight"])
    for k in range(2):
        z = 0.50 + k * 0.12
        b.frustum(z, z + 0.09, 0.30, 0.30, 8, shade(P["rope"], 1.0 - 0.06 * k))
    return b, "mooring_post_stone"


# ----------------------------------------------------------------- ruins
def block_column(b, x, y, z0, z1, r0, r1, n=8, col=P["stone"], courses=4, jitter=0.03):
    """A column built from visible drums, each one slightly off from the last."""
    for k in range(courses):
        t0, t1 = k / courses, (k + 1) / courses
        zz0 = z0 + (z1 - z0) * t0
        zz1 = z0 + (z1 - z0) * t1
        rr0 = r0 + (r1 - r0) * t0
        rr1 = r0 + (r1 - r0) * t1
        ph = jitter * 3.0 * math.sin(k * 2.1)
        b.push_trs(loc=(x + jitter * math.sin(k * 1.7), y + jitter * math.cos(k * 2.3), 0))
        b.frustum(zz0, zz1, rr0, rr1, n, shade(col, 1.0 if k % 2 == 0 else 0.93),
                  cap_top=shade(col, 1.08) if k == courses - 1 else None, phase=ph)
        b.pop()


def arch_ring(b, span, pier_half, thick, spring_z, col=P["stoneLight"], nseg=8,
              start=0.0, end=1.0):
    """Semicircular arch of voussoirs. Inner and outer radii are taken from the
    piers so the arch continues them instead of floating above the opening."""
    ri = span - pier_half
    ro = span + pier_half
    for k in range(nseg):
        t0, t1 = start + (end - start) * k / nseg, start + (end - start) * (k + 1) / nseg
        a0, a1 = math.pi * t0, math.pi * t1
        p = [(-math.cos(a) * r, 0.0, spring_z + math.sin(a) * r)
             for (a, r) in ((a0, ri), (a1, ri), (a1, ro), (a0, ro))]
        front = [(x, -thick, z) for (x, _, z) in p]
        back = [(x, thick, z) for (x, _, z) in p]
        c = shade(col, 1.0 if k % 2 == 0 else 0.90)
        b.face(front, c)
        b.face(list(reversed(back)), shade(c, 0.80))
        b.face([front[3], front[2], back[2], back[3]], shade(c, 1.06))   # extrados
        b.face([front[1], front[0], back[0], back[1]], shade(c, 0.74))   # intrados
        if k == 0:
            b.face([front[0], front[3], back[3], back[0]], shade(c, 0.86))
        if k == nseg - 1:
            b.face([front[2], front[1], back[1], back[2]], shade(c, 0.86))
    return ri, ro


def arch_pier(b, x, pier_half, thick, height, col=P["stone"]):
    b.push_trs(loc=(x, 0, 0))
    b.box((-pier_half - 0.14, -thick - 0.12, 0), (pier_half + 0.14, thick + 0.12, 0.26),
          P["stoneDark"], top=P["stone"])
    courses = 5
    for k in range(courses):
        z0 = 0.22 + (height - 0.22) * k / courses
        z1 = 0.22 + (height - 0.22) * (k + 1) / courses
        inset = 0.012 * math.sin(k * 2.2)
        b.box((-pier_half + inset, -thick + inset, z0), (pier_half - inset, thick - inset, z1),
              shade(col, 1.0 if k % 2 == 0 else 0.92),
              top=shade(col, 1.06) if k == courses - 1 else None,
              skip=() if k == courses - 1 else ("top", "bottom"))
    b.pop()


def rubble(b, spots):
    for (rx, ry, rr, nn) in spots:
        b.push_trs(loc=(rx, ry, 0), rot=(0, 0, rx * 2.3))
        b.frustum(-0.05, rr * 0.95, rr, rr * 0.55, nn, P["stone"], cap_top=P["stoneLight"])
        b.pop()


def ruin_arch():
    """Standing stone arch — the motif from the island sheet."""
    b = Build()
    span, pier_half, thick, height = 1.70, 0.42, 0.46, 2.55
    for sx in (-1, 1):
        arch_pier(b, sx * span, pier_half, thick, height)
    arch_ring(b, span, pier_half, thick * 0.97, height, nseg=9)
    # keystone, sunk into the ring so it is part of it
    b.box((-0.27, -thick, height + span + pier_half - 0.34),
          (0.27, thick, height + span + pier_half + 0.20),
          P["stoneLight"], top=P["stone"])
    rubble(b, ((-2.75, 0.5, 0.33, 5), (2.55, -0.55, 0.28, 6),
               (-1.5, -1.05, 0.22, 5), (1.7, 0.95, 0.26, 5)))
    return b, "ruin_arch"


def ruin_arch_broken():
    """Half an arch: one pier standing with the springing still on it, the other
    snapped off low, its drum lying in the grass."""
    b = Build()
    span, pier_half, thick, height = 1.70, 0.42, 0.46, 2.55
    arch_pier(b, -span, pier_half, thick, height)
    arch_ring(b, span, pier_half, thick * 0.97, height, nseg=9, start=0.0, end=0.42)
    # the broken end of the ring, cut on a slant
    a = math.pi * 0.42
    ri, ro = span - pier_half, span + pier_half
    pts = [(-math.cos(a) * r, 0, height + math.sin(a) * r) for r in (ri, ro)]
    b.box((pts[0][0] - 0.24, -thick, pts[0][2] - 0.10),
          (pts[1][0] + 0.10, thick, pts[1][2] + 0.26), P["stoneLight"], top=P["stone"])
    # the fallen pier: a low stump
    b.push_trs(loc=(span, 0, 0))
    b.box((-pier_half - 0.14, -thick - 0.12, 0), (pier_half + 0.14, thick + 0.12, 0.26),
          P["stoneDark"], top=P["stone"])
    b.box((-pier_half, -thick, 0.22), (pier_half, thick, 0.95), P["stone"], top=P["stoneLight"])
    b.box((-pier_half + 0.03, -thick + 0.03, 0.95), (pier_half - 0.03, thick - 0.03, 1.34),
          shade(P["stone"], 0.93), top=P["stoneLight"])
    b.pop()
    b.push_trs(loc=(span + 1.05, -0.80, 0.34), rot=(0, math.pi / 2, 0.5))
    b.frustum(-0.58, 0.58, 0.38, 0.35, 7, P["stone"], cap_top=P["stoneLight"],
              cap_bot=P["stoneDark"])
    b.pop()
    rubble(b, ((-2.6, 0.65, 0.30, 5), (1.1, 0.95, 0.26, 6), (3.2, 0.45, 0.22, 5)))
    return b, "ruin_arch_broken"


def ruin_column():
    b = Build()
    b.frustum(0, 0.20, 0.62, 0.56, 8, P["stoneDark"], cap_top=P["stone"])
    b.frustum(0.20, 0.42, 0.52, 0.47, 8, P["stoneLight"], cap_top=P["stone"])
    block_column(b, 0, 0, 0.40, 3.55, 0.42, 0.355, n=8, courses=5, jitter=0.025)
    b.frustum(3.55, 3.74, 0.44, 0.50, 8, P["stoneLight"])
    b.box((-0.58, -0.58, 3.74), (0.58, 0.58, 3.98), P["stoneLight"], top=P["stone"])
    return b, "ruin_column"


def ruin_column_broken():
    b = Build()
    b.frustum(0, 0.20, 0.62, 0.56, 8, P["stoneDark"], cap_top=P["stone"])
    b.frustum(0.20, 0.42, 0.52, 0.47, 8, P["stoneLight"], cap_top=P["stone"])
    block_column(b, 0, 0, 0.40, 1.62, 0.42, 0.39, n=8, courses=2, jitter=0.03)
    # jagged break
    ring = [(math.cos(i * TAU / 8) * 0.39, math.sin(i * TAU / 8) * 0.39,
             1.62 + 0.16 * math.sin(i * 1.9)) for i in range(8)]
    b.face(ring, P["stoneLight"])
    for i in range(8):
        j = (i + 1) % 8
        b.face([(ring[i][0], ring[i][1], 1.60), (ring[j][0], ring[j][1], 1.60),
                ring[j], ring[i]], shade(P["stone"], 1.04))
    # the fallen upper half lying beside it
    b.push_trs(loc=(1.35, 0.35, 0.40), rot=(0, math.pi / 2 * 0.96, 0.7))
    b.frustum(-0.95, 0.95, 0.40, 0.36, 8, P["stone"], cap_top=P["stoneLight"],
              cap_bot=P["stoneDark"])
    b.pop()
    b.push_trs(loc=(2.45, 0.95, 0.26), rot=(0.2, 1.4, 0.3))
    b.box((-0.50, -0.50, -0.22), (0.50, 0.50, 0.22), P["stoneLight"], top=P["stone"])
    b.pop()
    for (rx, ry, rr, nn) in ((-0.95, 0.75, 0.26, 5), (0.6, -0.85, 0.22, 6)):
        b.push_trs(loc=(rx, ry, 0), rot=(0, 0, rx * 3))
        b.frustum(-0.05, rr * 0.9, rr, rr * 0.55, nn, P["stone"], cap_top=P["stoneLight"])
        b.pop()
    return b, "ruin_column_broken"


def ruin_wall():
    """A broken stretch of wall with a doorway, built as individual stone blocks.

    Courses drawn as full-width slabs give the thing ledges like a bookshelf; real
    masonry is blocks with joints, and a ruin is that minus the ones that fell."""
    b = Build()
    L, th = 4.8, 0.40
    cols, rows = 11, 6
    ch = 0.46                                  # course height
    cw = L / cols
    joint = 0.016
    base = 0.26
    # how many courses each column still has standing
    standing = [6, 6, 6, 6, 5, 5, 6, 5, 4, 3, 2]
    door = (4, 5)                              # columns the doorway opens through
    door_rows = 4                              # courses the opening is tall

    b.box((-L / 2 - 0.16, -th - 0.13, 0), (L / 2 + 0.16, th + 0.13, base),
          P["stoneDark"], top=P["stone"])
    for i in range(cols):
        x0 = -L / 2 + i * cw
        for r in range(standing[i]):
            if i in door and r < door_rows:
                continue
            z0 = base + r * ch
            # every other course is offset half a block, as masonry is bonded
            off = (cw * 0.5) if r % 2 else 0.0
            jx = 0.012 * math.sin(i * 2.3 + r * 1.7)
            jz = 0.010 * math.sin(i * 1.1 + r * 2.9)
            dd = th - 0.012 * ((i + r) % 3)
            c = shade(P["stone"], 1.0 + 0.055 * math.sin(i * 3.1 + r * 1.3))
            top_block = (r == standing[i] - 1)
            b.box((max(-L / 2, x0 + joint + off * 0 + jx), -dd, z0 + joint + jz),
                  (min(L / 2, x0 + cw - joint + jx), dd, z0 + ch - joint + jz),
                  c, top=shade(P["stoneLight"], 1.0) if top_block else shade(c, 1.04),
                  skip=("bottom",))
    # doorway: jambs, a dark reveal and a lintel
    dx0 = -L / 2 + door[0] * cw
    dx1 = -L / 2 + (door[1] + 1) * cw
    dz = base + door_rows * ch
    b.face([(dx0 + 0.02, -th, base), (dx0 + 0.02, th, base),
            (dx0 + 0.02, th, dz), (dx0 + 0.02, -th, dz)], shade(P["stoneDark"], 1.05))
    b.face([(dx1 - 0.02, -th, dz), (dx1 - 0.02, th, dz),
            (dx1 - 0.02, th, base), (dx1 - 0.02, -th, base)], shade(P["stoneDark"], 1.05))
    b.face([(dx0, -th, dz), (dx1, -th, dz), (dx1, th, dz), (dx0, th, dz)],
           shade(P["stoneDark"], 0.95))
    b.box((dx0 - 0.11, -th - 0.055, dz - 0.07), (dx1 + 0.11, th + 0.055, dz + 0.24),
          P["stoneLight"], top=P["stone"])
    rubble(b, ((3.05, 0.70, 0.32, 5), (-2.95, -0.60, 0.27, 6), (2.1, -0.90, 0.22, 5),
               (-1.15, 0.85, 0.19, 5)))
    # a couple of fallen blocks at the foot of the collapsed end
    for (bx, by, rz) in ((2.45, 0.35, 0.5), (2.9, -0.35, 1.1)):
        b.push_trs(loc=(bx, by, 0.16), rot=(0, 0, rz))
        b.box((-0.21, -0.17, -0.16), (0.21, 0.17, 0.16), P["stone"], top=P["stoneLight"])
        b.pop()
    return b, "ruin_wall"


def main():
    for fn in (pier_straight, pier_end, pier_corner, mooring_post, mooring_post_stone,
               ruin_arch, ruin_arch_broken, ruin_column, ruin_column_broken, ruin_wall):
        pl.clear()
        b, name = fn()
        pl.emit(b, name)


main()
