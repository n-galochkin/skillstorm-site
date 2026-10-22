"""Low-poly prop builder for the Skillstorm promo site.

Everything is built as raw vertices + faces with a colour per face, then written out
as a single flat-shaded mesh with a COLOR_0 attribute and one material. That is what
site/props.js wants: one geometry, one material, instanceable.

Axes while modelling: Blender Z up, the object FACES -Y.
The glTF exporter turns that into Y up, facing +Z, which is the site's convention.
Pivot: put the base of the object at z = 0 (boats: the waterline at z = 0).
"""
import bpy
import bmesh
import math
import os
from mathutils import Vector, Matrix

TAU = math.pi * 2

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(ROOT, "..", "site", "assets", "props"))


def _s2l(c):
    """sRGB 0..1 -> linear. The palette is given as sRGB hex, but a glTF COLOR_0
    attribute is linear (and THREE.Color(hex) converts the same way), so the
    conversion has to happen here or every prop renders too dark."""
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hx(h):
    return tuple(_s2l(((h >> s) & 255) / 255.0) for s in (16, 8, 0))


def mix(a, b, t):
    return tuple(a[i] * (1 - t) + b[i] * t for i in range(3))


def shade(c, f):
    """Darken (f<1) or lighten (f>1) a colour, staying in gamut."""
    if f <= 1:
        return tuple(max(0.0, min(1.0, c[i] * f)) for i in range(3))
    return tuple(max(0.0, min(1.0, c[i] + (1 - c[i]) * (f - 1))) for i in range(3))


# Palette from the brief, plus the shades each material needs to read as a solid.
P = {
    "wall": hx(0xF0ECE2),
    "wallShade": hx(0xDBD4C6),
    "wallWarm": hx(0xE8DFCB),
    "roof": hx(0xB8452F),
    "roofDark": hx(0x8E3324),
    "roofLight": hx(0xC9573D),
    "stone": hx(0xA7AEB6),
    "stoneDark": hx(0x80878F),
    "stoneLight": hx(0xBFC5CB),
    "conifer": hx(0x2F6F3C),
    "coniferDark": hx(0x255A30),
    "green": hx(0x4E9F4A),
    "greenDark": hx(0x3C7C3A),
    "wood": hx(0x6D4C2F),
    "woodDark": hx(0x553A24),
    "woodLight": hx(0x8A6239),
    "woodPale": hx(0xA67C45),
    "sail": hx(0xF2E9D6),
    "sailShade": hx(0xDCD0B8),
    "sand": hx(0xEEDCAA),
    "red": hx(0xC0392B),
    "dark": hx(0x2A2420),
    "glass": hx(0x3C5A66),
    "glassLit": hx(0xF6D98A),
    "rope": hx(0xBFA272),
    "thatch": hx(0xC9A05A),
    "thatchDark": hx(0xA8803F),
    "iron": hx(0x4A4F55),
}


