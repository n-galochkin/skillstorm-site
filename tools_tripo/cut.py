"""Cut every island out of the painting as its own clean image.

Run with no arguments to redo the whole set, or with island numbers to redo a few.
Each island gets a transparent PNG for the generator and a flat preview over grey
so the silhouette can be judged by eye.
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

_cache = {}


def whole_mask():
    if "m" not in _cache:
        img = Image.open(SRC).convert("RGB")
        a = np.asarray(img).astype(np.float32) / 255.0
        land = M.land_mask(a)
        lab, n = M.label(land)
        _cache["m"] = (img, land, lab, n)
    return _cache["m"]


def cut(entry, pad=0.10, long_side=1024):
    img, land, lab, n = whole_mask()
    x0, y0, x1, y1 = entry["bbox"]

    sub = lab[y0:y1 + 1, x0:x1 + 1]
    ids, counts = np.unique(sub[sub > 0], return_counts=True)
    if not len(ids):
        return None
    # an island may be a few blobs inside its box (a rock just off the shore);
    # anything at least a tenth of the main one belongs to it
    main = counts.max()
    keep = ids[counts >= main * 0.10]
    sel = np.isin(lab, keep)
    # a few stray pixels survive the feather and show up as grit beside the
    # island; anything under a half percent of the main mass is not land
    slab, sn = M.label(sel)
    if sn > 1:
        sizes = np.bincount(slab.ravel())
        sizes[0] = 0
        sel = np.isin(slab, np.flatnonzero(sizes >= sizes.max() * 0.005))

    ys, xs = np.nonzero(sel)
    bx0, bx1, by0, by1 = xs.min(), xs.max(), ys.min(), ys.max()

    px = int(round((bx1 - bx0 + 1) * pad))
    py = int(round((by1 - by0 + 1) * pad))
    cx0, cy0 = max(0, bx0 - px), max(0, by0 - py)
    cx1, cy1 = min(img.size[0] - 1, bx1 + px), min(img.size[1] - 1, by1 + py)

    rgb = np.asarray(img)[cy0:cy1 + 1, cx0:cx1 + 1].astype(np.float32)
    alpha = M.soft_alpha(sel[cy0:cy1 + 1, cx0:cx1 + 1], feather=1)

    # the sea tints the pixels just inside the coast; pulling the colour from one
    # step further in keeps a blue halo from being baked into the model's texture
    inner = M.erode(sel, 2)[cy0:cy1 + 1, cx0:cx1 + 1]
    edge = (alpha > 0.02) & ~inner
    if edge.any():
        src = np.asarray(img)[cy0:cy1 + 1, cx0:cx1 + 1].astype(np.float32)
        blur = src.copy()
        for _ in range(3):
            p = np.pad(blur, ((1, 1), (1, 1), (0, 0)), mode="edge")
            w = np.pad(inner.astype(np.float32), 1, mode="edge")[..., None]
            num = (p[1:-1, 1:-1] * w[1:-1, 1:-1] + p[:-2, 1:-1] * w[:-2, 1:-1]
                   + p[2:, 1:-1] * w[2:, 1:-1] + p[1:-1, :-2] * w[1:-1, :-2]
                   + p[1:-1, 2:] * w[1:-1, 2:])
            den = (w[1:-1, 1:-1] + w[:-2, 1:-1] + w[2:, 1:-1]
                   + w[1:-1, :-2] + w[1:-1, 2:])
            filled = np.where(den > 0, num / np.maximum(den, 1e-6), blur)
            blur = np.where(inner[..., None], src, filled)
            inner = inner | (den[..., 0] > 0)
        rgb = np.where(edge[..., None], blur, rgb)

    rgba = np.dstack([rgb, alpha * 255]).astype(np.uint8)
    out = Image.fromarray(rgba, "RGBA")

    w, hgt = out.size
    side = max(w, hgt)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(out, ((side - w) // 2, (side - hgt) // 2))
    canvas = canvas.resize((long_side, long_side), Image.LANCZOS)

    os.makedirs(OUT, exist_ok=True)
    name = entry.get("id") or "isle_%02d" % entry["index"]
    canvas.save(os.path.join(OUT, name + ".png"))
    flat = Image.new("RGB", canvas.size, (170, 174, 178))
    flat.paste(canvas, (0, 0), canvas)
    flat.save(os.path.join(OUT, name + "_preview.jpg"), quality=92)
    full = sel[by0:by1 + 1, bx0:bx1 + 1]
    last = np.nonzero(full[-1])[0]
    anchor_x = int(bx0 + (last.mean() if len(last) else full.shape[1] / 2))
    return {"id": name, "bbox": [int(bx0), int(by0), int(bx1), int(by1)],
            "anchor": [anchor_x, int(by1)], "area": int(sel.sum()),
            "coverage": round(float((alpha > 0.5).mean()), 3)}


def main():
    meta = json.load(open(os.path.join(HERE, "islands_raw.json"), encoding="utf-8"))
    extra = json.load(open(os.path.join(HERE, "islands_manual.json"), encoding="utf-8"))
    items = {str(e["index"]): e for e in meta["islands"]}
    for e in extra:
        items[str(e["index"])] = e
    wanted = sys.argv[1:] or list(items)
    done = []
    for key in wanted:
        e = items.get(str(key))
        if not e:
            print("no such island", key)
            continue
        r = cut(e)
        print(json.dumps(r))
        if r:
            done.append(r)

    # the cut gives the true outline, which is what the arrangement is measured from
    path = os.path.join(HERE, "islands_cut.json")
    have = {}
    if os.path.exists(path):
        have = {e["id"]: e for e in json.load(open(path, encoding="utf-8"))}
    for r in done:
        have[r["id"]] = r
    json.dump(sorted(have.values(), key=lambda e: -e["area"]),
              open(path, "w", encoding="utf-8"), indent=1)


if __name__ == "__main__":
    main()
