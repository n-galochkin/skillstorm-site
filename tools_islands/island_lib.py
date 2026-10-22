"""Island mesh generator for the Skillstorm promo site.

The painting's islands are flat-topped plateaus whose shore band is a stack of
horizontal limestone strata: a narrow ledge, then a sheer riser, then the next
ledge. So the mesh is built as a stack of closed contour rings, from the sea
floor up to the plateau rim, and the grass top is capped on the innermost ring.

That buys sheer walls (a riser is a near-vertical quad strip), crisp horizontal
strata (a ledge is a horizontal strip, coloured per band), an organic outline
(the ring radius comes from a lobe field, so bays and headlands fall out of it)
and a very low triangle count.

Metres, origin at the island centre, z up in Blender -> y up in glTF.
y = 0 is the waterline; rings continue down to a reef shelf and a closed bottom.

Runs inside Blender 5.x. numpy only, no add-ons.
"""
import math
import os
import struct
import zlib

import numpy as np
import bpy
from mathutils import Vector

TAU = math.pi * 2.0


# --------------------------------------------------------------------- noise
def _hash2(ix, iy, seed):
    n = ix * np.int64(374761393) + iy * np.int64(668265263) + np.int64(seed) * np.int64(1442695041)
    n = (n ^ (n >> np.int64(13))) * np.int64(1274126177)
    n = n ^ (n >> np.int64(16))
    return (n & np.int64(0xFFFFFF)).astype(np.float64) / float(0x1000000)


def vnoise(x, y, seed):
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    ix = np.floor(x).astype(np.int64)
    iy = np.floor(y).astype(np.int64)
    fx, fy = x - ix, y - iy
    sx = fx * fx * (3.0 - 2.0 * fx)
    sy = fy * fy * (3.0 - 2.0 * fy)
    a = _hash2(ix, iy, seed)
    b = _hash2(ix + 1, iy, seed)
    c = _hash2(ix, iy + 1, seed)
    d = _hash2(ix + 1, iy + 1, seed)
    return (a * (1 - sx) + b * sx) * (1 - sy) + (c * (1 - sx) + d * sx) * sy


def fbm(x, y, seed, octaves=4, lac=2.03, gain=0.5):
    v = np.zeros_like(np.asarray(x, dtype=np.float64))
    amp, fx, fy = 0.5, x, y
    for i in range(octaves):
        v = v + amp * vnoise(fx, fy, seed + i * 101)
        fx, fy = fx * lac, fy * lac
        amp *= gain
    return v


def ring_noise(theta, seed, freq=2.6, octaves=3):
    """Noise that is continuous around the circle."""
    return fbm(np.cos(theta) * freq + 13.0, np.sin(theta) * freq + 7.0, seed, octaves)


def sstep(a, b, x):
    t = np.clip((np.asarray(x, dtype=np.float64) - a) / (b - a), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def smin(a, b, k):
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0.0, 1.0)
    return b * (1 - h) + a * h - k * h * (1 - h)


def smax(a, b, k):
    return -smin(-a, -b, k)


def norm01(a):
    lo, hi = float(np.min(a)), float(np.max(a))
    return (a - lo) / max(hi - lo, 1e-6)


# ------------------------------------------------------------------- palette
def srgb_hex(h):
    return np.array([((h >> 16) & 255) / 255.0, ((h >> 8) & 255) / 255.0, (h & 255) / 255.0])


def to_linear(c):
    c = np.asarray(c, dtype=np.float64)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


PAL = {
    'rock_light': srgb_hex(0xB4B9BE),
    'rock_mid':   srgb_hex(0xA9AFB5),
    'rock_dark':  srgb_hex(0x8D949C),
    'rock_deep':  srgb_hex(0x6E757E),
    'rock_warm':  srgb_hex(0xA8A49A),
    'grass':      srgb_hex(0x74B84A),
    'grass_dark': srgb_hex(0x56954A),
    'grass_dry':  srgb_hex(0x8CC456),
    'sand':       srgb_hex(0xEEDCAA),
    'sand_wet':   srgb_hex(0xDCC795),
    'seabed':     srgb_hex(0xCFC08A),
    'deep':       srgb_hex(0x4A7B85),
    'snow':       srgb_hex(0xF2F6FA),
    'basalt':     srgb_hex(0x6B6764),
    'basalt_dk':  srgb_hex(0x4B4847),
    'lava':       srgb_hex(0xFF7A1A),
    'scorch':     srgb_hex(0x8C4A2A),
}


# -------------------------------------------------------------------- outline
def _lobe_dist(X, Y, lobe):
    if isinstance(lobe, dict):
        kind = lobe.get('t', 'disc')
        if kind == 'ring':
            return np.abs(np.hypot(X - lobe['x'], Y - lobe['y']) - lobe['r']) - lobe['w']
        return np.hypot(X - lobe['x'], Y - lobe['y']) - lobe['r']
    cx, cy, r = lobe
    return np.hypot(X - cx, Y - cy) - r


