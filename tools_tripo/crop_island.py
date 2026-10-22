"""Cut one island out of the painting as a clean image for the 3D generator.

The generator wants a single subject on an empty background, so everything that is
sea — open water, the lagoon inside a bay, the foam ring — is made transparent and
only the land mass itself is kept, centred with a margin around it.
"""
import json
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = r"C:/Projects/SkillStorm/Content/SourceArt/StartScreen/T_ArchipelagoSource.png"
OUT = os.path.join(HERE, "crops")

sys.path.insert(0, HERE)
from segment_islands import to_hsv, binary_dilate, binary_erode, label  # noqa: E402


def land_mask(a):
    h, s, v = to_hsv(a)
    water = ((h > 170) & (h < 225) & (s > 0.30)) | ((v > 0.86) & (s < 0.22))
    land = ~water
    land = binary_erode(land, 1)
    land = binary_dilate(land, 4)
    land = binary_erode(land, 3)
    return land


def main():
    index = int(sys.argv[1])
    pad = float(sys.argv[2]) if len(sys.argv) > 2 else 0.10
    long_side = int(sys.argv[3]) if len(sys.argv) > 3 else 1024

    os.makedirs(OUT, exist_ok=True)
    meta = json.load(open(os.path.join(HERE, "islands_raw.json"), encoding="utf-8"))
    spec = next(e for e in meta["islands"] if e["index"] == index)
    x0, y0, x1, y1 = spec["bbox"]

    img = Image.open(SRC).convert("RGB")
    a = np.asarray(img).astype(np.float32) / 255.0
    land = land_mask(a)

    # keep only the blob this bounding box belongs to, so a neighbour that leans
    # into the same rectangle is not glued onto the island
    lab, n = label(land)
    sub = lab[y0:y1 + 1, x0:x1 + 1]
    ids, counts = np.unique(sub[sub > 0], return_counts=True)
    keep = ids[np.argmax(counts)]
    mask = (lab == keep)

    # sunlit rock and bright grass read as "bright and colourless" just like foam,
    # so the mask comes out full of pinholes; anything enclosed by the island is
    # island, while a bay that opens into the sea stays open
    holes, hn = label(~mask)
    edge = set(np.unique(np.concatenate([
        holes[0], holes[-1], holes[:, 0], holes[:, -1]])).tolist()) - {0}
    mask |= ~np.isin(holes, list(edge)) & (holes > 0)

    px = int(round((x1 - x0 + 1) * pad))
    py = int(round((y1 - y0 + 1) * pad))
    cx0, cy0 = max(0, x0 - px), max(0, y0 - py)
    cx1, cy1 = min(img.size[0] - 1, x1 + px), min(img.size[1] - 1, y1 + py)

    rgb = np.asarray(img)[cy0:cy1 + 1, cx0:cx1 + 1]
    alpha = (mask[cy0:cy1 + 1, cx0:cx1 + 1] * 255).astype(np.uint8)
    rgba = np.dstack([rgb, alpha])
    out = Image.fromarray(rgba, "RGBA")

    # square canvas: the generator reads a centred subject better than a wide strip
    w, hgt = out.size
    side = max(w, hgt)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(out, ((side - w) // 2, (side - hgt) // 2))
    scale = long_side / side
    canvas = canvas.resize((long_side, long_side), Image.LANCZOS)

    path = os.path.join(OUT, "island_%02d.png" % index)
    canvas.save(path)

    # what the mask kept, over white, for a quick look
    white = Image.new("RGB", canvas.size, (255, 255, 255))
    white.paste(canvas, (0, 0), canvas)
    white.save(os.path.join(OUT, "island_%02d_preview.jpg" % index), quality=92)

    print(json.dumps({
        "index": index, "path": path, "bbox": [x0, y0, x1, y1],
        "crop": [cx0, cy0, cx1, cy1], "px_per_unit": scale,
        "coverage": round(float((alpha > 0).mean()), 3),
    }))


if __name__ == "__main__":
    main()
