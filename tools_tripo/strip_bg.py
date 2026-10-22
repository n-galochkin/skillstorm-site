"""Knock the flat backdrop out of a generated island so only the island is left.

The backdrop is one even colour, but so are parts of the island's own pale stone,
so a colour test alone would bite into the cliffs. The backdrop is instead found
by flooding inward from the frame edge through pixels close to the corner colour:
stone of the same shade inside the island is never reached.

Run: python strip_bg.py <in.png> <out.png> [tolerance]
"""
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mask as M  # noqa: E402


def main():
    src, dst = sys.argv[1], sys.argv[2]
    tol = float(sys.argv[3]) if len(sys.argv) > 3 else 0.065

    img = Image.open(src).convert("RGB")
    a = np.asarray(img).astype(np.float32) / 255.0
    h, w = a.shape[:2]
    k = max(4, int(min(h, w) * 0.01))
    corners = np.concatenate([
        a[:k, :k].reshape(-1, 3), a[:k, -k:].reshape(-1, 3),
        a[-k:, :k].reshape(-1, 3), a[-k:, -k:].reshape(-1, 3)])
    bg = np.median(corners, axis=0)

    near = np.sqrt(((a - bg) ** 2).sum(axis=-1)) < tol
    # The generator often lays a soft cast shadow on the backdrop: darker, but the
    # same cool grey. Stone on the island is warm, so a cool, colourless, darker
    # pixel is still backdrop as far as the flood is concerned.
    _, sat, val = M.to_hsv(a)
    cool = (a[..., 2] >= a[..., 0] - 0.01) & (sat < 0.16)
    shade = cool & (val < bg.max() + 0.02) & (val > bg.max() * 0.45)
    back = M.flood_from_border(near | shade)
    land = ~back

    land = M.erode(land, 1)
    lab, n = M.label(land)
    if n:
        sizes = np.bincount(lab.ravel())
        sizes[0] = 0
        # 'main' keeps only the biggest piece: a generator likes to scatter boulders
        # beside a rock, and from this angle they hang in the air
        only_main = len(sys.argv) > 4 and sys.argv[4] == 'main'
        floor = sizes.max() if only_main else sizes.max() * 0.004
        land = np.isin(lab, np.flatnonzero(sizes >= floor))
    land = M.dilate(land, 1)
    # pinholes inside the island are filled, but a real opening — the hole under a
    # sea arch — is far larger than a pinhole and stays see-through
    holes, hn = M.label(~land)
    if hn:
        edge = set(np.unique(np.concatenate([
            holes[0], holes[-1], holes[:, 0], holes[:, -1]])).tolist())
        sizes = np.bincount(holes.ravel())
        small = [i for i in range(1, hn + 1)
                 if i not in edge and sizes[i] < land.sum() * 0.003]
        land |= np.isin(holes, small)

    ys, xs = np.nonzero(land)
    if not len(xs):
        raise SystemExit("nothing left after stripping the background")
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    pad = int(round(max(x1 - x0, y1 - y0) * 0.06))
    x0, y0 = max(0, x0 - pad), max(0, y0 - pad)
    x1, y1 = min(w - 1, x1 + pad), min(h - 1, y1 + pad)

    alpha = M.soft_alpha(land, feather=1)[y0:y1 + 1, x0:x1 + 1]
    rgb = np.asarray(img)[y0:y1 + 1, x0:x1 + 1]
    out = Image.fromarray(np.dstack([rgb, alpha * 255]).astype(np.uint8), "RGBA")

    ow, oh = out.size
    side = max(ow, oh)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(out, ((side - ow) // 2, (side - oh) // 2))
    canvas.save(dst)
    flat = Image.new("RGB", canvas.size, (170, 174, 178))
    flat.paste(canvas, (0, 0), canvas)
    flat.save(os.path.splitext(dst)[0] + "_preview.jpg", quality=92)
    print("kept %.1f%% of the frame, wrote %s (%dx%d)"
          % (100 * land.mean(), dst, side, side))


if __name__ == "__main__":
    main()
