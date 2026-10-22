"""Staged camera flights between the islands (Nikita 2026-10-22: "нестандартные перелёты камеры,
как на brand.ivress.co.jp"). IVRESS scrubs hand-animated camera clips with the scroll and lets
the frame lean toward the mouse; here every leg of the voyage gets its own manoeuvre - a bank,
a skim over the water, a climb and a spiral, a dive, an orbit - built on the straight blend
between two stations, so each flight still starts and ends exactly on its island."""
import io
import sys

world_p, app_p = sys.argv[1], sys.argv[2]
w = io.open(world_p, encoding="utf-8").read()

old = "        return { u: (seg.i + eased) / (n - 1), station: eased < 0.5 ? seg.i : seg.i + 1, local, moving: true };\n"
new = "        return { u: (seg.i + eased) / (n - 1), station: eased < 0.5 ? seg.i : seg.i + 1, local, moving: true, leg: seg.i, e: eased };\n"
assert w.count(old) == 1
w = w.replace(old, new)

old = """  setCamera(p, elapsed) {
    const r = this.routeAt(p);
    const pos = this.routeCurve.getPoint(r.u);
    const look = this.lookCurve.getPoint(r.u);
"""
new = """  /* One leg of the voyage as a staged flight. Every manoeuvre is an offset on the plain blend
     between the two stations that vanishes at both ends (sin(pi*e) and friends), so a flight
     always leaves from and lands on the exact hold over its island. */
  flight(leg, e) {
    const A = this.stationFor(ISLANDS[leg]), B = this.stationFor(ISLANDS[leg + 1]);
    const LA = new THREE.Vector3(ISLANDS[leg].pos[0], 0, ISLANDS[leg].pos[1]);
    const LB = new THREE.Vector3(ISLANDS[leg + 1].pos[0], 0, ISLANDS[leg + 1].pos[1]);
    const pos = A.clone().lerp(B, e), look = LA.clone().lerp(LB, e);
    const dir = new THREE.Vector3(B.x - A.x, 0, B.z - A.z);
    const dist = dir.length();
    dir.normalize();
    const side = new THREE.Vector3(dir.z, 0, -dir.x);
    const bump = Math.sin(Math.PI * e);
    const smooth = (a, b, x) => THREE.MathUtils.smoothstep(x, a, b);
    let roll = 0, fov = 0;
    const turnAround = (centre, from, angle) => {
      const v = from.clone().sub(centre), c = Math.cos(angle), s = Math.sin(angle);
      return new THREE.Vector3(centre.x + v.x * c - v.z * s, from.y, centre.z + v.x * s + v.z * c);
    };
    switch (FLIGHTS[leg]) {
      case 'bank': {        // a wide banked turn, leaning into the curve, eyes a little ahead
        pos.addScaledVector(side, dist * 0.32 * bump);
        pos.y += 34 * bump;
        look.addScaledVector(dir, dist * 0.14 * bump);
        roll = -15 * bump;
        break;
      }
      case 'skim': {        // drop to the waves and race over the water, then pull up
        const low = Math.pow(bump, 0.7);
        pos.y = THREE.MathUtils.lerp(pos.y, 16, low);
        const ahead = pos.clone().addScaledVector(dir, 120);
        ahead.y = 6;
        look.lerp(ahead, low);
        roll = 5 * Math.sin(2 * Math.PI * e);
        fov = 8 * low;
        break;
      }
      case 'climbSpiral': { // climb over the clouds, then spiral down round the storm
        pos.y += 300 * bump;
        const below = pos.clone().addScaledVector(dir, 60);
        below.y = 0;
        look.lerp(below, smooth(0.05, 0.5, e) * (1 - smooth(0.55, 0.95, e)));
        const spin = smooth(0.45, 1, e);
        if (spin > 0) pos.copy(pos.clone().lerp(turnAround(LB, pos, -2.2 * (1 - e)), spin));
        roll = -12 * bump;
        fov = 12 * bump;
        break;
      }
      case 'dive': {        // a short hop up, then a steep dive with a long lens
        pos.y += 170 * Math.sin(Math.PI * Math.min(1, e * 1.6)) * (1 - e * 0.6);
        roll = 9 * Math.sin(2 * Math.PI * e);
        fov = -11 * bump;
        break;
      }
      case 'orbit': {       // swing round the next island on the way in
        const ring = turnAround(LB, B, -2.4 * (1 - e));
        ring.y = B.y + 50 * bump;
        pos.lerp(ring, smooth(0.1, 0.55, e));
        roll = 10 * bump;
        break;
      }
    }
    return { pos, look, roll, fov };
  }

  setCamera(p, elapsed) {
    const r = this.routeAt(p);
    let pos, look, roll = 0, fovKick = 0;
    if (r.moving) ({ pos, look, roll, fov: fovKick } = this.flight(r.leg, r.e));
    else {
      pos = this.stationFor(ISLANDS[r.station]);
      look = new THREE.Vector3(ISLANDS[r.station].pos[0], 0, ISLANDS[r.station].pos[1]);
    }
    // the frame leans a little toward the mouse, the way IVRESS's does (set by the page)
    this.lean = this.lean || new THREE.Vector2();
    this.lean.x = THREE.MathUtils.damp(this.lean.x, (this.leanTarget && this.leanTarget.x) || 0, 2.2, 1 / 60);
    this.lean.y = THREE.MathUtils.damp(this.lean.y, (this.leanTarget && this.leanTarget.y) || 0, 2.2, 1 / 60);
"""
assert w.count(old) == 1
w = w.replace(old, new)

