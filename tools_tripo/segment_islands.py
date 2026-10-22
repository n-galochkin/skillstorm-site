"""Pull the individual islands out of the start-screen painting.

The painting is one flat image; what we need is a list of separate land masses with
their place in the frame, so each one can be sent to an image-to-3D generator and
then put back on the sea in the same arrangement.

Water is told from land by colour: the sea is a saturated blue-cyan, the foam and
the haze are bright and almost colourless, everything else (grass, rock, sand,
roofs) is land. Touching pixels of land then become one island.
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = r"C:/Projects/SkillStorm/Content/SourceArt/StartScreen/T_ArchipelagoSource.png"


def to_hsv(rgb):
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    mx = rgb.max(axis=-1)
    mn = rgb.min(axis=-1)
    d = mx - mn
    h = np.zeros_like(mx)
    m = (d > 1e-6) & (mx == r)
    h[m] = ((g - b)[m] / d[m]) % 6
    m = (d > 1e-6) & (mx == g)
    h[m] = ((b - r)[m] / d[m]) + 2
    m = (d > 1e-6) & (mx == b)
    h[m] = ((r - g)[m] / d[m]) + 4
    h = h * 60.0
    s = np.where(mx > 1e-6, d / np.maximum(mx, 1e-6), 0.0)
    return h, s, mx


def binary_dilate(mask, radius):
    out = mask.copy()
    for _ in range(radius):
        p = np.pad(out, 1, mode="constant", constant_values=False)
        out = (p[1:-1, 1:-1] | p[:-2, 1:-1] | p[2:, 1:-1] | p[1:-1, :-2] | p[1:-1, 2:])
    return out


def binary_erode(mask, radius):
    return ~binary_dilate(~mask, radius)


def label(mask):
    """Two-pass connected components with union-find, 8-connected."""
    h, w = mask.shape
    lab = np.zeros((h, w), dtype=np.int32)
    parent = [0]

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    nxt = 1
    for y in range(h):
        row = mask[y]
        if not row.any():
            continue
        prev = lab[y - 1] if y else None
        for x in np.flatnonzero(row):
            n = []
            if x and lab[y, x - 1]:
                n.append(lab[y, x - 1])
            if prev is not None:
                for xx in (x - 1, x, x + 1):
                    if 0 <= xx < w and prev[xx]:
                        n.append(prev[xx])
            if n:
                m = min(n)
                lab[y, x] = m
                for o in n:
                    union(m, o)
            else:
                lab[y, x] = nxt
                parent.append(nxt)
                nxt += 1

    remap = np.zeros(nxt, dtype=np.int32)
    order = {}
    for i in range(1, nxt):
        r = find(i)
        if r not in order:
            order[r] = len(order) + 1
        remap[i] = order[r]
    return remap[lab], len(order)


def main():
    min_area = int(sys.argv[1]) if len(sys.argv) > 1 else 900
    img = Image.open(SRC).convert("RGB")
    a = np.asarray(img).astype(np.float32) / 255.0
    h, s, v = to_hsv(a)

    # the horizon: above it is sky, and nothing there is an island
    horizon = 0
    for y in range(a.shape[0]):
        if (s[y] > 0.45).mean() > 0.25:
            horizon = y
            break

    water = ((h > 170) & (h < 225) & (s > 0.30)) | ((v > 0.86) & (s < 0.22))
    land = ~water
    land[:horizon + 2] = False

    land = binary_erode(land, 1)          # drop the speckle inside the sea
    land = binary_dilate(land, 4)         # join a beach to the rock it belongs to
    land = binary_erode(land, 3)

    lab, n = label(land)
    items = []
    for i in range(1, n + 1):
        ys, xs = np.nonzero(lab == i)
        area = len(xs)
        if area < min_area:
            continue
        x0, x1, y0, y1 = int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())
        items.append({
            "index": len(items) + 1,
            "bbox": [x0, y0, x1, y1],
            "w": x1 - x0 + 1,
            "h": y1 - y0 + 1,
            "area": int(area),
            # the waterline at the bottom of the mass is what anchors it on the sea
            "anchor": [int(round(xs[ys > y1 - 3].mean())), y1],
        })

    items.sort(key=lambda e: -e["area"])
    for k, e in enumerate(items):
        e["index"] = k + 1

    out = {"source": SRC, "size": list(img.size), "horizon": horizon, "islands": items}
    with open(os.path.join(HERE, "islands_raw.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)

    vis = img.copy()
    d = ImageDraw.Draw(vis)
    d.line([(0, horizon), (img.size[0], horizon)], fill=(255, 0, 255), width=2)
    for e in items:
        x0, y0, x1, y1 = e["bbox"]
        d.rectangle([x0, y0, x1, y1], outline=(255, 60, 60), width=2)
        d.text((x0 + 3, y0 + 2), str(e["index"]), fill=(255, 255, 0))
    vis.save(os.path.join(HERE, "segmented.png"))

    print("horizon row", horizon)
    print("islands kept", len(items), "of", n)
    for e in items[:40]:
        print(" %2d area %7d  bbox %s" % (e["index"], e["area"], e["bbox"]))


if __name__ == "__main__":
    main()
