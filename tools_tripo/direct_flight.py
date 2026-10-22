"""Straight to the island (Nikita 2026-10-22: "перелёты не по всему маршруту, а к конкретному:
клик по логотипу в конце - лететь весь путь долго; так же клики по карте").

A jump of more than one island (the logo, the chart) no longer scrolls through every leg in
between: the page moves to the target chapter at once and the camera flies there directly -
it turns toward the island, climbs, crosses the archipelago in one arc and comes down onto the
hold. The chapter's text waits until it lands. Next-door islands keep their own leg flights."""
import io
import sys

world_p, app_p = sys.argv[1], sys.argv[2]
w = io.open(world_p, encoding="utf-8").read()

old = "  setCamera(p, elapsed) {\n    const r = this.routeAt(p);\n    let pos, look, roll = 0, fovKick = 0;\n"
new = """  /* Fly straight to an island, whatever the scroll says: one arc from where the camera is now,
     high over the archipelago, down onto the island's hold. Returns the flight's length in s. */
  flyTo(index) {
    const to = this.stationFor(ISLANDS[index]);
    const from = this.camera.position.clone();
    const dist = Math.hypot(to.x - from.x, to.z - from.z);
    const seconds = THREE.MathUtils.clamp(2.4 + dist / 650, 2.4, 4);
    this.direct = { index, from, fromLook: (this.camLook || to).clone(), to, dist, t0: this.lastElapsed || 0, seconds };
    return seconds;
  }

  directPose(elapsed) {
    const d = this.direct;
    const k = THREE.MathUtils.clamp((elapsed - d.t0) / d.seconds, 0, 1);
    if (k >= 1) { this.direct = null; return null; }
    const s = 0.5 - 0.5 * Math.cos(Math.PI * k);            // lift off slowly, land slowly
    const target = new THREE.Vector3(ISLANDS[d.index].pos[0], 0, ISLANDS[d.index].pos[1]);
    // one arc: a quadratic curve whose top rides high over the islands in between
    const top = d.from.clone().lerp(d.to, 0.5);
    top.y = Math.max(d.from.y, d.to.y) + Math.min(260, 60 + d.dist * 0.22);
    const pos = d.from.clone().multiplyScalar((1 - s) * (1 - s))
      .addScaledVector(top, 2 * s * (1 - s)).addScaledVector(d.to, s * s);
    // the bird turns to its goal first, then keeps it in sight all the way
    const look = d.fromLook.clone().lerp(target, THREE.MathUtils.smoothstep(k, 0, 0.35));
    return { pos, look };
  }

  setCamera(p, elapsed) {
    const r = this.routeAt(p);
    let pos, look, roll = 0, fovKick = 0;
    const direct = this.direct && this.directPose(elapsed);
    if (direct) {
      ({ pos, look } = direct);
    } else
"""
assert w.count(old) == 1
w = w.replace(old, new)
io.open(world_p, "w", encoding="utf-8").write(w)

a = io.open(app_p, encoding="utf-8").read()
old = """  function sailTo(index, msOverride) {
    index = THREE.MathUtils.clamp(index, 0, n - 1);
    const to = holdTop(index);
    if (reduced) { scrollTo(0, to); return; }
"""
new = """  // more than one island away: the page goes there at once and the camera flies straight to it
  let directTimer = 0;
  function flyStraight(index) {
    if (sailing) { sailing = null; vel = 0; }
    const seconds = world.flyTo(index);
    pos = holdTop(index);
    scrollTo(0, pos);
    const next = panels.find((p) => p.dataset.island === ISLANDS[index].id);
    if (next) world.setTextSide(next.classList.contains('right') ? -1 : 1);
    document.body.classList.add('sailing');
    clearTimeout(directTimer);
    directTimer = setTimeout(() => document.body.classList.remove('sailing'), seconds * 1000);
  }

  function sailTo(index, msOverride) {
    index = THREE.MathUtils.clamp(index, 0, n - 1);
    const to = holdTop(index);
    if (reduced) { scrollTo(0, to); return; }
    const from = sailing ? sailing.index : chapterAt(Math.min(scrollY, maxScroll()));
    if (Math.abs(from - index) > 1 || scrollY > maxScroll() + 2) { flyStraight(index); return; }
"""
assert a.count(old) == 1
a = a.replace(old, new)
old = "    if (scrollY > maxScroll() + 2) scrollTo({ top: maxScroll(), behavior: 'auto' });\n    sailTo(0, 3800);   // home is one swift flight back, however far the voyage went\n"
new = "    sailTo(0);   // from far away this is one straight flight home\n"
assert a.count(old) == 1
a = a.replace(old, new)
io.open(app_p, "w", encoding="utf-8").write(a)
print("ok")
