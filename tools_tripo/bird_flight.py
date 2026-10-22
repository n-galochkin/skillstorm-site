"""The voyage flown like a bird (Nikita 2026-10-22: "слишком быстро и местами криво. Пролёт от
лица птицы не по прямой, с опусканием вниз и вверх, с облётом острова; скорость по кривой -
начало и конец с замедлением").

- Each leg is one smooth path (centripetal Catmull-Rom) through waypoints: lift off and glide
  down, skim low over the water off to one side, come at the next island from the flank,
  sweep round it and settle on the hold. The long leg to the storm climbs over the clouds
  first. The path never goes lower than 22 m above whatever island is under it.
- The camera moves along the path by arc length, so its speed follows the page's own easing.
- Mid-flight it looks ahead and down along its course; at both ends it turns to the island.
  It banks from the curvature of the turn, smoothed.
- Paging is a timed glide with a slow start and a slow end (~3 s a leg) instead of a spring;
  the chapter text leaves at once, so the turn of the page is felt immediately.
- The holds on the scroll track shrink, so the camera leaves as soon as the page does."""
import io
import sys

world_p, app_p, html_p = sys.argv[1:4]
w = io.open(world_p, encoding="utf-8").read()

old = """  buildRoute() {
    const points = ISLANDS.map((s) => this.stationFor(s));
    const looks = ISLANDS.map((s) => new THREE.Vector3(s.pos[0], 0, s.pos[1]));
    this.routeCurve = new THREE.CatmullRomCurve3(points, false, 'catmullrom', 0.4);
    this.lookCurve = new THREE.CatmullRomCurve3(looks, false, 'catmullrom', 0.4);
  }
"""
new = """  buildRoute() {
    const points = ISLANDS.map((s) => this.stationFor(s));
    const looks = ISLANDS.map((s) => new THREE.Vector3(s.pos[0], 0, s.pos[1]));
    this.routeCurve = new THREE.CatmullRomCurve3(points, false, 'catmullrom', 0.4);
    this.lookCurve = new THREE.CatmullRomCurve3(looks, false, 'catmullrom', 0.4);
    this.legs = ISLANDS.slice(0, -1).map((_, i) => this.birdPath(i));
  }

  /* The highest island ground under a point (0 over open water). */
  groundUnder(x, z) {
    let top = 0;
    for (const t of this.terrain.values()) top = Math.max(top, t.worldHeight(x, z) || 0);
    return top;
  }

  /* One leg as a bird would fly it: off the hold with a gliding drop, low over the water off
     to one side, in at the next island from its flank, round it, and down onto the hold. */
  birdPath(i) {
    const A = this.stationFor(ISLANDS[i]), B = this.stationFor(ISLANDS[i + 1]);
    const LA = new THREE.Vector3(ISLANDS[i].pos[0], 0, ISLANDS[i].pos[1]);
    const LB = new THREE.Vector3(ISLANDS[i + 1].pos[0], 0, ISLANDS[i + 1].pos[1]);
    const RB = ISLANDS[i + 1].radius;
    const span = new THREE.Vector3().subVectors(LB, LA);
    const D = span.length();
    const dir = span.clone().normalize();
    const side = new THREE.Vector3(dir.z, 0, -dir.x).multiplyScalar(i % 2 ? 1 : -1);
    const at = (base, along, aside, y) => base.clone().addScaledVector(dir, along).addScaledVector(side, aside).setY(y);
    const pts = [A.clone()];
    pts.push(at(A, D * 0.16, D * 0.06, A.y * 0.62));                     // off the hold, gliding down
    if (D > 500) {                                                          // the long way to the storm:
      pts.push(at(LA, D * 0.32, -D * 0.08, 230));                           // up over the clouds
      pts.push(at(LA, D * 0.62, D * 0.1, 70));                              // and back down
    } else {
      pts.push(at(LA, D * 0.5, D * 0.24, 26));                              // low over the water, off to one side
    }
    // in at the next island from its flank, then a sweep round it onto the hold
    const fromA = Math.atan2(LA.z - LB.z, LA.x - LB.x);
    const toHold = Math.atan2(B.z - LB.z, B.x - LB.x);
    const turn = (i % 2 ? 1 : -1) * 1.25;
    let sweep = toHold - (fromA + turn);
    while (sweep > Math.PI) sweep -= 2 * Math.PI;
    while (sweep < -Math.PI) sweep += 2 * Math.PI;
    const hold = Math.hypot(B.x - LB.x, B.z - LB.z);
    const ring = (a, r, y) => new THREE.Vector3(LB.x + Math.cos(a) * r, y, LB.z + Math.sin(a) * r);
    pts.push(ring(fromA + turn, Math.max(RB * 1.9, hold * 0.8), B.y * 0.45));
    pts.push(ring(fromA + turn + sweep * 0.55, hold * 0.95, B.y * 0.72));
    pts.push(B.clone());
    // never through a hillside: lift any waypoint that sits too close to the ground
    for (const p of pts) p.y = Math.max(p.y, this.groundUnder(p.x, p.z) + 22);
    return new THREE.CatmullRomCurve3(pts, false, 'centripetal');
  }
"""
assert w.count(old) == 1
w = w.replace(old, new)