def field(X, Y, o, seed):
    d = None
    k = o.get('k', 3.2)
    for lobe in o['lobes']:
        di = _lobe_dist(X, Y, lobe)
        d = di if d is None else smin(d, di, k)
    for bay in o.get('bays', []):
        d = smax(d, -_lobe_dist(X, Y, bay), o.get('bk', 2.2))
    a1, f1 = o.get('warp', (2.8, 0.055))
    if a1:
        d = d + a1 * (fbm(X * f1, Y * f1, seed + 3, 3) - 0.5) * 2.0
    a2, f2 = o.get('warp2', (0.8, 0.2))
    if a2:
        d = d + a2 * (fbm(X * f2, Y * f2, seed + 11, 2) - 0.5) * 2.0
    return d


def outline(spec, theta):
    """Radius of the waterline for every angle: the outermost zero of the field."""
    o = spec['outline']
    seed = spec['seed']
    rmax = spec['size'] * 0.46
    steps = 420
    rs = np.linspace(0.25, rmax, steps)
    TH, RR = np.meshgrid(theta, rs, indexing='ij')
    d = field(RR * np.cos(TH), RR * np.sin(TH), o, seed)
    inside = d < 0.0
    # outermost sample that is still inside, then refine the crossing
    idx = np.where(inside.any(axis=1),
                   (steps - 1) - np.argmax(inside[:, ::-1], axis=1), 0)
    r_hi = rs[np.minimum(idx + 1, steps - 1)]
    r_lo = rs[idx]
    d_lo = np.take_along_axis(d, idx[:, None], axis=1)[:, 0]
    d_hi = np.take_along_axis(d, np.minimum(idx + 1, steps - 1)[:, None], axis=1)[:, 0]
    t = np.where(np.abs(d_hi - d_lo) > 1e-9, -d_lo / (d_hi - d_lo), 0.0)
    return np.clip(r_lo + t * (r_hi - r_lo), 1.0, rmax)


# --------------------------------------------------------------------- rings
def _sector(theta, cfg):
    """A 0..1 mask around the circle: (amount, cover, seed) or (amount, amp, phase, harmonic)."""
    if cfg is None:
        return None
    if cfg.get('harmonic'):
        return np.clip(0.5 + 0.5 * np.cos(cfg['harmonic'] * (theta - math.radians(cfg.get('phase', 0)))), 0, 1) ** cfg.get('power', 1.0)
    n = norm01(ring_noise(theta, cfg.get('seed', 5), cfg.get('freq', 2.1), 2))
    cover = cfg.get('cover', 0.45)
    lo = 1.0 - cover - 0.08
    return sstep(lo, lo + 0.16, n)


def limit_slope(r, theta, k=2.4, passes=4):
    """Stop a ring from collapsing into a slit where a bay or a beach eats into it:
    the radius may not fall faster than ~k per angular step, measured around the circle."""
    M = len(theta)
    step = TAU / M
    out = r.copy()
    for _ in range(passes):
        for direction in (1, -1):
            idx = range(M) if direction > 0 else range(M - 1, -1, -1)
            for j in idx:
                p = (j - direction) % M
                lim = out[p] - k * max(out[p], 1.0) * step
                if out[j] < lim:
                    out[j] = lim
    return np.maximum(out, 0.45)


def smooth_ring(r, w=2):
    k = np.ones(1, dtype=np.float64)
    for _ in range(w):
        k = np.convolve(k, np.array([1.0, 2.0, 1.0]))
    k /= k.sum()
    h = (len(k) - 1) // 2
    pad = np.concatenate([r[-h:], r, r[:h]])
    return np.convolve(pad, k, mode='valid')


def ring_at(arr, theta_q, M):
    fi = np.mod(theta_q, TAU) / TAU * M
    i0 = np.floor(fi).astype(int) % M
    i1 = (i0 + 1) % M
    fr = fi - np.floor(fi)
    return arr[i0] * (1 - fr) + arr[i1] * fr


