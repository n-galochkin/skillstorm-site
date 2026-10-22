"""Forward and return flights (Nikita 2026-10-22): forward - an ordinary curved route with a dive
down, no circling; back - first a circle round the island you are leaving, then home along the
same route, the camera looking the way it flies. The direction of a leg is fixed by the side the
camera entered it from, so a change of mind mid-leg rolls back along the same curve instead of
jumping to the other one. The volcano leg follows the same recipe (its old climb read oddly).
The page also slides the frame toward the next chapter's free side as soon as a flight starts,
so the island arrives where it belongs instead of shifting after the landing."""
import io
import sys

world_p, app_p = sys.argv[1], sys.argv[2]
w = io.open(world_p, encoding="utf-8").read()

b0 = w.index("  /* One leg as a bird would fly it:")
b1 = w.index("  /* The highest island ground under a point")
# keep groundUnder; replace birdPath (which sits after it)
p0 = w.index("  /* One leg as a bird would fly it:")
p1 = w.index("    return new THREE.CatmullRomCurve3(pts, false, 'centripetal');\n  }\n", p0) + len("    return new THREE.CatmullRomCurve3(pts, false, 'centripetal');\n  }\n")
w = w[:p0] + """  /* One leg, both ways. Forward: off the hold with a gliding drop, a dive low over the water
     off to one side, a climb toward the next island and down onto its hold - a curve, no
     circling. Back: a circle round the island being left, then the forward route in reverse. */
  birdPath(i) {
    const A = this.stationFor(ISLANDS[i]), B = this.stationFor(ISLANDS[i + 1]);
    const LB = new THREE.Vector3(ISLANDS[i + 1].pos[0], 0, ISLANDS[i + 1].pos[1]);
    // measured from hold to hold, not island to island: a hold sits well off its island's centre
    const span = new THREE.Vector3(B.x - A.x, 0, B.z - A.z);
    const D = span.length();
    const dir = span.clone().normalize();
    const side = new THREE.Vector3(dir.z, 0, -dir.x).multiplyScalar(i % 2 ? 1 : -1);
    const at = (along, aside, y) => A.clone().addScaledVector(dir, along).addScaledVector(side, aside).setY(y);
    const lowY = 26;
    const mid = [
      at(D * 0.18, D * 0.05, THREE.MathUtils.lerp(A.y, lowY, 0.45)),        // off the hold, gliding down
      at(D * 0.46, D * 0.16, lowY),                                         // the dive: low over the water
      at(D * 0.76, D * 0.07, THREE.MathUtils.lerp(lowY, B.y, 0.6)),         // and the climb toward the island
    ];
    const lift = (p) => { p.y = Math.max(p.y, this.groundUnder(p.x, p.z) + 22); return p; };
    mid.forEach(lift);
    const forward = new THREE.CatmullRomCurve3([A.clone(), ...mid, B.clone()], false, 'centripetal');

    // back: round the island first - the long way round, out of the hold and into the route
    const hold = Math.hypot(B.x - LB.x, B.z - LB.z);
    const from = Math.atan2(B.z - LB.z, B.x - LB.x);
    const exit = Math.atan2(mid[2].z - LB.z, mid[2].x - LB.x);
    let sweep = exit - from;
    while (sweep <= 0) sweep += 2 * Math.PI;              // counter-clockwise ...
    if (sweep < Math.PI) sweep -= 2 * Math.PI;            // ... unless that is the short way: then clockwise
    const ringY = Math.max(B.y * 0.75, 50);
    const ring = [0.25, 0.5, 0.75].map((f) => lift(new THREE.Vector3(
      LB.x + Math.cos(from + sweep * f) * hold * 1.05, THREE.MathUtils.lerp(B.y, ringY, Math.sin(Math.PI * f)),
      LB.z + Math.sin(from + sweep * f) * hold * 1.05)));
    const back = new THREE.CatmullRomCurve3([B.clone(), ...ring, ...mid.slice().reverse(), A.clone()], false, 'centripetal');
    return { forward, back };
  }
""" + w[p1:]