# routeAt: tiny holds; no smoothstep on top of the page's own easing
old = "    const hold = 1.0, travel = 1.45;\n"
assert w.count(old) == 1
w = w.replace(old, "    const hold = HOLD, travel = TRAVEL;\n")
old = "        const eased = local * local * (3 - 2 * local);\n"
assert w.count(old) == 1
w = w.replace(old, "        const eased = local;   // the page glide already starts and ends slowly\n")

# the flight itself
f0 = w.index("  /* One leg of the voyage as a staged flight.")
f1 = w.index("  setCamera(p, elapsed) {")
w = w[:f0] + """  /* One leg of the voyage, flown along its bird path. The camera looks ahead and down along
     its course in mid-flight and turns to the island at both ends; it banks with the turn. */
  flight(leg, e) {
    const path = this.legs[leg];
    const s = THREE.MathUtils.clamp(e, 0, 1);
    const pos = path.getPointAt(s);
    const ahead = path.getPointAt(Math.min(1, s + 0.03));
    const behind = path.getPointAt(Math.max(0, s - 0.03));
    const course = ahead.clone().sub(behind);
    const flat = new THREE.Vector3(course.x, 0, course.z);
    if (flat.lengthSq() < 1e-6) flat.set(0, 0, -1);
    flat.normalize();
    // where a bird would look: well ahead along its course, and down at the sea
    const gaze = pos.clone().addScaledVector(flat, 140);
    gaze.y = Math.max(0, pos.y - 70);
    const LA = new THREE.Vector3(ISLANDS[leg].pos[0], 0, ISLANDS[leg].pos[1]);
    const LB = new THREE.Vector3(ISLANDS[leg + 1].pos[0], 0, ISLANDS[leg + 1].pos[1]);
    const look = gaze.clone()
      .lerp(LA, 1 - THREE.MathUtils.smoothstep(s, 0, 0.22))
      .lerp(LB, THREE.MathUtils.smoothstep(s, 0.7, 1));
    // bank with the turn: how far the course swings between just behind and just ahead
    const a0 = Math.atan2(pos.z - behind.z, pos.x - behind.x);
    const a1 = Math.atan2(ahead.z - pos.z, ahead.x - pos.x);
    let swing = a1 - a0;
    while (swing > Math.PI) swing -= 2 * Math.PI;
    while (swing < -Math.PI) swing += 2 * Math.PI;
    const ends = THREE.MathUtils.smoothstep(s, 0, 0.12) * (1 - THREE.MathUtils.smoothstep(s, 0.88, 1));
    const roll = THREE.MathUtils.clamp(-swing * 220, -16, 16) * ends;
    // low over the water the lens opens a touch: the sea rushes past
    const fov = 6 * (1 - THREE.MathUtils.smoothstep(pos.y, 30, 110)) * ends;
    return { pos, look, roll, fov };
  }

""" + w[f1:]

# the bank is smoothed frame to frame
old = "    if (r.moving) ({ pos, look, roll, fov: fovKick } = this.flight(r.leg, r.e));\n"
new = ("    if (r.moving) ({ pos, look, roll, fov: fovKick } = this.flight(r.leg, r.e));\n"
       "    this.rollSm = THREE.MathUtils.damp(this.rollSm || 0, roll, 3, 1 / 60);\n"
       "    roll = this.rollSm;\n")
assert w.count(old) == 1
w = w.replace(old, new)