def build_rings(spec, theta):
    """Returns (radii[R,M], heights[R,M], tags[R-1], ring_meta) from sea floor up."""
    seed = spec['seed']
    M = len(theta)
    R0 = smooth_ring(limit_slope(outline(spec, theta), theta, spec.get('lip', 2.2)))
    radii, zs, tags = [], [], []
    meta = []

    sea = spec.get('sea', dict(floor=6.0, shelf_out=9.0, shelf_z=3.1, shallow_out=2.6, shallow_z=0.7))
    jitter = ring_noise(theta, seed + 200, 3.0, 2) - 0.5

    # --- below the waterline, outermost first
    radii.append(R0 + sea['shelf_out'] + sea['shelf_out'] * 0.30 * jitter * 2)
    zs.append(np.full(M, -sea['floor']))
    radii.append(R0 + sea['shelf_out'] * 0.55 + 1.4 * jitter)
    zs.append(np.full(M, -sea['shelf_z']))
    tags.append('floor')
    radii.append(R0 + sea['shallow_out'] + 0.9 * jitter)
    zs.append(np.full(M, -sea['shallow_z']))
    tags.append('shelf')
    radii.append(R0.copy())
    zs.append(np.zeros(M))
    tags.append('shallow')

    beach = spec.get('beach')
    sand = np.zeros(M)
    if beach:
        B = _sector(theta, beach) * beach.get('amount', 1.0)
        sand = B
        bw = 0.55 + 0.9 * norm01(ring_noise(theta, seed + 410, 2.8, 2))
        width = beach.get('base_w', 0.6) + B * beach.get('width', 12.0) * bw
        rise = beach.get('base_rise', 0.25) + B * beach.get('rise', 1.5) * (0.6 + 0.7 * bw)
        radii.append(radii[-1] - width)
        zs.append(zs[-1] + rise)
        tags.append('beach')

    # --- terraces
    terrw = np.zeros(M)
    nz = spec.get('ring_noise', (1.0, 0.25))
    ta, tp = spec.get('tilt', (0.0, 0.0))
    tilt = 1.0 + ta * np.cos(theta - math.radians(tp))
    for i, lv in enumerate(spec['levels']):
        extra = 0.0
        ins = lv.get('inset')
        if ins:
            extra = _sector(theta, ins) * ins.get('amount', 0.0)
        wob = (ring_noise(theta, seed + 300 + i * 17, lv.get('wob_freq', 2.2 + 0.55 * i), 2) - 0.5) * 2.0
        base_l = lv.get('ledge', 0.9) + extra
        ledge = base_l + nz[0] * wob * (0.35 + 0.65 * np.clip(np.asarray(base_l) / 2.0, 0, 1))
        radii.append(radii[-1] - np.maximum(ledge, 0.05))
        zs.append(zs[-1] + lv.get('ledge_rise', 0.0) + nz[1] * wob * 0.5)
        if lv.get('tag') == 'terrace':
            terrw = np.maximum(terrw, np.maximum(ledge, 0.05))
            radii[-1] = radii[-1]  # keep index readable
            mid = radii[-2] - np.maximum(ledge, 0.05) * 0.5
            radii.insert(len(radii) - 1, mid)
            zs.insert(len(zs) - 1, zs[-2] + (zs[-1] - zs[-2]) * 0.5)
            tags.append('terrace')
        tags.append(lv.get('tag', 'ledge'))
        rise = lv['rise'] * tilt * (1.0 + lv.get('rise_var', 0.42) * wob)
        if lv.get('rise_sector'):
            rise = rise * (0.25 + 0.75 * _sector(theta, lv['rise_sector']))
        radii.append(radii[-1] - lv.get('run', 0.35))
        zs.append(zs[-1] + rise)
        tags.append('riser')
        meta.append(i)

    radii = np.array(radii)
    zs = np.array(zs)
    lip = spec.get('lip', 2.2)
    for k in range(len(radii)):
        radii[k] = limit_slope(radii[k], theta, lip)
        if k >= 3:
            zs[k] = smooth_ring(zs[k], 1)
    # keep the stack strictly nested so the loft never folds through itself
    for k in range(1, len(radii)):
        if tags[k - 1] in ('ledge', 'riser', 'beach'):
            radii[k] = np.minimum(radii[k], radii[k - 1] - 0.05)
    radii = np.maximum(radii, 0.45)
    spec['_zmid'] = float(np.mean(zs[-1]))
    spec['_terrw'] = terrw
    return radii, zs, tags, sand


# ---------------------------------------------------------------------- mesh
class MeshBuf:
    def __init__(self):
        self.v = []
        self.f = []
        self.tag = []
        self.band = []

    def add_verts(self, pts):
        i0 = len(self.v)
        self.v.extend(pts)
        return i0

    def quad(self, a, b, c, d, tag, band):
        self.f.append((a, b, c))
        self.f.append((a, c, d))
        self.tag.extend([tag, tag])
        self.band.extend([band, band])

    def tri(self, a, b, c, tag, band):
        self.f.append((a, b, c))
        self.tag.append(tag)
        self.band.append(band)

    def arrays(self):
        return (np.array(self.v, dtype=np.float64),
                np.array(self.f, dtype=np.int64),
                np.array(self.tag),
                np.array(self.band, dtype=np.int64))


def loft(buf, theta, radii, zs, tags):
    M = len(theta)
    cos, sin = np.cos(theta), np.sin(theta)
    rows = []
    for k in range(len(radii)):
        pts = np.stack([radii[k] * cos, radii[k] * sin, zs[k]], axis=1)
        rows.append(buf.add_verts([tuple(p) for p in pts]))
    band = 0
    for k in range(len(radii) - 1):
        a0, b0 = rows[k], rows[k + 1]
        for j in range(M):
            jn = (j + 1) % M
            buf.quad(a0 + j, a0 + jn, b0 + jn, b0 + j, tags[k], band)
        if tags[k] == 'riser':
            band += 1
    return rows[-1], rows[0]


def cap_height(spec, X, Y, r_top_at, z_top_at, rr, z_mid=None):
    """Plateau surface: the rim height blended into a rolling interior."""
    c = spec.get('cap', {})
    ra, rf = c.get('roll', (0.9, 0.085))
    roll = (fbm(X * rf, Y * rf, spec['seed'] + 13, 3) - 0.5) * 2.0 * ra
    flat = c.get('flat_center')
    if flat:
        roll = roll * sstep(flat[0], flat[0] + flat[1], np.hypot(X, Y))
    w = sstep(0.0, 1.0, np.clip(1.0 - rr / np.maximum(r_top_at, 1e-6), 0, 1) / max(c.get('blend', 0.35), 1e-3))
    if z_mid is None:
        z_mid = spec.get('_zmid', float(np.mean(z_top_at)))
    base = z_top_at + (z_mid + c.get('dome', 0.0) - z_top_at) * w
    z = base + roll * w
    cr = c.get('crater')
    if cr:
        cx, cy, crr, depth = cr
        z = z - depth * (1.0 - sstep(crr * 0.3, crr, np.hypot(X - cx, Y - cy)))
    return z


