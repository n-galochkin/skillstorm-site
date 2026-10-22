"""Separate land from sea in the start-screen painting.

Colour alone cannot do it: sunlit grass and pale rock are as bright and as
colourless as foam, so a per-pixel test eats holes out of the middle of an island.
The sea, though, is one connected body that touches the edge of the frame — so it
is found by flooding inward from the border, and everything the flood never
reaches is land, whatever colour it happens to be.
"""
import numpy as np


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
    return h * 60.0, np.where(mx > 1e-6, d / np.maximum(mx, 1e-6), 0.0), mx


def dilate(mask, r):
    out = mask
    for _ in range(r):
        p = np.pad(out, 1, constant_values=False)
        out = (p[1:-1, 1:-1] | p[:-2, 1:-1] | p[2:, 1:-1] | p[1:-1, :-2] | p[1:-1, 2:])
    return out


def erode(mask, r):
    return ~dilate(~mask, r)


def flood_from_border(passable):
    """Everything reachable from the frame edge through `passable`."""
    h, w = passable.shape
    seen = np.zeros_like(passable)
    seen[0] |= passable[0]
    seen[-1] |= passable[-1]
    seen[:, 0] |= passable[:, 0]
    seen[:, -1] |= passable[:, -1]
    # grow the wavefront until it stops changing; a few hundred passes at most
    while True:
        p = np.pad(seen, 1, constant_values=False)
        grown = (p[1:-1, 1:-1] | p[:-2, 1:-1] | p[2:, 1:-1] | p[1:-1, :-2] | p[1:-1, 2:])
        grown &= passable
        if grown.sum() == seen.sum():
            return seen
        seen = grown


def label(mask):
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


def land_mask(rgb01, grow=3, despeckle=400):
    """rgb01: float image in 0..1. Returns a boolean land mask."""
    h, s, v = to_hsv(rgb01)

    # anything that could be sea: open blue water, turquoise shallows, foam, haze
    sea_like = ((h > 168) & (h < 232) & (s > 0.22)) | ((v > 0.80) & (s < 0.28))
    sea = flood_from_border(sea_like)

    land = ~sea
    land = erode(land, 1)                 # let go of the single-pixel fringe
    land = dilate(land, grow + 1)         # take the beach and the foam line back
    land = erode(land, 1)

    lab, n = label(land)
    if n:
        sizes = np.bincount(lab.ravel())
        keep = np.flatnonzero(sizes >= despeckle)
        land = np.isin(lab, keep[keep > 0])

    # Widening the coast seals the narrow channels that feed inner pools, which
    # leaves those pools walled in by land. A hole in a island is a hole in the
    # model, so anything the sea can no longer reach becomes island.
    land |= ~flood_from_border(~land)
    return land


def soft_alpha(mask, feather=1):
    """A binary mask has stair-stepped edges; one box blur takes the stairs off."""
    a = mask.astype(np.float32)
    for _ in range(feather):
        p = np.pad(a, 1, mode="edge")
        a = (p[1:-1, 1:-1] * 4 + p[:-2, 1:-1] + p[2:, 1:-1]
             + p[1:-1, :-2] + p[1:-1, 2:]) / 8.0
    return np.clip(a, 0, 1)
