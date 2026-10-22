"""Find the small islands in the far band of the painting, near the horizon.

Out there land and sea are washed toward the same blue, so the near-field flood
finds nothing. Each row is compared with the sea's own colour in that row (the
row median, since open water fills most of it), and what stands out is land.
Blobs that already belong to a cut island are left alone.

Writes far_islands.json: [{id, bbox, anchor, area}], and far_found.png to look at.
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mask as M  # noqa: E402

SRC = r"C:/Projects/SkillStorm/Content/SourceArt/StartScreen/T_ArchipelagoSource.png"
BAND = (96, 300)        # rows: just under the horizon down to where the near flood works
TOL = 0.085
MIN_AREA = 40


def main():
    img = Image.open(SRC).convert("RGB")
    a = np.asarray(img).astype(np.float32) / 255.0
    y0, y1 = BAND
    band = a[y0:y1]
    bg = np.median(band, axis=1)[:, None, :]
    diff = np.sqrt(((band - bg) ** 2).sum(axis=-1))
    land = diff > TOL
    land = M.erode(land, 1)
    land = M.dilate(land, 2)

    lab, n = M.label(land)
    cut = json.load(open(os.path.join(HERE, "islands_cut.json"), encoding="utf-8"))
    taken = np.zeros(a.shape[:2], bool)
    for e in cut:
        x0, by0, x1, by1 = e["bbox"]
        taken[max(0, by0 - 6):by1 + 7, max(0, x0 - 6):x1 + 7] = True

    found = []
    for i in range(1, n + 1):
        ys, xs = np.nonzero(lab == i)
        if len(xs) < MIN_AREA:
            continue
        ys = ys + y0
        if taken[ys, xs].mean() > 0.3:
            continue
        bx0, bx1, by0, by1 = int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())
        if bx1 - bx0 < 8 or (by1 - by0) > (bx1 - bx0) * 1.6:
            continue                                   # a foam streak, not an island
        found.append({"bbox": [bx0, by0, bx1, by1], "area": int(len(xs)),
                      "anchor": [int((bx0 + bx1) / 2), by1]})

    found.sort(key=lambda e: (e["bbox"][1], e["bbox"][0]))
    for k, e in enumerate(found):
        e["id"] = "far_%02d" % (k + 1)
    json.dump(found, open(os.path.join(HERE, "far_islands.json"), "w", encoding="utf-8"), indent=1)

    vis = img.copy()
    d = ImageDraw.Draw(vis)
    for e in cut:
        d.rectangle(e["bbox"], outline=(80, 255, 80), width=1)
    for e in found:
        d.rectangle(e["bbox"], outline=(255, 60, 60), width=2)
    vis.crop((0, 60, img.size[0], 420)).save(os.path.join(HERE, "far_found.png"))
    print(len(found), "far islands")


if __name__ == "__main__":
    main()
