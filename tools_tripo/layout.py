"""Turn the painting's flat arrangement into places on the sea.

The painting is a perspective view, so an island low in the frame is near and one
near the horizon is far away. Firing a ray through each island's waterline and
catching it on the water plane gives the arrangement back as real positions.

Taken literally the far band lands twenty times further out than the near one,
which no camera but the painting's own can hold, so distance is compressed —
and each island is scaled by the same amount, which means the painting's camera
still sees exactly the painting, while any other view sees a sane archipelago.
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

FOV_Y = 40.0          # the painting's vertical field of view, degrees
HORIZON_ROW = 94      # where sea meets sky in the source image
COMPRESS = 0.48       # 1.0 = literal perspective, lower pulls the far band in
NEAR = 3.0            # camera heights within which the painting is kept literal
HERO_ID = "isle_01"   # the island the whole archipelago is scaled against
HERO_RADIUS = 58.0    # metres across its half-width; the fight needs 38 m clear
MIN_GEN_PX = 110      # narrower than this in the painting and there is nothing to read
FAR_MANUAL = [         # x0, y0, x1, y1 in the painting: islands the far-band test missed
    [285, 62, 355, 80], [660, 66, 728, 82], [1040, 105, 1200, 140],
    [795, 148, 845, 165], [1100, 200, 1146, 215], [155, 185, 198, 203],
]


def build(meta, extra=()):
    w_px, h_px = meta["size"]
    half = h_px / 2.0
    tan_half = math.tan(math.radians(FOV_Y) / 2.0)
    # the horizon row fixes how far the camera is pitched down
    theta = math.atan((half - HORIZON_ROW) / half * tan_half)
    st, ct = math.sin(theta), math.cos(theta)

    items = list(meta["islands"]) + list(extra)
    out = []
    for e in items:
        x0, y0, x1, y1 = e["bbox"]
        # across: the middle of the island; in depth: its near waterline. The lowest
        # row alone can sit at one end of the island (an arch, a spit) and drag it
        # sideways, so it only decides how far away the island is.
        ax, ay = (x0 + x1) / 2.0, y1
        a = (ax - w_px / 2.0) / half * tan_half
        b = (half - ay) / half * tan_half
        dy = -st + b * ct
        dz = -ct - b * st
        if dy > -1e-4:
            continue                      # at or above the horizon, no footing
        t = 1.0 / -dy                     # distance in camera heights
        px, pz = a * t, dz * t

        d = math.hypot(px, pz)
        # Only the far band is pulled in. Compressing the near islands too would move
        # them toward a camera whose height stays put, so they would grow and sink in
        # the frame; out past a few camera heights that error is a sliver of a degree.
        k = 1.0 if d <= NEAR else (NEAR * (d / NEAR) ** COMPRESS) / d
        # half-width of the island at its own distance, same units
        rad = (x1 - x0) / 2.0 / half * tan_half * t

        out.append({
            "id": e.get("id") or "isle_%02d" % e["index"],
            "src": e["index"],
            "bbox": e["bbox"],
            "image_anchor": [ax, ay],
            "raw_pos": [px, pz],
            "raw_radius": rad,
            "pos": [px * k, pz * k],
            "radius": rad * k,
            "depth": d,
            # a tiny blob in the painting carries no shape worth generating, so it
            # gets one of the generated rock clusters instead
            "kind": ("far" if e.get("far") else
                     "island" if (x1 - x0) >= MIN_GEN_PX else "rock"),
        })

    out.sort(key=lambda e: e["depth"])
    hero = next(e for e in out if e["id"] == HERO_ID)
    scale = HERO_RADIUS / hero["radius"]
    for e in out:
        e["pos"] = [round(e["pos"][0] * scale, 2), round(e["pos"][1] * scale, 2)]
        e["radius"] = round(e["radius"] * scale, 2)
        e["raw_pos"] = [round(v * scale, 2) for v in e["raw_pos"]]
        e["raw_radius"] = round(e["raw_radius"] * scale, 2)

    cam_h = scale  # one camera height is one unit before scaling
    return {
        "camera": {
            "fov_y": FOV_Y, "pitch_deg": round(math.degrees(theta), 2),
            "height": round(cam_h, 2), "compress": COMPRESS,
        },
        "islands": out,
    }


def main():
    # the true outlines from the cut, not the first rough segmentation
    raw = json.load(open(os.path.join(HERE, "islands_raw.json"), encoding="utf-8"))
    cut = json.load(open(os.path.join(HERE, "islands_cut.json"), encoding="utf-8"))
    # the far band near the horizon: found by find_far.py, plus a few the eye sees
    # and the colour test misses; they get existing models, not new generations
    far = []
    p = os.path.join(HERE, "far_islands.json")
    if os.path.exists(p):
        far = [e for e in json.load(open(p, encoding="utf-8"))
               if (e["bbox"][2] - e["bbox"][0]) >= 10]
    for k, box in enumerate(FAR_MANUAL):
        far.append({"id": "farm_%02d" % (k + 1), "bbox": box, "area": 0})
    for e in far:
        e["far"] = True
    meta = {"size": raw["size"], "islands": [dict(e, index=i + 1) for i, e in enumerate(cut + far)]}
    data = build(meta)
    json.dump(data, open(os.path.join(HERE, "islands_layout.json"), "w",
                         encoding="utf-8"), indent=1)
    c = data["camera"]
    gen = [e for e in data["islands"] if e["kind"] == "island"]
    print("camera pitch %.1f deg, height %.0f m, %d places: %d islands, %d rocks"
          % (c["pitch_deg"], c["height"], len(data["islands"]),
             len(gen), len(data["islands"]) - len(gen)))
    for e in data["islands"]:
        print(" %-10s %-7s pos %8.1f %8.1f  r %6.1f  px %4d"
              % (e["id"], e["kind"], e["pos"][0], e["pos"][1], e["radius"],
                 e["bbox"][2] - e["bbox"][0]))


if __name__ == "__main__":
    main()