old = "const FLIGHTS = ['bank', 'skim', 'climbSpiral', 'dive', 'orbit'];\n"
new = ("// the scroll track: a short hold at each island, a long flight between them\n"
       "export const HOLD = 0.2, TRAVEL = 1.45;\n")
assert w.count(old) == 1
w = w.replace(old, new)
w = w.replace("/* the voyage's flights, one per leg: landing->fight, fight->skills, skills->storm,\n   storm->forge, forge->devlog (see World.flight) */\n", "")
io.open(world_p, "w", encoding="utf-8").write(w)

a = io.open(app_p, encoding="utf-8").read()
a = a.replace("import { World, LIGHT } from './world.js';", "import { World, LIGHT, HOLD, TRAVEL } from './world.js';", 1)
old = "  const TOTAL = n * 1.0 + (n - 1) * 1.45;\n"
assert a.count(old) == 1
a = a.replace(old, "  const TOTAL = n * HOLD + (n - 1) * TRAVEL;\n")
old = "  const holdTop = (index) => (index ? ((index * 2.45 + 0.5) / TOTAL) * maxScroll() : 0);\n"
assert a.count(old) == 1
a = a.replace(old, "  const holdTop = (index) => (index ? ((index * (HOLD + TRAVEL) + HOLD / 2) / TOTAL) * maxScroll() : 0);\n")
old = "  const unitVh = LIGHT ? 48 : 58;\n"
if a.count(old) == 1:
    a = a.replace(old, "  const unitVh = LIGHT ? 64 : 76;   // the track keeps its old length with the shorter holds\n")

# the spring becomes a timed glide that eases in and out
g0 = a.index("  function glide(now, last) {")
g1 = a.index("  chartGoTo = (index) => sailTo(index);")
a = a[:g0] + """  // ease in, ease out: a bird lifting off and settling (sine in/out, then a cubic tail)
  const ease = (k) => (k < 1 ? 0.5 - 0.5 * Math.cos(Math.PI * k) : 1);
  function glide(now) {
    if (!sailing) return;
    const k = Math.min(1, (now - sailing.t0) / sailing.ms);
    pos = sailing.from + (sailing.to - sailing.from) * ease(k);
    scrollTo(0, pos);
    if (k < 1) requestAnimationFrame(glide);
    else {
      sailing = null; vel = 0;
      document.body.classList.remove('sailing');
      quietUntil = performance.now() + 250;
    }
  }

  function sailTo(index) {
    index = THREE.MathUtils.clamp(index, 0, n - 1);
    const to = holdTop(index);
    if (reduced) { scrollTo(0, to); return; }
    const from = scrollY;
    if (Math.abs(to - from) < 2) return;
    // about three seconds a leg; a jump of several islands takes longer, but not much
    const legs = Math.abs(chapterAt(from) - index) || 1;
    const ms = Math.min(3000 + (legs - 1) * 1100, 6500);
    const fresh = !sailing;
    sailing = { to, index, from, t0: performance.now(), ms };
    // the chapter's text leaves at once: the turn of the page is felt before the camera moves
    document.body.classList.add('sailing');
    if (fresh) requestAnimationFrame(glide);
  }
""" + a[g1:]
a = a.replace("    sailTo(here + dir, Math.abs(touchV) * 0.6 + 300);\n", "    sailTo(here + dir);\n")
a = a.replace("    if (page(dir, 420 + Math.min(px, 120) * 6)) e.preventDefault();\n", "    if (page(dir)) e.preventDefault();\n")
a = a.replace("    if (inVoyage(dir) && page(dir, 700)) e.preventDefault();\n", "    if (inVoyage(dir) && page(dir)) e.preventDefault();\n")
a = a.replace("  function page(dir, kick) {\n", "  function page(dir) {\n")
a = a.replace("sailTo(n - 1, kick)", "sailTo(n - 1)").replace("    sailTo(target, kick);\n", "    sailTo(target);\n")
a = a.replace("    const px = Math.abs(e.deltaY) * (e.deltaMode === 1 ? 32 : 1);\n", "")
io.open(app_p, "w", encoding="utf-8").write(a)

h = io.open(html_p, encoding="utf-8").read()
old = "</style>"
assert h.count(old) == 1
h = h.replace(old, "/* while the page sails to the next island the chapter's text is already gone */\nbody.sailing .panel{opacity:0 !important; pointer-events:none; transition:opacity .25s ease}\n" + old)
io.open(html_p, "w", encoding="utf-8").write(h)
print("ok")
