"""Cut an island that stands in the distance haze.

Far away, land and sea are both washed toward the same pale blue, so the flood
that separates them near the camera finds no edge at all. Here the sea colour is
read from the water right beside the island instead, and anything that differs
from it by more than a little is land.

Run: python cut_hazy.py <id> x0 y0 x1 y1
"""
import json
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mask as M  # noqa: E402

SRC = r"C:/Projects/SkillStorm/Content/SourceArt/StartScreen/T_ArchipelagoSource.png"
OUT = os.path.join(HERE, "crops")


def main():
    name = sys.argv[1]
    x0, y0, x1, y1 = (int(v) for v in sys.argv[2:6])
    tol = float(sys.argv[6]) if len(sys.argv) > 6 else 0.055

    img = Image.open(SRC).convert("RGB")
    a = np.asarray(img).astype(np.float32) / 255.0
    box = a[y0:y1 + 1, x0:x1 + 1]

    # The box holds both sky and sea, and they are different colours, so one
    # reference cannot serve the whole of it. Each row gets its own background,
    # read from the margins at the left and right of the box, where the island
    # does not reach; what differs from it across the row is the island.
    edge = int(max(6, (x1 - x0) * 0.06))
    margin = np.concatenate([box[:, :edge], box[:, -edge:]], axis=1)
    bg = np.median(margin, axis=1)[:, None, :]
    diff = np.sqrt(((box - bg) ** 2).sum(axis=-1))
    land = diff > tol

    land = M.erode(land, 1)
    land = M.dilate(land, 2)
    lab, n = M.label(land)
    sizes = np.bincount(lab.ravel())
    sizes[0] = 0
    land = (lab == int(sizes.argmax()))
    # the ridge line breaks into separate peaks against the sky; close it back up
    land = M.dilate(land, 3)
    land = M.erode(land, 3)
    holes, hn = M.label(~land)
    edge = set(np.unique(np.concatenate([
        holes[0], holes[-1], holes[:, 0], holes[:, -1]])).tolist()) - {0}
    land |= (holes > 0) & ~np.isin(holes, list(edge))

    # the shoreline frays into the water along the bottom; keep only the rows that
    # still hold a decent run of island, so no strip of sea rides along
    width = land.sum(axis=1)
    solid = np.flatnonzero(width > width.max() * 0.12)
    land[solid[-1] + 1:] = False

    ys, xs = np.nonzero(land)
    bx0, bx1, by0, by1 = xs.min(), xs.max(), ys.min(), ys.max()
    land = land[by0:by1 + 1, bx0:bx1 + 1]
    rgb = np.asarray(img)[y0 + by0:y0 + by1 + 1, x0 + bx0:x0 + bx1 + 1]

    pad = int(round(max(land.shape) * 0.10))
    alpha = M.soft_alpha(np.pad(land, pad), feather=1)
    rgb = np.pad(rgb, ((pad, pad), (pad, pad), (0, 0)), mode="edge")

    # Distance lays a blue veil over the island: what reaches the eye is part its
    # own colour and part the colour of the air in between. Taking that share of
    # the background back out brings the rock and the greenery back.
    f = rgb.astype(np.float32) / 255.0
    veil = float(sys.argv[7]) if len(sys.argv) > 7 else 0.5
    air = np.median(bg.reshape(-1, 3), axis=0)
    f = np.clip((f - veil * air) / (1.0 - veil), 0, 1)

    rgba = np.dstack([f * 255, alpha * 255]).astype(np.uint8)
    out = Image.fromarray(rgba, "RGBA")
    w, h = out.size
    side = max(w, h)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(out, ((side - w) // 2, (side - h) // 2))
    canvas = canvas.resize((1024, 1024), Image.LANCZOS)

    os.makedirs(OUT, exist_ok=True)
    canvas.save(os.path.join(OUT, name + ".png"))
    flat = Image.new("RGB", canvas.size, (170, 174, 178))
    flat.paste(canvas, (0, 0), canvas)
    flat.save(os.path.join(OUT, name + "_preview.jpg"), quality=92)

    rec = {"id": name, "bbox": [int(x0 + bx0), int(y0 + by0), int(x0 + bx1), int(y0 + by1)],
           "anchor": [int(x0 + (bx0 + bx1) // 2), int(y0 + by1)],
           "area": int(land.sum()), "coverage": round(float((alpha > 0.5).mean()), 3)}

    path = os.path.join(HERE, "islands_cut.json")
    have = {}
    if os.path.exists(path):
        have = {e["id"]: e for e in json.load(open(path, encoding="utf-8"))}
    have[name] = rec
    json.dump(sorted(have.values(), key=lambda e: -e["area"]),
              open(path, "w", encoding="utf-8"), indent=1)
    print(json.dumps(rec))


if __name__ == "__main__":
    main()