def build_cap(buf, spec, theta, r_top, z_top, row_top):
    """Plateau top: a constrained Delaunay triangulation of the rim polygon with a
    jittered interior point set, so the grass reads as irregular chunky facets
    instead of a fan converging on the centre."""
    from mathutils.geometry import delaunay_2d_cdt
    from mathutils import Vector as V2

    c = spec.get('cap', {})
    M = len(theta)
    cos, sin = np.cos(theta), np.sin(theta)
    bx, by = r_top * cos, r_top * sin

    spacing = c.get('spacing', 2.4)
    rng = np.random.RandomState((spec['seed'] * 7919) & 0x7FFFFFFF)
    rmax = float(r_top.max())
    n = int(math.ceil(rmax * 2 / spacing)) + 2
    pts = []
    for iy in range(-n, n + 1):
        for ix in range(-n, n + 1):
            px = (ix + (0.5 if iy % 2 else 0.0)) * spacing
            py = iy * spacing * 0.866
            px += (rng.rand() - 0.5) * spacing * 0.45
            py += (rng.rand() - 0.5) * spacing * 0.45
            rr = math.hypot(px, py)
            if rr < 1e-6:
                continue
            lim = float(ring_at(r_top, np.array([math.atan2(py, px)]), M)[0])
            if rr < lim - spacing * 0.62:
                pts.append((px, py))

    coords = [V2((bx[j], by[j])) for j in range(M)] + [V2(p) for p in pts]
    edges = [(j, (j + 1) % M) for j in range(M)]
    try:
        out_v, out_e, out_f, orig_v, orig_e, orig_f = delaunay_2d_cdt(coords, edges, [], 1, 1e-5)
    except Exception:
        out_v, out_e, out_f, orig_v, orig_e, orig_f = delaunay_2d_cdt(coords, edges, [], 1, 1e-5, True)

    ov = np.array([(v.x, v.y) for v in out_v])
    ang = np.arctan2(ov[:, 1], ov[:, 0])
    rr = np.hypot(ov[:, 0], ov[:, 1])
    rt = ring_at(r_top, ang, M)
    zt = ring_at(z_top, ang, M)
    z = cap_height(spec, ov[:, 0], ov[:, 1], rt, zt, rr)

    # vertices that came from the rim keep the ring's exact height: no crack
    idx_map = {}
    for i, srcs in enumerate(orig_v):
        for s in srcs:
            if s < M:
                idx_map[i] = s
                break
    base = buf.add_verts([(ov[i, 0], ov[i, 1], z[i]) for i in range(len(ov))])
    for i, s in idx_map.items():
        buf.v[base + i] = (float(bx[s]), float(by[s]), float(z_top[s]))

    rim_frac = c.get('rim_frac', 0.945)
    for f in out_f:
        if len(f) < 3:
            continue
        a, b, cc = f[0], f[1], f[2]
        p = np.array([buf.v[base + a], buf.v[base + b], buf.v[base + cc]])
        nz = np.cross(p[1] - p[0], p[2] - p[0])[2]
        tri = (a, b, cc) if nz >= 0 else (a, cc, b)
        cx, cy = p[:, 0].mean(), p[:, 1].mean()
        crr = math.hypot(cx, cy)
        clim = float(ring_at(r_top, np.array([math.atan2(cy, cx)]), M)[0])
        tag = 'rim' if crr > clim * rim_frac else 'cap'
        buf.tri(base + tri[0], base + tri[1], base + tri[2], tag, 0)


def build_bottom(buf, theta, radii, zs, row_bottom):
    M = len(theta)
    zb = float(np.min(zs[0])) - 0.5
    centre = buf.add_verts([(0.0, 0.0, zb)])
    for j in range(M):
        jn = (j + 1) % M
        buf.tri(row_bottom + jn, row_bottom + j, centre, 'floor', 0)


def add_spire(buf, cx, cy, r, h, seed, sides=7, levels=3, base_z=-4.0, tag='stack'):
    """A chunky rock spire: a few stacked irregular rings tapering to a tip."""
    rng = np.random.RandomState(seed & 0x7FFFFFFF)
    ang = np.linspace(0, TAU, sides, endpoint=False) + rng.rand() * TAU
    rows = []
    zsv = []
    for i in range(levels + 1):
        f = i / float(levels)
        rr = r * (1.0 - f) ** 0.75 * (0.75 + 0.5 * rng.rand(sides))
        z = base_z + (h - base_z) * f ** 1.05
        if i == levels:
            rr = rr * 0.25
        rows.append(buf.add_verts([(cx + rr[j] * math.cos(ang[j]), cy + rr[j] * math.sin(ang[j]), z)
                                   for j in range(sides)]))
        zsv.append(z)
    for i in range(levels):
        a0, b0 = rows[i], rows[i + 1]
        for j in range(sides):
            jn = (j + 1) % sides
            buf.quad(a0 + j, a0 + jn, b0 + jn, b0 + j, tag, 0)
    tip = buf.add_verts([(cx + rng.randn() * r * 0.06, cy + rng.randn() * r * 0.06, h)])
    last = rows[-1]
    for j in range(sides):
        jn = (j + 1) % sides
        buf.tri(last + j, last + jn, tip, tag, 0)


