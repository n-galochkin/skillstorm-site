"""Check the exported heightmap against the mesh: raycast the island from above."""
import os, sys, json, zlib, struct
import numpy as np, bpy
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import island_lib as L
import build_islands as B   # reuses SPECS; it builds everything first

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "site", "assets", "islands")


def read_png16(path):
    d = open(path, 'rb').read()
    i, idat, w, h = 8, b'', 0, 0
    while i < len(d):
        ln = struct.unpack('>I', d[i:i + 4])[0]
        tag = d[i + 4:i + 8]
        pay = d[i + 8:i + 8 + ln]
        if tag == b'IHDR':
            w, h, bd, ct = struct.unpack('>IIBB', pay[:10])
            assert bd == 16 and ct == 0, (bd, ct)
        elif tag == b'IDAT':
            idat += pay
        i += 12 + ln
    raw = zlib.decompress(idat)
    stride = w * 2 + 1
    out = np.zeros((h, w), dtype=np.uint16)
    for y in range(h):
        assert raw[y * stride] == 0
        out[y] = np.frombuffer(raw[y * stride + 1:(y + 1) * stride], dtype='>u2')
    return out


man = json.load(open(os.path.join(OUT, "manifest.json"), encoding='utf-8'))
print("[verify] islands:", len(man['islands']))
worst = 0.0
for e in man['islands']:
    spec = next(s for s in B.SPECS if s['id'] == e['id'])
    theta = np.linspace(0, L.TAU, spec.get('M', 112), endpoint=False)
    obj, tris, rings = L.build_island(spec, e['id'] + "_v")
    png = read_png16(os.path.join(OUT, e['id'] + "_height.png"))
    size, zmin, zmax = e['size'], e['minHeight'], e['maxHeight']
    res = png.shape[0]
    rng = np.random.RandomState(1)
    errs = []
    for _ in range(240):
        ix, iy = rng.randint(0, res), rng.randint(0, res)
        x = -size / 2 + size * ix / (res - 1)
        gz = -size / 2 + size * iy / (res - 1)
        y = -gz
        hz = zmin + (png[iy, ix] / 65535.0) * (zmax - zmin)
        ok, loc, nrm, idx = obj.ray_cast((x, y, zmax + 20), (0, 0, -1))
        if ok:
            errs.append(abs(loc.z - hz))
    bad = float(np.percentile(errs, 97)) if errs else -1
    worst = max(worst, bad)
    print("[verify] {:<10} hits={:<4} p97 err={:.3f} m  max={:.3f} m".format(
        e['id'], len(errs), bad, float(np.max(errs)) if errs else -1))
    bpy.data.objects.remove(obj, do_unlink=True)
print("[verify] worst p97 error {:.3f} m".format(worst))
