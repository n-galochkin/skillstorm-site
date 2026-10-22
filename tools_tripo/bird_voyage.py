"""The camera becomes a bird of its own (Nikita 2026-10-22: "сдвиг сначала вбок и потом полёт;
корявые маршруты от вулкана, камеру гнёт и выворачивает; если следующая точка подразумевает
полёт назад - сначала облететь остров, чтобы развернуться. Всегда полёт вперёд, камера смотрит по
направлению полёта, не летает задом и не делает сальто").

The scroll no longer drives the camera along fixed routes. The page only says which island to go
to; the camera flies there from wherever it is, the way it is facing:
- it carries on forward and starts its glide;
- if the goal lies behind or well to the side, it turns in a wide arc first (over and round the
  island it is leaving);
- it cruises - low over the water for a near island, high over the archipelago for a far one;
- if it comes at the goal from the island's far side, it swings round the island;
- and it comes in from behind the hold, already facing the island, so the landing needs no turn.
It looks where it flies, banks with its turns, and a new goal mid-flight starts a new path from
where it is and the way it is heading. The frame's sideways offset rides along with the flight,
from the first island's side to the next one's, instead of sliding first."""
import io
import sys

world_p, app_p = sys.argv[1], sys.argv[2]
w = io.open(world_p, encoding="utf-8").read()

