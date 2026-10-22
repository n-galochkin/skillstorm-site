"""Build every island .glb + heightmap + manifest. Run headless:

  blender --background --factory-startup --python build_islands.py -- [--only id,id] [--no-render]
"""
import json
import os
import sys

import numpy as np
import bpy

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import island_lib as L  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "site", "assets", "islands")
SHOTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "renders")
os.makedirs(OUT, exist_ok=True)
os.makedirs(SHOTS, exist_ok=True)

BASALT = dict(rock_a=L.PAL['basalt'], rock_b=L.PAL['basalt_dk'],
              rock_c=L.PAL['rock_dark'], rock_d=L.PAL['basalt'] * 0.88,
              grass_a=L.PAL['grass_dark'], grass_b=L.PAL['grass_dark'] * 0.8,
              grass_c=L.PAL['grass_dark'] * 1.1)


def terr(n, rise, ledge, run=0.32, **kw):
    return [dict(rise=rise, ledge=ledge, run=run, **kw) for _ in range(n)]


def wall(total, bands, run=0.10, thin=0.08, thick=0.26, **kw):
    """A sheer cliff face: `bands` thin steps, so the strata read as colour seams on
    one near-vertical wall rather than as a stack of shelves."""
    out = []
    for i in range(bands):
        out.append(dict(rise=total / bands * (0.82 + 0.36 * ((i * 7) % 5) / 4.0),
                        ledge=(thick if i % 2 else thin), run=run, **kw))
    return out


def shelf(rise, ledge, run=0.3, **kw):
    kw.setdefault('tag', 'terrace')
    return [dict(rise=rise, ledge=ledge, run=run, **kw)]


def strata(pairs, run=0.30, **kw):
    """(rise, ledge) per band: uneven bands read as rock, even ones as a wedding cake."""
    return [dict(rise=r, ledge=l, run=run, **kw) for (r, l) in pairs]


def free_circle(Z, size, tol=0.8):
    """Diameter of the largest circle of near-level ground, in metres."""
    n = Z.shape[0]
    med = float(np.median(Z[Z > Z.max() - 4.0]))
    m = np.abs(Z - med) < tol
    cell = size / (n - 1)
    best = 0
    cur = m.copy()
    for i in range(1, 80):
        nxt = (cur[1:-1, 1:-1] & cur[:-2, 1:-1] & cur[2:, 1:-1]
               & cur[1:-1, :-2] & cur[1:-1, 2:])
        pad = np.zeros_like(cur)
        pad[1:-1, 1:-1] = nxt
        cur = pad
        if not cur.any():
            break
        best = i
    return 2.0 * best * cell