class Build:
    """Accumulates coloured faces under a transform stack."""

    def __init__(self):
        self.v = []
        self.f = []
        self.c = []
        self.stack = [Matrix.Identity(4)]

    # ---- transform stack -------------------------------------------------
    @property
    def m(self):
        return self.stack[-1]

    def push(self, mat):
        self.stack.append(self.m @ mat)
        return self

    def pop(self):
        self.stack.pop()
        return self

    def push_trs(self, loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1)):
        m = Matrix.Translation(Vector(loc))
        if rot[2]:
            m = m @ Matrix.Rotation(rot[2], 4, "Z")
        if rot[1]:
            m = m @ Matrix.Rotation(rot[1], 4, "Y")
        if rot[0]:
            m = m @ Matrix.Rotation(rot[0], 4, "X")
        if scale != (1, 1, 1):
            m = m @ Matrix.Diagonal(Vector(scale).to_4d())
        return self.push(m)

    # ---- raw ------------------------------------------------------------
    def _pt(self, p):
        w = self.m @ Vector(p)
        self.v.append((w.x, w.y, w.z))
        return len(self.v) - 1

    def face(self, pts, col):
        idx = [self._pt(p) for p in pts]
        self.f.append(idx)
        self.c.append(col)

    def face2(self, pts, col, back=None):
        """Double sided (sails, flags, thin planes).

        `back` lets the reverse side carry a lighter albedo. Cloth is thin and
        lets light through; a flat-shaded double face does not, so a backlit sail
        goes dead grey. Brightening the reverse is the cheap stand-in for that."""
        self.face(pts, col)
        self.face(list(reversed(pts)), back if back is not None else col)

    # ---- primitives ------------------------------------------------------
    def box(self, lo, hi, col, top=None, bottom=None, sides=None, skip=()):
        """Axis-aligned box in the current frame. lo/hi are opposite corners."""
        x0, y0, z0 = lo
        x1, y1, z1 = hi
        s = sides or col
        t = top if top is not None else col
        b = bottom if bottom is not None else shade(s, 0.7)
        quads = {
            "top": ([(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)], t),
            "bottom": ([(x0, y1, z0), (x1, y1, z0), (x1, y0, z0), (x0, y0, z0)], b),
            "front": ([(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)], s),
            "back": ([(x1, y1, z0), (x0, y1, z0), (x0, y1, z1), (x1, y1, z1)], shade(s, 0.86)),
            "left": ([(x0, y1, z0), (x0, y0, z0), (x0, y0, z1), (x0, y1, z1)], shade(s, 0.93)),
            "right": ([(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)], shade(s, 0.93)),
        }
        for k, (pts, c) in quads.items():
            if k not in skip:
                self.face(pts, c)
        return self

    def frustum(self, z0, z1, r0, r1, n, col, cap_top=None, cap_bot=None,
                off1=(0, 0), phase=0.0, squash0=1.0, squash1=1.0):
        """n-gon frustum between z0 and z1. off1 shifts the top ring (lean)."""
        ring0 = [(math.cos(phase + i * TAU / n) * r0,
                  math.sin(phase + i * TAU / n) * r0 * squash0, z0) for i in range(n)]
        ring1 = [(off1[0] + math.cos(phase + i * TAU / n) * r1,
                  off1[1] + math.sin(phase + i * TAU / n) * r1 * squash1, z1) for i in range(n)]
        for i in range(n):
            j = (i + 1) % n
            # light the -Y facing side a touch brighter so the flat shading reads
            f = 1.0 + 0.10 * math.cos(phase + (i + 0.5) * TAU / n + math.pi / 2)
            if r1 < 1e-5:
                self.face([ring0[i], ring0[j], ring1[0]], shade(col, f))
            else:
                self.face([ring0[i], ring0[j], ring1[j], ring1[i]], shade(col, f))
        if cap_top is not None and r1 > 1e-5:
            self.face(ring1, cap_top)
        if cap_bot is not None and r0 > 1e-5:
            self.face(list(reversed(ring0)), cap_bot)
        return self

    def cyl(self, z0, z1, r, n, col, **kw):
        return self.frustum(z0, z1, r, r, n, col, **kw)

    def prism(self, profile, z0, z1, col_side, col_top=None, col_bot=None, shade_by_normal=True):
        """Extrude a closed 2D profile (list of (x,y), CCW) from z0 to z1."""
        n = len(profile)
        for i in range(n):
            a = profile[i]
            b = profile[(i + 1) % n]
            c = col_side
            if shade_by_normal:
                nx, ny = (b[1] - a[1]), -(b[0] - a[0])
                ln = math.hypot(nx, ny) or 1.0
                c = shade(col_side, 1.0 + 0.10 * (-ny / ln))
            self.face([(a[0], a[1], z0), (b[0], b[1], z0), (b[0], b[1], z1), (a[0], a[1], z1)], c)
        if col_top is not None:
            self.face([(p[0], p[1], z1) for p in profile], col_top)
        if col_bot is not None:
            self.face([(p[0], p[1], z0) for p in reversed(profile)], col_bot)
        return self

    def loft(self, rings, col, close=False, cap_first=None, cap_last=None, shade_fn=None):
        """Quad-strip a list of equal-length rings of 3D points."""
        for k in range(len(rings) - 1):
            a, b = rings[k], rings[k + 1]
            n = len(a)
            last = n if close else n - 1
            for i in range(last):
                j = (i + 1) % n
                c = col if shade_fn is None else shade_fn(k, i, col)
                self.face([a[i], a[j], b[j], b[i]], c)
        if cap_first is not None:
            self.face(list(reversed(rings[0])), cap_first)
        if cap_last is not None:
            self.face(rings[-1], cap_last)
        return self

    def strut(self, a, b, r, col, n=4, phase=math.pi / 4):
        """A thin bar (rope, spar, rail) between two points in the current frame."""
        a, b = Vector(a), Vector(b)
        d = b - a
        if d.length < 1e-6:
            return self
        up = Vector((0, 0, 1)) if abs(d.normalized().z) < 0.95 else Vector((1, 0, 0))
        zx = d.normalized()
        xx = up.cross(zx).normalized()
        yy = zx.cross(xx)
        m = Matrix((
            (xx.x, yy.x, zx.x, a.x),
            (xx.y, yy.y, zx.y, a.y),
            (xx.z, yy.z, zx.z, a.z),
            (0, 0, 0, 1),
        ))
        self.push(m)
        self.frustum(0, d.length, r, r, n, col, phase=phase)
        self.pop()
        return self

    def disc(self, r, n, col, rim=None, thick=0.06):
        """Flat disc in the XZ plane of the current frame (faces -Y), e.g. a shield."""
        ring = [(math.cos(i * TAU / n) * r, 0.0, math.sin(i * TAU / n) * r) for i in range(n)]
        back = [(p[0], thick, p[2]) for p in ring]
        self.face(ring, col)
        self.face(list(reversed(back)), shade(col, 0.7))
        rc = rim or shade(col, 0.75)
        for i in range(n):
            j = (i + 1) % n
            self.face([ring[j], ring[i], back[i], back[j]], rc)
        return self

    def gable_roof(self, x0, x1, y0, y1, zb, zt, col, ridge_along_x=True,
                   over=0.0, thick=0.10):
        """Pitched roof as a solid slab with an overhang. Ridge along X or Y."""
        c = col
        cd = shade(col, 0.82)
        ce = shade(col, 0.6)
        if ridge_along_x:
            xm0, xm1 = x0 - over, x1 + over
            ya, yb = y0 - over, y1 + over
            ym = (y0 + y1) * 0.5
            top = [(xm0, ya, zb), (xm1, ya, zb), (xm1, ym, zt), (xm0, ym, zt)]
            top2 = [(xm1, yb, zb), (xm0, yb, zb), (xm0, ym, zt), (xm1, ym, zt)]
            self.face(top, c)
            self.face(top2, cd)
            # under-slab + edges give it thickness so the eaves read
            self.face([(xm0, ya, zb - thick), (xm0, ym, zt - thick), (xm1, ym, zt - thick), (xm1, ya, zb - thick)], ce)
            self.face([(xm1, yb, zb - thick), (xm1, ym, zt - thick), (xm0, ym, zt - thick), (xm0, yb, zb - thick)], ce)
            for xx, flip in ((xm0, False), (xm1, True)):
                pts = [(xx, ya, zb), (xx, ym, zt), (xx, ym, zt - thick), (xx, ya, zb - thick)]
                self.face(pts if flip else list(reversed(pts)), ce)
                pts = [(xx, yb, zb), (xx, ym, zt), (xx, ym, zt - thick), (xx, yb, zb - thick)]
                self.face(list(reversed(pts)) if flip else pts, ce)
            for yy in (ya, yb):
                self.face([(xm0, yy, zb), (xm1, yy, zb), (xm1, yy, zb - thick), (xm0, yy, zb - thick)]
                          if yy == ya else
                          [(xm1, yy, zb), (xm0, yy, zb), (xm0, yy, zb - thick), (xm1, yy, zb - thick)], ce)
        else:
            self.push_trs(rot=(0, 0, math.pi / 2))
            self.gable_roof(y0, y1, -x1, -x0, zb, zt, col, True, over, thick)
            self.pop()
        return self