def add_arch(buf, cfg):
    """A natural rock arch: a chunky tapered span, thickest at the feet, feet sunk
    below the waterline so it reads as part of the shore."""
    cx, cy = cfg['x'], cfg['y']
    span, rise = cfg['span'], cfg['rise']
    w0, w1 = cfg.get('w_foot', 5.0), cfg.get('w_top', 2.8)
    t0, t1 = cfg.get('t_foot', 4.2), cfg.get('t_top', 1.8)
    rot = math.radians(cfg.get('rot', 0.0))
    n = cfg.get('segs', 8)
    base = cfg.get('base', -3.4)
    rng = np.random.RandomState(cfg.get('seed', 7))
    rows = []
    for i in range(n + 1):
        t = i / float(n)
        a = math.pi * t
        x = -math.cos(a) * span * 0.5
        taper = abs(math.cos(a)) ** 0.8
        w = (w1 + (w0 - w1) * taper) * (0.88 + 0.24 * rng.rand())
        th = (t1 + (t0 - t1) * taper) * (0.88 + 0.24 * rng.rand())
        if i == 0 or i == n:
            zl, zh = base, rise * 0.34 + th * 0.5
        else:
            crown = math.sin(a) * rise
            zl = max(crown - th * 0.45, 0.45)
            zh = crown + th * 0.55
        pts = []
        for (px, py, pz) in [(x, -w * 0.5, zl), (x, w * 0.5, zl), (x, w * 0.5, zh), (x, -w * 0.5, zh)]:
            px += (rng.rand() - 0.5) * span * 0.04
            py += (rng.rand() - 0.5) * w * 0.20
            rx = px * math.cos(rot) - py * math.sin(rot)
            ry = px * math.sin(rot) + py * math.cos(rot)
            pts.append((cx + rx, cy + ry, pz))
        rows.append(buf.add_verts(pts))
    for i in range(n):
        a0, b0 = rows[i], rows[i + 1]
        for j in range(4):
            jn = (j + 1) % 4
            buf.quad(a0 + j, a0 + jn, b0 + jn, b0 + j, 'arch', 0)
    buf.quad(rows[0] + 0, rows[0] + 1, rows[0] + 2, rows[0] + 3, 'arch', 0)
    buf.quad(rows[-1] + 3, rows[-1] + 2, rows[-1] + 1, rows[-1] + 0, 'arch', 0)