SPECS = [
    # ------------------------------------------------------------- heroes
    # a low sandy island: one wide cove, a long beach, a short rock step behind it
    dict(id='landing', kind='hero', radius=26, size=76, seed=11, M=100,
         outline=dict(lobes=[(0, 0, 15), (11, -8, 11), (-11, 6, 12), (2, 13, 9)], k=2.4,
                      bays=[(7, 18, 8.0)], warp=(3.6, 0.038), warp2=(1.45, 0.175)),
         beach=dict(amount=1.0, cover=0.50, seed=11, width=4.6, rise=1.4,
                    base_w=0.7, base_rise=0.35),
         levels=wall(3.0, 3) + shelf(0.3, 1.2, wob_freq=1.4, rise_var=0.1) + wall(3.4, 3),
         tilt=(0.40, 200),
         cap=dict(roll=(0.9, 0.095), spacing=2.4, blend=0.5),
         beach_top=2.1, grass_from=3.0,
         stacks=[(-23, -15, 3.2, 4.6), (23, 11, 2.6, 3.4, 6), (15, 23, 2.2, 2.6, 6)]),

    # a broad flat table: open ground in the middle, tall banded cliffs all round
    dict(id='combat', kind='hero', radius=31, size=86, seed=23, M=104,
         outline=dict(lobes=[(0, 0, 23), (14, 10, 12), (-13, -10, 13), (4, -18, 10)], k=2.4,
                      warp=(3.0, 0.036), warp2=(1.45, 0.175)),
         beach=dict(amount=0.45, cover=0.22, seed=23, width=3.5, rise=1.0,
                    base_w=0.6, base_rise=0.35),
         levels=wall(5.2, 4) + shelf(0.35, 1.1, wob_freq=1.3, rise_var=0.1) + wall(6.4, 5),
         tilt=(0.17, 70),
         cap=dict(roll=(0.55, 0.07), spacing=2.6, blend=0.24, flat_center=(20, 6)),
         stacks=[(29, -17, 3.0, 4.2), (-27, 19, 2.6, 3.2, 6)]),

    # a ridge: a low apron, then a narrow spine with the tallest sheer walls
    dict(id='skills', kind='hero', radius=27, size=78, seed=37, M=100,
         outline=dict(lobes=[(-11, -8, 11), (0, 0, 13), (10, 7, 12), (18, 13, 8)], k=2.6,
                      warp=(3.2, 0.04), warp2=(1.45, 0.175)),
         beach=dict(amount=0.3, cover=0.16, seed=37, width=4.0, rise=0.9,
                    base_w=0.5, base_rise=0.3),
         levels=(wall(5.6, 4)
                 + shelf(0.45, 0.8, rise_var=0.1, wob_freq=1.2,
                         inset=dict(amount=3.4, harmonic=1, phase=300, power=1.8))
                 + wall(8.2, 5)),
         tilt=(0.40, 125),
         cap=dict(roll=(1.4, 0.14), spacing=2.2, blend=0.55),
         stacks=[(-24, -17, 2.8, 5.0), (19, 21, 2.3, 3.4, 6)]),

    # a volcano: terraced basalt cone with a crater
    dict(id='storm', kind='hero', radius=29, size=82, seed=51, M=116, band_h=2.2,
         outline=dict(lobes=[(0, 0, 19), (9, 10, 11), (-10, -8, 11)], k=2.6,
                      warp=(3.2, 0.04), warp2=(1.45, 0.175)),
         beach=dict(amount=0.4, cover=0.20, seed=51, width=4.0, rise=0.9,
                    base_w=0.6, base_rise=0.35),
         levels=wall(3.4, 2) + strata([(2.3, 2.3)] * 6, run=0.38),
         tilt=(0.10, 20),
         cap=dict(roll=(0.5, 0.2), spacing=1.6, blend=0.5, crater=(0, 0, 3.6, 3.8)),
         lava=(0, 0, 2.8, 16.0),
         stacks=[(27, -19, 2.8, 3.6)], **BASALT),

    # a plateau with one wide low shelf on the south-east side for a town
    dict(id='forge', kind='hero', radius=31, size=86, seed=67, M=124,
         outline=dict(lobes=[(-6, -3, 17), (9, -13, 12), (7, 13, 13), (-15, 8, 10)], k=2.4,
                      warp=(3.2, 0.038), warp2=(1.45, 0.175)),
         beach=dict(amount=0.8, harmonic=1, phase=235, power=2.6, width=5.0, rise=1.0,
                    base_w=0.6, base_rise=0.3),
         levels=(wall(3.8, 2)
                 + shelf(0.3, 0.35, wob_freq=1.5, rise_var=0.05,
                         inset=dict(amount=7.5, harmonic=1, phase=55, power=4.0))
                 + wall(6.6, 5)),
         tilt=(0.34, 230),
         cap=dict(roll=(0.75, 0.08), spacing=2.6, blend=0.45),
         beach_top=1.3, terrace_grass=1.7,
         stacks=[(29, -16, 3.0, 4.2), (-27, 17, 2.4, 3.0, 6)]),

    # a small island whose two arms close around a sheltered basin
    dict(id='devlog', kind='hero', radius=25, size=72, seed=83, M=96,
         outline=dict(lobes=[(0, 8, 12), (-12.5, -4, 9.5), (12.5, -4, 9.5), (-3, 1, 8)], k=1.6,
                      bays=[(0, -12, 8.6)], bk=1.6, warp=(2.6, 0.045), warp2=(1.45, 0.175)),
         beach=dict(amount=0.85, cover=0.40, seed=83, width=4.4, rise=1.1,
                    base_w=0.6, base_rise=0.35),
         levels=wall(2.8, 2) + shelf(0.3, 1.0, wob_freq=1.4, rise_var=0.1) + wall(3.8, 3),
         tilt=(0.38, 150),
         cap=dict(roll=(0.8, 0.1), spacing=2.3, blend=0.5),
         beach_top=2.0, grass_from=3.2,
         stacks=[(-21, 16, 2.6, 3.6), (21, 15, 2.2, 2.8, 6)]),

    # ------------------------------------------------------------- islets
    dict(id='islet_01', kind='islet', radius=9, size=28, seed=101, M=46, snowline=8.6,
         outline=dict(lobes=[(0, 0, 6.2), (2.5, 1.8, 4.0)], warp=(1.5, 0.09), warp2=(0.5, 0.3)),
         beach=dict(amount=0.25, cover=0.2, seed=101, width=1.0, rise=0.4,
                    base_w=0.4, base_rise=0.2),
         levels=strata([(2.0, 1.0), (2.2, 0.9), (2.4, 0.9), (2.4, 0.8), (2.2, 0.8), (2.0, 0.7)], run=0.18),
         cap=dict(roll=(0.7, 0.3), spacing=1.0, blend=0.9, dome=1.8),
         sea=dict(floor=5.5, shelf_out=4.5, shelf_z=2.8, shallow_out=1.4, shallow_z=0.6),
         stacks=[(-8, -5, 1.8, 2.8, 6)]),

    dict(id='islet_02', kind='islet', radius=7, size=22, seed=113, M=52,
         outline=dict(lobes=[(0, 0, 5.0), (2.5, -2, 3.2)], warp=(1.2, 0.1), warp2=(0.4, 0.3)),
         beach=dict(amount=0.85, cover=0.42, seed=113, width=1.2, rise=0.6,
                    base_w=0.4, base_rise=0.2),
         levels=wall(1.5, 1, run=0.08) + shelf(0.25, 1.1, rise_var=0.1) + wall(2.0, 2, run=0.08),
         cap=dict(roll=(0.4, 0.2), spacing=1.0, blend=0.4),
         sea=dict(floor=5.0, shelf_out=3.8, shelf_z=2.4, shallow_out=1.3, shallow_z=0.55),
         beach_top=1.6,
         stacks=[(6.5, 4.5, 1.5, 2.2, 6)]),

    dict(id='islet_03', kind='islet', radius=11, size=32, seed=127, M=64,
         outline=dict(lobes=[(0, 0, 7.4), (4, 3.5, 4.6), (-4, -3, 4.2)],
                      warp=(1.7, 0.08), warp2=(0.5, 0.26)),
         beach=dict(amount=0.5, cover=0.28, seed=127, width=1.5, rise=0.7,
                    base_w=0.5, base_rise=0.25),
         levels=wall(2.4, 2, run=0.08) + shelf(0.3, 1.3, rise_var=0.1) + wall(3.2, 3, run=0.08),
         cap=dict(roll=(0.6, 0.16), spacing=1.2, blend=0.38),
         sea=dict(floor=5.5, shelf_out=5.0, shelf_z=2.9, shallow_out=1.8, shallow_z=0.6),
         stacks=[(-11, 7, 1.9, 2.8, 6)]),

    dict(id='islet_04', kind='islet', radius=8, size=24, seed=131, M=52, band_h=1.7,
         outline=dict(lobes=[(0, 0, 5.6)], warp=(1.2, 0.1), warp2=(0.4, 0.3)),
         beach=dict(amount=0.3, cover=0.2, seed=131, width=1.4, rise=0.5,
                    base_w=0.4, base_rise=0.2),
         levels=wall(1.6, 1, run=0.08) + strata([(2.0, 1.25)] * 4, run=0.3),
         cap=dict(roll=(0.3, 0.3), spacing=0.9, blend=0.5, crater=(0, 0, 2.2, 2.4)),
         lava=(0, 0, 1.5, 8.6),
         sea=dict(floor=5.0, shelf_out=4.0, shelf_z=2.5, shallow_out=1.4, shallow_z=0.55),
         **BASALT),

    # palm atoll: a low sand ring around a lagoon
    dict(id='islet_05', kind='islet', radius=10, size=30, seed=149, M=80, beach_top=2.4,
         outline=dict(lobes=[dict(t='ring', x=0, y=0, r=7.0, w=1.3), (5.6, -5.2, 2.2)],
                      warp=(1.0, 0.11), warp2=(0.4, 0.3)),
         beach=dict(amount=1.0, cover=0.85, seed=149, width=1.2, rise=0.5,
                    base_w=0.5, base_rise=0.35),
         levels=strata([(1.7, 0.9)], run=0.25),
         cap=dict(roll=(0.16, 0.32), spacing=0.9, blend=0.5, crater=(0, 0, 7.2, 3.6)),
         sea=dict(floor=4.6, shelf_out=2.4, shelf_z=2.0, shallow_out=1.1, shallow_z=0.45),
         ring_noise=(0.22, 0.1),
         stacks=[(-9, 6.5, 1.5, 2.0, 6)]),

    dict(id='islet_06', kind='islet', radius=6, size=20, seed=157, M=56,
         outline=dict(lobes=[(0, 0, 3.8)], warp=(0.9, 0.12), warp2=(0.4, 0.3)),
         beach=dict(amount=0.45, cover=0.3, seed=157, width=1.0, rise=0.45,
                    base_w=0.4, base_rise=0.2),
         levels=wall(1.6, 1, run=0.08) + shelf(0.25, 0.9, rise_var=0.1) + wall(2.0, 2, run=0.08),
         cap=dict(roll=(0.3, 0.26), spacing=0.8, blend=0.4),
         sea=dict(floor=4.6, shelf_out=3.4, shelf_z=2.2, shallow_out=1.2, shallow_z=0.5),
         stacks=[(6.2, 3.8, 1.3, 3.2), (-5.6, 3.0, 1.0, 2.2, 6), (3.2, -6.2, 0.9, 1.7, 6)]),

    dict(id='islet_07', kind='islet', radius=7, size=22, seed=163, M=64, snowline=7.2,
         outline=dict(lobes=[(0, 0, 4.6), (-2, 1.6, 3.0)], warp=(1.2, 0.1), warp2=(0.4, 0.3)),
         levels=strata([(1.9, 0.8), (2.1, 0.75), (2.2, 0.7), (2.2, 0.65), (2.0, 0.6)], run=0.16),
         cap=dict(roll=(0.6, 0.3), spacing=0.9, blend=0.9, dome=1.6),
         sea=dict(floor=5.0, shelf_out=3.6, shelf_z=2.4, shallow_out=1.2, shallow_z=0.55),
         stacks=[(6, -4, 1.6, 2.6, 6)]),

    dict(id='islet_08', kind='islet', radius=12, size=34, seed=173, M=68,
         outline=dict(lobes=[(0, 0, 7.8), (5, -4, 5.2), (-5, 4, 4.8)],
                      warp=(1.9, 0.075), warp2=(0.5, 0.25)),
         beach=dict(amount=0.45, cover=0.28, seed=173, width=1.6, rise=0.7,
                    base_w=0.5, base_rise=0.25),
         levels=wall(2.8, 2, run=0.08) + shelf(0.3, 1.5, rise_var=0.1) + wall(3.8, 3, run=0.08),
         cap=dict(roll=(0.7, 0.14), spacing=1.3, blend=0.36),
         sea=dict(floor=5.8, shelf_out=5.4, shelf_z=3.0, shallow_out=1.9, shallow_z=0.6),
         stacks=[(12, 8, 2.1, 3.4, 6), (-12, -8, 1.7, 2.6, 6)]),
]


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    only = None
    do_render = "--no-render" not in argv
    if "--only" in argv:
        only = set(argv[argv.index("--only") + 1].split(","))
    samples = 40
    if "--samples" in argv:
        samples = int(argv[argv.index("--samples") + 1])

    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    L.setup_scene(samples=samples)

    manifest_path = os.path.join(OUT, "manifest.json")
    entries = {}
    if os.path.exists(manifest_path):
        try:
            entries = {e['id']: e for e in json.load(open(manifest_path, encoding='utf-8')).get('islands', [])}
        except Exception:
            entries = {}

    total = 0
    for spec in SPECS:
        if only and spec['id'] not in only:
            continue
        obj, tris, rings = L.build_island(spec, spec['id'])
        zmin, zmax, Z = L.write_height(spec, rings, obj, OUT)
        L.export_glb(obj, os.path.join(OUT, spec['id'] + ".glb"))
        kb = os.path.getsize(os.path.join(OUT, spec['id'] + ".glb")) // 1024
        entries[spec['id']] = dict(
            id=spec['id'], radius=spec['radius'], size=spec['size'],
            maxHeight=round(zmax, 3), minHeight=round(zmin, 3), triangles=int(tris),
            kind=spec['kind'], mesh=spec['id'] + ".glb", height=spec['id'] + "_height.png")

        extra = ""
        if spec['id'] == 'combat':
            extra = "  open ground {:.1f} m across".format(free_circle(Z, spec['size']))
            entries[spec['id']]['openGround'] = round(free_circle(Z, spec['size']), 1)
        print("[isl] {:<10} tris={:<6} {:>4} KB  h={:+.1f}..{:+.1f}{}".format(
            spec['id'], tris, kb, zmin, zmax, extra))
        total += tris
        if do_render:
            L.render_island(obj, os.path.join(SHOTS, spec['id'] + ".png"), spec['radius'], zmax)
        bpy.data.objects.remove(obj, do_unlink=True)

    order = [s['id'] for s in SPECS]
    out = dict(
        note="Island meshes for the Skillstorm promo site. Metres, Y up, origin at the "
             "island centre, y=0 is the waterline. Vertex colours only, one material, "
             "flat shaded. <id>_height.png is a 256x256 16-bit greyscale heightmap over "
             "the island's bounding square (size metres on a side, centred on the origin). "
             "Column 0 is x = -size/2, row 0 is z = -size/2, both in the glTF frame: "
             "x = -size/2 + col/(res-1)*size, z = -size/2 + row/(res-1)*size. "
             "height = minHeight + (R/65535)*(maxHeight-minHeight).",
        islands=[entries[i] for i in order if i in entries])
    with open(manifest_path, "w", encoding='utf-8') as f:
        json.dump(out, f, indent=2)
    print("[isl] total tris", total)


if __name__ == "__main__":
    main()
