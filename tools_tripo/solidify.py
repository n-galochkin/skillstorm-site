"""Close the bites and gaps in a cut-out before it goes to the image generator.

Where trees or rock spires stand against the sea, the cut leaves notches and see-
through gaps along the coast, and the generator faithfully redraws every one of
them. Exact outline is not what we need, a solid island is: so the outline is
closed over a wide radius and the newly covered pixels take the colour of the
island around them.

Run: python solidify.py <in.png> <out.png> [radius]
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
    radius = int(sys.argv[3]) if len(sys.argv) > 3 else 14

    im = np.asarray(Image.open(src).convert("RGBA")).astype(np.float32)
    rgb, a = im[..., :3], im[..., 3] / 255.0
    solid = a > 0.5

    closed = M.erode(M.dilate(solid, radius), radius)
    closed |= ~M.flood_from_border(~closed)          # and nothing see-through inside
    added = closed & ~solid

    # spread the island's own colours into the filled pixels, ring by ring
    known = solid.copy()
    col = np.where(known[..., None], rgb, 0.0)
    for _ in range(radius * 3):
        if not (added & ~known).any():
            break
        p = np.pad(col, ((1, 1), (1, 1), (0, 0)), mode="edge")
        w = np.pad(known.astype(np.float32), 1, mode="edge")
        num = (p[:-2, 1:-1] * w[:-2, 1:-1, None] + p[2:, 1:-1] * w[2:, 1:-1, None]
               + p[1:-1, :-2] * w[1:-1, :-2, None] + p[1:-1, 2:] * w[1:-1, 2:, None])
        den = w[:-2, 1:-1] + w[2:, 1:-1] + w[1:-1, :-2] + w[1:-1, 2:]
        grow = added & ~known & (den > 0)
        col[grow] = num[grow] / den[grow][:, None]
        known |= grow

    alpha = M.soft_alpha(closed, feather=2)
    out = np.dstack([np.clip(col, 0, 255), alpha * 255]).astype(np.uint8)
    Image.fromarray(out, "RGBA").save(dst)
    flat = Image.new("RGB", (out.shape[1], out.shape[0]), (170, 174, 178))
    flat.paste(Image.fromarray(out, "RGBA"), (0, 0), Image.fromarray(out, "RGBA"))
    flat.save(os.path.splitext(dst)[0] + "_preview.jpg", quality=92)
    print("filled %d px (%.1f%% of the island)" % (added.sum(), 100 * added.sum() / max(solid.sum(), 1)))


if __name__ == "__main__":
    main()