r0 = w.index("  buildRoute() {")
r1 = w.index("  focusIsland(spec, zoom) {")
NEW = r"""  buildRoute() {
    // the camera now flies its own paths (flyTo); the page still calls this once on load
    this.voyage = this.voyage || { station: 0, flight: null, arrivedAt: 0 };
  }

  /* The highest island ground under a point (0 over open water). */
  groundUnder(x, z) {
    let top = 0;
    for (const t of this.terrain.values()) top = Math.max(top, t.worldHeight(x, z) || 0);
    return top;
  }

  /* where the camera is headed: the island it flies to, or the one it holds over */
  target() { return this.voyage.flight ? this.voyage.flight.to : this.voyage.station; }
  isFlying() { return !!this.voyage.flight; }

  /* A bird's path from a pose (position, horizontal heading) to an island's hold: forward only. */
  birdPath(P0, H0, to) {
    const B = this.stationFor(ISLANDS[to]);
    const LB = new THREE.Vector3(ISLANDS[to].pos[0], 0, ISLANDS[to].pos[1]);
    const FB = new THREE.Vector3(LB.x - B.x, 0, LB.z - B.z).normalize();     // facing at the hold
    const flatAngle = (a, b) => Math.atan2(a.x * b.z - a.z * b.x, a.x * b.x + a.z * b.z);
    const pts = [P0.clone()];
    // 1. carry on the way it faces and start the glide
    let cur = P0.clone().addScaledVector(H0, 70);
    cur.y = P0.y - 22;
    pts.push(cur.clone());
    let h = H0.clone();
    // 2. a goal behind or well to the side: a wide turn first, round the island being left
    const toGoal = () => new THREE.Vector3(B.x - cur.x, 0, B.z - cur.z).normalize();
    let ang = flatAngle(h, toGoal());
    if (Math.abs(ang) > 0.7) {
      const sgn = Math.sign(ang) || 1;
      const R = 115;
      const centre = cur.clone().add(new THREE.Vector3(-h.z, 0, h.x).multiplyScalar(-sgn * R));
      for (let i = 0; i < 7 && Math.abs(ang) > 0.45; i++) {
        const v = new THREE.Vector3(cur.x - centre.x, 0, cur.z - centre.z);
        const step = 0.62 * sgn;
        const c = Math.cos(step), s = Math.sin(step);
        cur = new THREE.Vector3(centre.x + v.x * c - v.z * s, Math.max(70, cur.y - 10), centre.z + v.x * s + v.z * c);
        h = new THREE.Vector3(-(cur.z - centre.z), 0, cur.x - centre.x).multiplyScalar(sgn).normalize();
        pts.push(cur.clone());
        ang = flatAngle(h, toGoal());
      }
    }
    // 3. the approach: always from behind the hold, already facing the island
    const hold = Math.hypot(B.x - LB.x, B.z - LB.z);
    const Q = B.clone().addScaledVector(FB, -140);
    Q.y = B.y * 0.85;
    // coming at the island from its far side: swing round it to the approach first
    const aCur = Math.atan2(cur.z - LB.z, cur.x - LB.x), aQ = Math.atan2(Q.z - LB.z, Q.x - LB.x);
    let swing = aQ - aCur;
    while (swing > Math.PI) swing -= 2 * Math.PI;
    while (swing < -Math.PI) swing += 2 * Math.PI;
    const dist = Math.hypot(Q.x - cur.x, Q.z - cur.z);
    // 4. the cruise: a dive low over the water for a near island, high over the islands for a far one
    if (dist > 140) {
      const mid = cur.clone().lerp(Q, 0.5);
      const across = new THREE.Vector3(Q.z - cur.z, 0, cur.x - Q.x).normalize();
      mid.addScaledVector(across, dist * 0.1 * (to % 2 ? 1 : -1));
      mid.y = dist > 450 ? 170 : 30;
      if (Math.abs(swing) < 1.4 || Math.hypot(mid.x - LB.x, mid.z - LB.z) > hold * 1.4) pts.push(mid);
    }
    if (Math.abs(swing) > 1.2) {
      const r = Math.max(hold * 1.35, ISLANDS[to].radius * 1.9);
      for (const f of [0.4, 0.75]) {
        const a = aCur + swing * f;
        pts.push(new THREE.Vector3(LB.x + Math.cos(a) * r, B.y * 0.7, LB.z + Math.sin(a) * r));
      }
    }
    pts.push(Q, B.clone());
    // never through a hillside
    for (let i = 1; i < pts.length - 1; i++) pts[i].y = Math.max(pts[i].y, this.groundUnder(pts[i].x, pts[i].z) + 24);
    return new THREE.CatmullRomCurve3(pts, false, 'centripetal');
  }

  /* Fly to an island from wherever the camera is, the way it faces. Mid-flight this starts a new
     path from the current point and heading, so a change of mind is a turn, not a jump. */
  flyTo(index, elapsed) {
    const v = this.voyage;
    if (!v.flight && index === v.station) return 0;
    const from = (this.camPos || this.camera.position).clone();
    const lookNow = (this.camLook || this.stationFor(ISLANDS[v.station])).clone();
    let heading = new THREE.Vector3(lookNow.x - from.x, 0, lookNow.z - from.z);
    if (v.flight) heading = v.flight.heading.clone();
    if (heading.lengthSq() < 1e-6) heading.set(0, 0, -1);
    heading.normalize();
    const curve = this.birdPath(from, heading, index);
    const length = curve.getLength();
    const seconds = THREE.MathUtils.clamp(length / 190, 2.6, 5.5);
    v.flight = {
      to: index, from: v.flight ? v.flight.from : v.station, curve, seconds, t0: elapsed,
      moving: !!v.flight, lookFrom: lookNow, sideFrom: this.side || 0, heading,
    };
    return seconds;
  }

  /* the pose along the current flight, or null once it has landed */
  flightPose(elapsed) {
    const v = this.voyage, f = v.flight;
    const k = THREE.MathUtils.clamp((elapsed - f.t0) / f.seconds, 0, 1);
    if (k >= 1) { v.station = f.to; v.flight = null; v.arrivedAt = elapsed; return null; }
    // from rest: lift off slowly, land slowly; already flying: keep going, land slowly
    const s = f.moving ? Math.sin(k * Math.PI / 2) : 0.5 - 0.5 * Math.cos(Math.PI * k);
    const c = f.curve;
    const pos = c.getPointAt(s);
    const ahead = c.getPointAt(Math.min(1, s + 0.025)), behind = c.getPointAt(Math.max(0, s - 0.025));
    const flat = new THREE.Vector3(ahead.x - behind.x, 0, ahead.z - behind.z);
    if (flat.lengthSq() > 1e-6) f.heading = flat.clone().normalize();
    // it looks where it flies - ahead along the course and down at the sea - turning to it
    // from where it was looking as it sets off, and to the island as it lands
    const gaze = pos.clone().addScaledVector(f.heading, 150);
    gaze.y = Math.max(0, pos.y - 55);
    const island = new THREE.Vector3(ISLANDS[f.to].pos[0], 0, ISLANDS[f.to].pos[1]);
    const look = f.lookFrom.clone().lerp(gaze, THREE.MathUtils.smoothstep(s, 0, 0.14))
      .lerp(island, THREE.MathUtils.smoothstep(s, 0.84, 1));
    const a0 = Math.atan2(pos.z - behind.z, pos.x - behind.x), a1 = Math.atan2(ahead.z - pos.z, ahead.x - pos.x);
    let turn = a1 - a0;
    while (turn > Math.PI) turn -= 2 * Math.PI;
    while (turn < -Math.PI) turn += 2 * Math.PI;
    const ends = THREE.MathUtils.smoothstep(s, 0, 0.1) * (1 - THREE.MathUtils.smoothstep(s, 0.9, 1));
    const roll = THREE.MathUtils.clamp(-turn * 260, -18, 18) * ends;
    const fov = 5 * (1 - THREE.MathUtils.smoothstep(pos.y, 30, 110)) * ends;
    // the frame's sideways offset rides along with the flight
    const sideTo = this.sides ? this.sides[f.to] : 0;
    const side = THREE.MathUtils.lerp(f.sideFrom, sideTo, THREE.MathUtils.smoothstep(s, 0.05, 0.95));
    return { pos, look, roll, fov, side, k };
  }

  /* where the voyage stands, for the page: the island held or flown to, flying or not, and a
     position along the route for the chart's ship */
  voyageState(elapsed) {
    const v = this.voyage;
    if (!v.flight) return { station: v.station, moving: false, u: v.station, holdFor: elapsed - v.arrivedAt };
    const f = v.flight;
    const k = THREE.MathUtils.clamp((elapsed - f.t0) / f.seconds, 0, 1);
    return { station: f.to, moving: true, u: THREE.MathUtils.lerp(f.from, f.to, k), holdFor: 0 };
  }

  setCamera(p, elapsed) {
    const v = this.voyage;
    let pos, look, roll = 0, fovKick = 0, side;
    const pose = v.flight && this.flightPose(elapsed);
    if (pose) {
      ({ pos, look, roll, fov: fovKick, side } = pose);
    } else {
      pos = this.stationFor(ISLANDS[v.station]);
      look = new THREE.Vector3(ISLANDS[v.station].pos[0], 0, ISLANDS[v.station].pos[1]);
    }
    // the sideways offset: tied to the flight while flying; held at the island's side otherwise
    if (this.sides) {
      this.sideTarget = pose ? side : this.sides[v.station];
      if (pose && this.size) { this.side = side; this.frameFor(this.size[0], this.size[1]); }
    }
    // the real camera trails the computed one by a moment, which rounds off what corners remain;
    // a still frame (a capture, the first frame) or a long gap snaps; back from the fight it glides
    const dt = this.lastElapsed === undefined ? 0 : elapsed - this.lastElapsed;
    this.lastElapsed = elapsed;
    const snap = !this.camPos || dt <= 0 || dt > 0.25;
    if (snap) {
      this.camPos = pos.clone(); this.camLook = look.clone(); this.rollSm = roll;
    } else {
      if (this.detached) {
        this.camPos.copy(this.camera.position);
        this.camLook.copy(this.camera.position).add(this.camera.getWorldDirection(new THREE.Vector3()).multiplyScalar(150));
      }
      const k = 1 - Math.exp(-5 * dt);
      this.camPos.lerp(pos, k);
      this.camLook.lerp(look, k);
      this.rollSm = THREE.MathUtils.damp(this.rollSm || 0, roll, 3, dt);
    }
    this.detached = false;
    pos = this.camPos.clone();
    look = this.camLook.clone();
    roll = this.rollSm;
    // the frame leans a little toward the mouse (set by the page)
    this.lean = this.lean || new THREE.Vector2();
    this.lean.x = THREE.MathUtils.damp(this.lean.x, (this.leanTarget && this.leanTarget.x) || 0, 2.2, 1 / 60);
    this.lean.y = THREE.MathUtils.damp(this.lean.y, (this.leanTarget && this.leanTarget.y) || 0, 2.2, 1 / 60);
    // holding over an island the camera hangs in the wind like a drone
    this.holdSway = THREE.MathUtils.damp(this.holdSway || 0, pose ? 0 : 1, 1.6, 1 / 60);
    const sway = this.holdSway;
    const gust = Math.max(0, Math.sin(elapsed * 0.31) * Math.sin(elapsed * 0.113 + 1.3)) ** 2;
    pos.x += (Math.sin(elapsed * 0.17) * 3.2 + Math.sin(elapsed * 0.53 + 2) * 0.9 + gust * 4.5) * sway;
    pos.z += (Math.cos(elapsed * 0.13) * 2.4 + Math.sin(elapsed * 0.41) * 0.7) * sway;
    pos.y += Math.sin(elapsed * 0.21) * 1.4 + Math.sin(elapsed * 0.67 + 1) * 0.5 * sway;
    look.x += (Math.sin(elapsed * 0.11 + 0.7) * 1.6 + gust * 1.5) * sway;
    look.z += Math.cos(elapsed * 0.09 + 0.3) * 1.2 * sway;
    this.camera.position.copy(pos);
    this.camera.lookAt(look);
    const right = new THREE.Vector3().setFromMatrixColumn(this.camera.matrixWorld, 0);
    const up = new THREE.Vector3().setFromMatrixColumn(this.camera.matrixWorld, 1);
    this.camera.position.addScaledVector(right, this.lean.x * 7).addScaledVector(up, -this.lean.y * 4);
    this.camera.rotateZ(((Math.sin(elapsed * 0.23) * 0.55 + Math.sin(elapsed * 0.61 + 0.4) * 0.2 + gust * 0.6) * sway + roll) * Math.PI / 180);
    const fov = (this.baseFov || this.camera.fov) + fovKick;
    if (Math.abs(this.camera.fov - fov) > 0.01) { this.camera.fov = fov; this.camera.updateProjectionMatrix(); }
    return this.voyageState(elapsed);
  }

"""
w = w[:r0] + NEW + w[r1:]
# the hold stance changes on a tall screen: nothing to rebuild now
w = w.replace("      if (this.routeCurve) this.buildRoute();\n", "")
w = w.replace("// the scroll track: a short hold at each island, a long flight between them\nexport const HOLD = 0.2, TRAVEL = 1.45;\n",
              "// the scroll track: a short hold at each island, a long stretch between them\nexport const HOLD = 0.2, TRAVEL = 1.45;\n")
io.open(world_p, "w", encoding="utf-8").write(w)
print("world ok")