def _apply_shade_dir(cols, faces, verts):
    """No-op hook kept for symmetry; per-face tints are set at build time."""
    return cols


def finish(build, name, triangulate=True, quiet=False):
    """Turn a Build into a mesh object with a COLOR_0 attribute."""
    me = bpy.data.meshes.new(name)
    me.from_pydata(build.v, [], build.f)
    me.update()
    me.validate(verbose=False)

    att = me.color_attributes.new(name="Color", type="FLOAT_COLOR", domain="CORNER")
    data = att.data
    for pi, poly in enumerate(me.polygons):
        poly.use_smooth = False
        r, g, b = build.c[pi] if pi < len(build.c) else (1, 1, 1)
        for li in poly.loop_indices:
            data[li].color = (r, g, b, 1.0)

    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)

    mat = bpy.data.materials.get("PropVC") or bpy.data.materials.new("PropVC")
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    if bsdf and not any(n.type == "VERTEX_COLOR" for n in nt.nodes):
        vc = nt.nodes.new("ShaderNodeVertexColor")
        vc.layer_name = "Color"
        nt.links.new(vc.outputs["Color"], bsdf.inputs["Base Color"])
        bsdf.inputs["Roughness"].default_value = 1.0
        bsdf.inputs["Metallic"].default_value = 0.0
    me.materials.append(mat)

    if triangulate:
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.triangulate(bm, faces=bm.faces[:])
        bm.to_mesh(me)
        bm.free()
    me.shade_flat()
    if not quiet:
        print("BUILT %-26s tris=%d" % (name, len(me.polygons)))
    return ob


def clear():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for m in list(bpy.data.meshes):
        bpy.data.meshes.remove(m)


def export(ob, name=None, outdir=None):
    name = name or ob.name
    outdir = outdir or OUT
    os.makedirs(outdir, exist_ok=True)
    for o in bpy.context.scene.objects:
        o.select_set(False)
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    path = os.path.join(outdir, name + ".glb")
    bpy.ops.export_scene.gltf(
        filepath=path, export_format="GLB", use_selection=True,
        export_yup=True, export_apply=True, export_normals=True,
        export_vertex_color="ACTIVE", export_all_vertex_colors=False,
        export_texcoords=False, export_materials="EXPORT",
        export_cameras=False, export_lights=False, export_animations=False,
    )
    tris = len(ob.data.polygons)
    print("EXPORT %-26s tris=%-5d %s" % (name, tris, path))
    return tris


def emit(build, name, outdir=None):
    ob = finish(build, name, quiet=True)
    return export(ob, name, outdir)
