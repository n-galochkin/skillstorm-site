"""Smooth the camera's turns (Nikita 2026-10-22: "у камер дёрганые переходы между направлениями,
нужно как-то интерполировать между маршрутами").

Two causes, two fixes:
- a page turn restarted from rest whenever a new one came while gliding (and a reversal snapped
  the direction): the glide is now one continuous motion that only changes its target - the
  speed carries over, starts ramp up under an acceleration cap, stops ease out;
- the computed camera has corners where a flight meets a hold or the next flight: the real
  camera now trails the computed one by about a quarter of a second (position, gaze, bank),
  which rounds every corner off, and comes back from the fight as a glide, not a jump."""
import io
import sys

world_p, app_p = sys.argv[1], sys.argv[2]
w = io.open(world_p, encoding="utf-8").read()

old = """    // the bank is smoothed frame to frame, so a turn never snaps the horizon
    this.rollSm = THREE.MathUtils.damp(this.rollSm || 0, roll, 3, 1 / 60);
    roll = this.rollSm;
"""
new = """    // the real camera trails the computed one by about a quarter of a second: every corner
    // where a flight meets a hold or the next flight is rounded off. A still frame (a capture,
    // the first frame) or a long gap snaps straight to it; coming back from the fight glides.
    const dt = this.lastElapsed === undefined ? 0 : elapsed - this.lastElapsed;
    this.lastElapsed = elapsed;
    const snap = !this.camPos || dt <= 0 || dt > 0.25;
    if (snap) {
      this.camPos = pos.clone(); this.camLook = look.clone(); this.rollSm = roll;
    } else {
      if (this.detached) {   // the fight moved the camera itself: start from where it is now
        this.camPos.copy(this.camera.position);
        this.camLook.copy(this.camera.position).add(this.camera.getWorldDirection(new THREE.Vector3()).multiplyScalar(150));
      }
      const k = 1 - Math.exp(-4.2 * dt);
      this.camPos.lerp(pos, k);
      this.camLook.lerp(look, k);
      this.rollSm = THREE.MathUtils.damp(this.rollSm || 0, roll, 3, dt);
    }
    this.detached = false;
    pos = this.camPos.clone();
    look = this.camLook.clone();
    roll = this.rollSm;
"""
assert w.count(old) == 1
w = w.replace(old, new)
old = """  focusIsland(spec, zoom) {
    this.camera.position.copy(this.stationFor(spec, zoom));
"""
new = """  focusIsland(spec, zoom) {
    this.detached = true;     // the voyage camera picks up from here when the fight ends
    this.camera.position.copy(this.stationFor(spec, zoom));
"""
assert w.count(old) == 1
w = w.replace(old, new)
io.open(world_p, "w", encoding="utf-8").write(w)

a = io.open(app_p, encoding="utf-8").read()
g0 = a.index("  // ease in, ease out: a bird lifting off and settling")
g1 = a.index("  chartGoTo = (index) => sailTo(index);")
a = a[:g0] + """  /* The glide: one continuous motion toward a target that may change on the way. It wants to
     close the distance at a pace that slows as it nears (the soft landing), but its speed can
     change only so fast (the gentle lift-off), and a new target never resets that speed - so a
     second flick carries on, and a turn back slows, stops and reverses instead of snapping. */
  const step = () => (maxScroll() / TOTAL) * (HOLD + TRAVEL);   // one island to the next, in px
  let lastT = 0;
  function glide(now) {
    if (!sailing) return;
    const dt = Math.min(0.05, (now - lastT) / 1000 || 0.016);
    lastT = now;
    const d = sailing.to - pos;
    const L = step();
    const vMax = L * 0.62 * sailing.speed;            // cruise: about a leg in under two seconds
    const want = THREE.MathUtils.clamp(d * 1.5, -vMax, vMax);
    const aMax = L * 1.15 * sailing.speed;            // lift-off: a third of a second to cruise
    vel += THREE.MathUtils.clamp(want - vel, -aMax * dt, aMax * dt);
    pos += vel * dt;
    if (Math.abs(d) < 0.5 && Math.abs(vel) < 6) {
      pos = sailing.to; scrollTo(0, pos);
      sailing = null; vel = 0;
      document.body.classList.remove('sailing');
      quietUntil = performance.now() + 250;
      return;
    }
    scrollTo(0, pos);
    requestAnimationFrame(glide);
  }

  function sailTo(index, msOverride) {
    index = THREE.MathUtils.clamp(index, 0, n - 1);
    const to = holdTop(index);
    if (reduced) { scrollTo(0, to); return; }
    if (!sailing && Math.abs(to - scrollY) < 2) return;
    const fresh = !sailing;
    if (fresh) { pos = scrollY; vel = 0; lastT = performance.now(); }
    // a long way (home from the far end, a click on the chart) flies faster, not longer
    const legs = Math.abs(chapterAt(pos) - index) || 1;
    const speed = msOverride ? Math.max(1, legs / 2) : Math.max(1, legs * 0.7);
    sailing = { to, index, speed };
    // the chapter's text leaves at once: the turn of the page is felt before the camera moves
    document.body.classList.add('sailing');
    if (fresh) requestAnimationFrame(glide);
  }
""" + a[g1:]
io.open(app_p, "w", encoding="utf-8").write(a)
print("ok")