old = """    this.camera.position.copy(pos);
    this.camera.lookAt(look);
    this.camera.rotateZ((Math.sin(elapsed * 0.23) * 0.55 + Math.sin(elapsed * 0.61 + 0.4) * 0.2 + gust * 0.6) * sway * Math.PI / 180);
    return r;
  }
"""
new = """    this.camera.position.copy(pos);
    this.camera.lookAt(look);
    // the mouse lean: slide along the camera's own right and up, a few metres at most
    const right = new THREE.Vector3().setFromMatrixColumn(this.camera.matrixWorld, 0);
    const up = new THREE.Vector3().setFromMatrixColumn(this.camera.matrixWorld, 1);
    this.camera.position.addScaledVector(right, this.lean.x * 7).addScaledVector(up, -this.lean.y * 4);
    this.camera.rotateZ(((Math.sin(elapsed * 0.23) * 0.55 + Math.sin(elapsed * 0.61 + 0.4) * 0.2 + gust * 0.6) * sway + roll) * Math.PI / 180);
    // a manoeuvre may widen or narrow the lens for a moment
    const fov = (this.baseFov || this.camera.fov) + fovKick;
    if (Math.abs(this.camera.fov - fov) > 0.01) { this.camera.fov = fov; this.camera.updateProjectionMatrix(); }
    return r;
  }
"""
assert w.count(old) == 1
w = w.replace(old, new)

old = "    this.camera.fov = tall ? 50 : 42;\n"
new = "    this.camera.fov = this.baseFov = tall ? 50 : 42;\n"
assert w.count(old) == 1
w = w.replace(old, new)

# the flight plan: one manoeuvre per leg of the voyage
old = "/* --------------------------------------------------------------- textures */"
new = ("/* the voyage's flights, one per leg: landing->fight, fight->skills, skills->storm,\n"
       "   storm->forge, forge->devlog (see World.flight) */\n"
       "const FLIGHTS = ['bank', 'skim', 'climbSpiral', 'dive', 'orbit'];\n\n" + old)
assert w.count(old) == 1
w = w.replace(old, new)
io.open(world_p, "w", encoding="utf-8").write(w)

a = io.open(app_p, encoding="utf-8").read()
old = "  const W = 5.2;                // spring stiffness: about 1.2 s from island to island\n"
new = "  const W = 3.9;                // spring stiffness: about 1.7 s, long enough for a manoeuvre to read\n"
assert a.count(old) == 1
a = a.replace(old, new)
old = "  /* ---- size ---- */\n"
new = ("  /* ---- the mouse lean: the frame drifts a little toward the pointer (mouse only) ---- */\n"
       "  if (matchMedia('(pointer:fine)').matches && !reduced) {\n"
       "    world.leanTarget = new THREE.Vector2();\n"
       "    addEventListener('pointermove', (e) => {\n"
       "      if (e.pointerType !== 'mouse' || playing) { world.leanTarget.set(0, 0); return; }\n"
       "      world.leanTarget.set(e.clientX / innerWidth * 2 - 1, e.clientY / innerHeight * 2 - 1);\n"
       "    }, { passive: true });\n"
       "  }\n\n" + old)
assert a.count(old) == 1
a = a.replace(old, new)
io.open(app_p, "w", encoding="utf-8").write(a)
print("ok")