f0 = w.index("  /* One leg of the voyage, flown along its bird path.")
f1 = w.index("  setCamera(p, elapsed) {")
w = w[:f0] + """  /* One leg of the voyage. `e` runs 0 at the leg's first island to 1 at its second; `back`
     says the camera entered from the second, so it flies the return route. Forward it looks at
     where it is going; on the way back it looks the way it flies. It banks with the turn. */
  flight(leg, e, back) {
    const path = back ? this.legs[leg].back : this.legs[leg].forward;
    const s = THREE.MathUtils.clamp(back ? 1 - e : e, 0, 1);
    const pos = path.getPointAt(s);
    const ahead = path.getPointAt(Math.min(1, s + 0.03));
    const behind = path.getPointAt(Math.max(0, s - 0.03));
    const flat = new THREE.Vector3(ahead.x - behind.x, 0, ahead.z - behind.z);
    if (flat.lengthSq() < 1e-6) flat.set(0, 0, -1);
    flat.normalize();
    const gaze = pos.clone().addScaledVector(flat, 150);
    gaze.y = Math.max(0, pos.y - 60);
    const L0 = new THREE.Vector3(ISLANDS[leg].pos[0], 0, ISLANDS[leg].pos[1]);
    const L1 = new THREE.Vector3(ISLANDS[leg + 1].pos[0], 0, ISLANDS[leg + 1].pos[1]);
    const leaving = back ? L1 : L0, going = back ? L0 : L1;
    const look = gaze.clone();
    // forward a bird keeps its goal in sight; flying home it just watches the way ahead
    if (!back) look.lerp(going, 0.6 + 0.4 * THREE.MathUtils.smoothstep(s, 0.4, 0.8));
    else look.lerp(going, THREE.MathUtils.smoothstep(s, 0.82, 1));
    look.lerp(leaving, 1 - THREE.MathUtils.smoothstep(s, 0, back ? 0.12 : 0.2));
    // bank with the turn
    const a0 = Math.atan2(pos.z - behind.z, pos.x - behind.x);
    const a1 = Math.atan2(ahead.z - pos.z, ahead.x - pos.x);
    let swing = a1 - a0;
    while (swing > Math.PI) swing -= 2 * Math.PI;
    while (swing < -Math.PI) swing += 2 * Math.PI;
    const ends = THREE.MathUtils.smoothstep(s, 0, 0.12) * (1 - THREE.MathUtils.smoothstep(s, 0.88, 1));
    const roll = THREE.MathUtils.clamp(-swing * 220, -16, 16) * ends;
    const fov = 6 * (1 - THREE.MathUtils.smoothstep(pos.y, 30, 110)) * ends;
    return { pos, look, roll, fov };
  }

""" + w[f1:]

old = "    if (r.moving) ({ pos, look, roll, fov: fovKick } = this.flight(r.leg, r.e));\n"
new = """    // a leg's direction is the side the camera came in from, held until it reaches a hold
    if (r.moving) {
      if (this.activeLeg !== r.leg) { this.activeLeg = r.leg; this.legBack = r.e > 0.5; }
      ({ pos, look, roll, fov: fovKick } = this.flight(r.leg, r.e, this.legBack));
    } else this.activeLeg = null;
    if (r.moving) {}
"""
assert w.count(old) == 1
w = w.replace(old, new)
# the following `else {` belonged to the old one-line if: fold it into a plain hold branch
old = "    if (r.moving) {}\n    else {\n"
assert w.count(old) == 1
w = w.replace(old, "    if (!r.moving) {\n")
io.open(world_p, "w", encoding="utf-8").write(w)

a = io.open(app_p, encoding="utf-8").read()
old = "    sailing = { to, index, speed };\n"
new = ("    sailing = { to, index, speed };\n"
       "    // the frame starts sliding toward the next chapter's free side right away, so the island\n"
       "    // lands where it belongs instead of shifting once the text appears\n"
       "    const next = panels.find((p) => p.dataset.island === ISLANDS[index].id);\n"
       "    if (next) world.setTextSide(next.classList.contains('right') ? -1 : 1);\n")
assert a.count(old) == 1
a = a.replace(old, new)
io.open(app_p, "w", encoding="utf-8").write(a)
print("ok")