# ----------------------------------------------------------------- colouring
def face_colours(spec, cent, nrm, tags, bands, sand_at):
    x, y, z = cent[:, 0], cent[:, 1], cent[:, 2]
    n = len(z)
    seed = spec['seed']
    jit = fbm(x * 0.37, y * 0.37, seed + 5, 2)
    patch = fbm(x * 0.11, y * 0.11, seed + 9, 3)
    grain = (0.93 + 0.14 * jit)[:, None]

    rock = [spec.get('rock_a', PAL['rock_mid']),
            spec.get('rock_b', PAL['rock_dark']),
            spec.get('rock_c', PAL['rock_light']),
            spec.get('rock_d', PAL['rock_warm']),
            spec.get('rock_e', PAL['rock_deep'] * 0.8 + PAL['rock_warm'] * 0.2)]
    order = [0, 2, 0, 1, 0, 0, 3, 0, 2, 0, 1, 0, 0, 4]
    strata = np.array([rock[order[int(b) % len(order)] % len(rock)] for b in bands]) * grain
    strata = strata * (1.0 - 0.16 * sstep(3.4, 0.2, z))[:, None]

    grass_a = np.asarray(spec.get('grass_a', PAL['grass']))
    grass_b = np.asarray(spec.get('grass_b', PAL['grass_dark']))
    grass = np.where((patch > 0.5)[:, None], grass_a, grass_b)
    grass = np.where((patch > 0.82)[:, None], np.asarray(spec.get('grass_c', PAL['grass_dry'])), grass)
    grass = grass * (0.955 + 0.09 * jit)[:, None]

    sand = PAL['sand'] * (0.95 + 0.1 * jit)[:, None]
    col = np.tile(PAL['rock_mid'], (n, 1))

    depth = np.clip(-z, 0, None)
    deep_mix = sstep(0.2, 4.0, depth)[:, None]
    seabed = PAL['seabed'] * (1 - deep_mix) + PAL['deep'] * deep_mix

    is_floor = (tags == 'floor') | (tags == 'shelf')
    is_shallow = tags == 'shallow'
    is_beach = tags == 'beach'
    is_ledge = (tags == 'ledge') | (tags == 'terrace')
    is_terrace = tags == 'terrace'
    is_riser = tags == 'riser'
    is_cap = tags == 'cap'
    is_rim = tags == 'rim'
    is_rock = (tags == 'stack') | (tags == 'arch')

    col = np.where(is_floor[:, None], seabed, col)
    col = np.where(is_shallow[:, None],
                   PAL['sand_wet'] * (1 - sstep(0.0, 1.6, depth))[:, None] + seabed * sstep(0.0, 1.6, depth)[:, None],
                   col)

    sandy = sand_at[:, None]
    beach_col = sand * sandy + strata * (1 - sandy)
    beach_col = np.where((z < 0.12)[:, None], PAL['sand_wet'] * sandy + strata * (1 - sandy), beach_col)
    col = np.where(is_beach[:, None], beach_col, col)

    # ledges: sand where a beach reaches them, pale limestone shelf otherwise
    low = sstep(spec.get('beach_top', 1.6) + 0.5, spec.get('beach_top', 1.6) - 0.6, z)[:, None]
    ledge_col = strata * 0.86
    lwet = sstep(2.2, -0.2, z)[:, None]
    ledge_col = ledge_col * (1 - lwet * 0.4) + PAL['rock_deep'] * (lwet * 0.4)
    ledge_col = ledge_col * (1 - sandy * low) + sand * (sandy * low)
    col = np.where(is_ledge[:, None], ledge_col, col)

    riser_col = strata.copy()
    wet = sstep(0.9, -0.5, z)[:, None]
    riser_col = riser_col * (1 - wet * 0.40) + PAL['rock_deep'] * (wet * 0.40)
    surf = (sstep(-0.45, -0.05, z) * sstep(0.5, 0.1, z))[:, None]
    riser_col = riser_col * (1 - surf * 0.55) + np.array([0.90, 0.95, 0.96]) * (surf * 0.55)
    col = np.where(is_riser[:, None], riser_col, col)

    # a wide terrace high above the water carries grass, like the town shelves
    if np.any(is_terrace):
        g = (is_terrace & (z > spec.get('terrace_grass', 2.2)) & (sand_at < 0.35)
             & (spec.get('_terrw_at', np.zeros(n)) > 2.0))[:, None]
        col = np.where(g, grass * 0.72 + np.asarray(rock[2]) * grain * 0.28, col)
    col = np.where(is_rock[:, None],
                   np.array([rock[int(max(0, min(len(rock) - 1, math.floor(zz / max(spec.get('band_h', 1.8), 0.3)) % len(rock))))] for zz in z]) * grain,
                   col)

    col = np.where(is_cap[:, None], grass, col)
    rim_col = grass * 0.52 + np.asarray(rock[2]) * grain * 0.48
    col = np.where(is_rim[:, None], rim_col, col)

    # a cap that sits low is a sandy flat or a lagoon floor, not grass
    flat_top = is_cap | is_rim
    col = np.where((flat_top & (z < spec.get('beach_top', 1.6)))[:, None], sand, col)
    col = np.where((flat_top & (z < 0.15))[:, None],
                   PAL['sand_wet'] * (1 - deep_mix) + PAL['deep'] * deep_mix, col)

    # grass creeping onto the top ledges
    if spec.get('grass_ledges', False):
        hi = sstep(spec.get('grass_from', 4.0), spec.get('grass_from', 4.0) + 3.0, z)
        mossy = (is_ledge & (patch > 0.42) & (sand_at < 0.25))[:, None] * hi[:, None]
        col = col * (1 - mossy * 0.8) + grass * (mossy * 0.8)

    snow = spec.get('snowline')
    if snow is not None:
        flat = np.clip(nrm[:, 2], 0, 1)
        sn = sstep(snow, snow + 1.4, z) * (0.25 + 0.75 * sstep(0.3, 0.8, flat))
        sn = np.where(is_floor | is_shallow, 0.0, sn)
        col = col * (1 - sn)[:, None] + PAL['snow'] * sn[:, None]

    lava = spec.get('lava')
    if lava is not None:
        cx, cy, rr, hz = lava
        r = np.hypot(x - cx, y - cy)
        hot = (r < rr) & (z < hz) & (is_cap | is_rim)
        warm = (r < rr * 1.7) & (z < hz + 1.6) & (~hot) & (is_cap | is_rim)
        col = np.where(warm[:, None], PAL['scorch'], col)
        col = np.where(hot[:, None], PAL['lava'], col)

    return np.clip(col, 0, 1)


# ----------------------------------------------------------------- assembly
def build_island(spec, name):
    M = spec.get('M', 112)
    theta = np.linspace(0, TAU, M, endpoint=False)
    radii, zs, tags, sand = build_rings(spec, theta)

    buf = MeshBuf()
    row_top, row_bottom = loft(buf, theta, radii, zs, tags)
    build_cap(buf, spec, theta, radii[-1], zs[-1], row_top)
    build_bottom(buf, theta, radii, zs, row_bottom)

    for st in spec.get('stacks', []):
        add_spire(buf, st[0], st[1], st[2], st[3], spec['seed'] + int(abs(st[0]) * 7 + abs(st[1]) * 13),
                  sides=st[4] if len(st) > 4 else 7, levels=3,
                  base_z=-spec.get('sea', {}).get('shallow_z', 0.7) - 2.4)
    if spec.get('arch'):
        cfg = dict(spec['arch'])
        if 'angle' in cfg:
            a = math.radians(cfg['angle'])
            r_shore = float(ring_at(radii[3], np.array([a]), M)[0])
            rr = r_shore + cfg.get('offset', 0.0)
            cfg['x'], cfg['y'] = rr * math.cos(a), rr * math.sin(a)
            cfg['rot'] = cfg['angle'] + cfg.get('turn', 90)
        add_arch(buf, cfg)

    V, F, TAGS, BANDS = buf.arrays()
    p0, p1, p2 = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    nrm = np.cross(p1 - p0, p2 - p0)
    area = np.linalg.norm(nrm, axis=1)
    keep = area > 1e-5
    F, TAGS, BANDS = F[keep], TAGS[keep], BANDS[keep]
    p0, p1, p2 = p0[keep], p1[keep], p2[keep]
    nrm = nrm[keep] / np.maximum(area[keep][:, None], 1e-9)
    cent = (p0 + p1 + p2) / 3.0

    # how sandy the shore is at each face's angle
    ang = np.mod(np.arctan2(cent[:, 1], cent[:, 0]), TAU)
    fi = ang / TAU * M
    i0 = np.floor(fi).astype(int) % M
    i1 = (i0 + 1) % M
    fr = fi - np.floor(fi)
    sand_at = sand[i0] * (1 - fr) + sand[i1] * fr

    tw = spec.get('_terrw')
    spec['_terrw_at'] = (tw[i0] * (1 - fr) + tw[i1] * fr) if tw is not None else np.zeros(len(F))
    cols = face_colours(spec, cent, nrm, TAGS, BANDS, sand_at)

    nt = len(F)
    out_v = np.empty((nt, 3, 3))
    out_v[:, 0], out_v[:, 1], out_v[:, 2] = p0, p1, p2
    out_v = out_v.reshape(-1, 3)
    out_t = np.arange(nt * 3).reshape(nt, 3)
    out_c = np.repeat(cols, 3, axis=0)

    me = bpy.data.meshes.new(name)
    me.from_pydata(out_v.tolist(), [], out_t.tolist())
    me.validate()
    me.update()
    me.polygons.foreach_set("use_smooth", np.zeros(nt, dtype=np.int8))
    attr = me.color_attributes.new(name="Col", type='FLOAT_COLOR', domain='POINT')
    rgba = np.ones((nt * 3, 4))
    rgba[:, :3] = to_linear(out_c)
    attr.data.foreach_set("color", rgba.ravel())

    obj = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(island_material())
    return obj, nt, (theta, radii, zs, tags)


def island_material():
    mat = bpy.data.materials.get("IslandVC")
    if mat:
        return mat
    mat = bpy.data.materials.new("IslandVC")
    mat.use_nodes = True
    mat.use_backface_culling = True
    nt = mat.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    bsdf.inputs["Roughness"].default_value = 1.0
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.15
    ca = nt.nodes.new("ShaderNodeVertexColor")
    ca.layer_name = "Col"
    ca.location = (-300, 200)
    nt.links.new(ca.outputs["Color"], bsdf.inputs["Base Color"])
    return mat


# ------------------------------------------------------------ height lookup
def sample_height(spec, rings, X, Y):
    theta, radii, zs, tags = rings
    M = len(theta)
    shp = X.shape
    x, y = X.ravel(), Y.ravel()
    ang = np.mod(np.arctan2(y, x), TAU)
    r = np.hypot(x, y)
    fi = ang / TAU * M
    i0 = np.floor(fi).astype(int) % M
    i1 = (i0 + 1) % M
    fr = (fi - np.floor(fi))[None, :]
    rk = radii[:, i0] * (1 - fr) + radii[:, i1] * fr      # (R, P) decreasing in k
    zk = zs[:, i0] * (1 - fr) + zs[:, i1] * fr
    R = rk.shape[0]

    inside = rk >= r[None, :]
    count = inside.sum(axis=0)
    k = np.clip(count - 1, 0, R - 2)
    rk0 = np.take_along_axis(rk, k[None, :], 0)[0]
    rk1 = np.take_along_axis(rk, (k + 1)[None, :], 0)[0]
    zk0 = np.take_along_axis(zk, k[None, :], 0)[0]
    zk1 = np.take_along_axis(zk, (k + 1)[None, :], 0)[0]
    den = np.maximum(rk0 - rk1, 1e-6)
    f = np.clip((rk0 - r) / den, 0, 1)
    z = zk0 + f * (zk1 - zk0)

    # outside the outermost ring -> sea floor; inside the innermost -> the cap
    z = np.where(count == 0, zs[0][i0], z)
    r_top = radii[-1][i0] * (1 - fr[0]) + radii[-1][i1] * fr[0]
    z_top = zs[-1][i0] * (1 - fr[0]) + zs[-1][i1] * fr[0]
    cap_z = cap_height(spec, x, y, r_top, z_top, r)
    z = np.where(count >= R, cap_z, z)

    for st in spec.get('stacks', []):
        sx, sy, sr, sh = st[0], st[1], st[2], st[3]
        rr = np.hypot(x - sx, y - sy)
        z = np.maximum(z, sh * (1.0 - rr / sr) * 0.9)
    return z.reshape(shp)


def write_png16(path, arr01):
    h, w = arr01.shape
    data = (np.clip(arr01, 0, 1) * 65535.0 + 0.5).astype('>u2')
    raw = bytearray()
    for row in data:
        raw.append(0)
        raw.extend(row.tobytes())

    def chunk(tag, payload):
        return (struct.pack('>I', len(payload)) + tag + payload
                + struct.pack('>I', zlib.crc32(tag + payload) & 0xFFFFFFFF))

    png = b'\x89PNG\r\n\x1a\n'
    png += chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 16, 0, 0, 0, 0))
    png += chunk(b'IDAT', zlib.compress(bytes(raw), 9))
    png += chunk(b'IEND', b'')
    with open(path, 'wb') as f:
        f.write(png)


def write_height(spec, rings, obj, out_dir, res=256):
    """Rasterise the real mesh, not the field: a ray straight down per texel, so the
    lookup matches the geometry the site actually draws, sea stacks included.

    Image convention (glTF space, Y up): column 0 is x = -size/2, row 0 is z = -size/2,
    x = -size/2 + col/(res-1)*size, z = -size/2 + row/(res-1)*size.
    """
    from mathutils.bvhtree import BVHTree
    half = spec['size'] * 0.5
    bvh = BVHTree.FromObject(obj, bpy.context.evaluated_depsgraph_get())
    ax = np.linspace(-half, half, res)
    # analytic fall-back for texels that miss the mesh entirely (open sea)
    GX, GZ = np.meshgrid(ax, ax, indexing='xy')
    Z = sample_height(spec, rings, GX, -GZ)
    top = float(max(zs_max(rings), 1.0)) + 5.0
    down = Vector((0, 0, -1))
    for r in range(res):
        by = -ax[r]                      # glTF z -> blender y
        for c in range(res):
            hit = bvh.ray_cast(Vector((ax[c], by, top)), down)
            if hit[0] is not None:
                Z[r, c] = hit[0].z
    zmin, zmax = float(Z.min()), float(Z.max())
    write_png16(os.path.join(out_dir, spec['id'] + "_height.png"),
                (Z - zmin) / max(zmax - zmin, 1e-6))
    return zmin, zmax, Z


def zs_max(rings):
    return float(np.max(rings[2]))


def export_glb(obj, path):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.export_scene.gltf(
        filepath=path, export_format='GLB', use_selection=True, export_apply=True,
        export_yup=True, export_normals=True, export_tangents=False,
        export_materials='EXPORT', export_vertex_color='ACTIVE',
        export_all_vertex_colors=False, export_attributes=False,
        export_texcoords=False, export_cameras=False, export_lights=False,
        export_animations=False,
    )


# -------------------------------------------------------------------- render
def setup_scene(samples=40, res=(1000, 620)):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 3
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.view_settings.view_transform = 'Standard'
    sc.view_settings.look = 'None'

    # Exposure is set so a face renders at about its own albedo: that way the preview
    # shows the vertex colours, not a guess at how three.js will light them. The sky is
    # bright to the camera but dim as a light, via Light Path.
    world = sc.world or bpy.data.worlds.new("W")
    sc.world = world
    world.use_nodes = True
    wt = world.node_tree
    for n in list(wt.nodes):
        if n.type != 'OUTPUT_WORLD':
            wt.nodes.remove(n)
    out = wt.nodes['World Output']
    vis = wt.nodes.new('ShaderNodeBackground')
    vis.inputs[0].default_value = (0.42, 0.67, 0.94, 1.0)
    vis.inputs[1].default_value = 1.0
    lit = wt.nodes.new('ShaderNodeBackground')
    lit.inputs[0].default_value = (0.52, 0.70, 0.95, 1.0)
    lit.inputs[1].default_value = 0.34
    mix = wt.nodes.new('ShaderNodeMixShader')
    lp = wt.nodes.new('ShaderNodeLightPath')
    wt.links.new(lp.outputs['Is Camera Ray'], mix.inputs[0])
    wt.links.new(lit.outputs[0], mix.inputs[1])
    wt.links.new(vis.outputs[0], mix.inputs[2])
    wt.links.new(mix.outputs[0], out.inputs['Surface'])

    if "Sun" not in bpy.data.objects:
        sd = bpy.data.lights.new("Sun", 'SUN')
        sd.energy = 2.9
        sd.angle = math.radians(4.0)
        sun = bpy.data.objects.new("Sun", sd)
        bpy.context.scene.collection.objects.link(sun)
        sun.rotation_euler = (math.radians(44), 0, math.radians(142))

    if "Sea" not in bpy.data.objects:
        me = bpy.data.meshes.new("SeaMesh")
        s = 900.0
        me.from_pydata([(-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0)],
                       [], [(0, 1, 2, 3)])
        me.validate()
        me.update(calc_edges=True)
        sea = bpy.data.objects.new("Sea", me)
        bpy.context.scene.collection.objects.link(sea)
        print("[isl] sea polys:", len(me.polygons), "objects:",
              [o.name for o in bpy.context.scene.objects])
        m = bpy.data.materials.new("SeaMat")
        m.use_nodes = True
        b = m.node_tree.nodes.get("Principled BSDF")
        b.inputs["Base Color"].default_value = (0.045, 0.30, 0.52, 1)
        b.inputs["Roughness"].default_value = 0.22
        sea.data.materials.append(m)


def render_island(obj, path, radius, top=0.0, elev_deg=35.0, azim_deg=38.0, dist_mul=3.5, lens=42):
    cam_data = bpy.data.cameras.get("Cam") or bpy.data.cameras.new("Cam")
    cam_data.lens = lens
    cam = bpy.data.objects.get("CamObj")
    if cam is None:
        cam = bpy.data.objects.new("CamObj", cam_data)
        bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    d = max(radius, top * 0.95) * dist_mul
    e, a = math.radians(elev_deg), math.radians(azim_deg)
    target = Vector((0, 0, max(radius * 0.12, top * 0.42)))
    cam.location = target + Vector((math.cos(e) * math.cos(a) * d,
                                    math.cos(e) * math.sin(a) * d,
                                    math.sin(e) * d))
    cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
