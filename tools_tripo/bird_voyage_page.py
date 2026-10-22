"""The page side of the bird voyage: paging only names the island to fly to (world.flyTo); the
camera flies there on its own. The scroll position jumps to that chapter's place on the track
(so the end section and the cue keep working), the chapter's text leaves at once and comes back
when the camera lands. A scrollbar drag settles on the nearest island and flies there."""
import io
import sys

app_p = sys.argv[1]
a = io.open(app_p, encoding="utf-8").read()

s0 = a.index("  /* A page turn is a timed glide that lifts off slowly and settles slowly")
s1 = a.index("  addEventListener('keydown', (e) => {\n    if (playing || (e.target.closest")
a = a[:s0] + """  /* A page turn names the island to fly to; the camera flies there by itself (world.flyTo),
     forward only, the way a bird would. The scroll jumps to that chapter's place on the track,
     the chapter's text leaves at once and comes back when the camera lands. */
  let quietUntil = 0;           // a trackpad keeps sending wheel events after a flick
  let lastWheel = 0;
  let quietScroll = false;      // the page's own jumps are not the visitor's scrolling
  function goTo(index) {
    index = THREE.MathUtils.clamp(index, 0, n - 1);
    quietScroll = true;
    scrollTo(0, holdTop(index));
    if (world.flyTo(index, elapsed)) document.body.classList.add('sailing');
  }
  chartGoTo = (index) => goTo(index);

  // inside the voyage, or in the first few pixels past it when heading back up
  const inVoyage = (dir) => scrollY < maxScroll() - 2 || (dir < 0 && scrollY <= maxScroll() + innerHeight * 0.15);
  function page(dir) {
    if (dir < 0 && scrollY > maxScroll() + 2) { goTo(n - 1); return true; }       // back from the end section
    const here = world.target();
    if (dir > 0 && here === n - 1) return false;                                   // on into the end section
    goTo(here + dir);
    return true;
  }

  addEventListener('wheel', (e) => {
    if (playing || e.ctrlKey) return;
    const dir = Math.sign(e.deltaY);
    if (!dir || !inVoyage(dir)) return;
    const now = performance.now();
    // only the first event of a gesture turns the page; the rest of it (a trackpad's long
    // tail, a wheel's extra notches) is swallowed. Another gesture while flying goes one further.
    const fresh = now - lastWheel > 220;
    lastWheel = now;
    if (!fresh || now < quietUntil) { e.preventDefault(); return; }
    quietUntil = now + 350;
    if (page(dir)) e.preventDefault();
  }, { passive: false });

  // touch: a swipe is a page turn; the page itself does not slide under the finger
  let touchY = null;
  addEventListener('touchstart', (e) => { touchY = playing ? null : e.touches[0].clientY; }, { passive: true });
  addEventListener('touchmove', (e) => {
    if (touchY === null) return;
    const dir = Math.sign(touchY - e.touches[0].clientY);
    if (dir && inVoyage(dir) && !(dir > 0 && world.target() === n - 1 && !world.isFlying())) e.preventDefault();
  }, { passive: false });
  addEventListener('touchend', (e) => {
    if (touchY === null) return;
    const dy = touchY - e.changedTouches[0].clientY;
    touchY = null;
    if (Math.abs(dy) < 36) return;
    const dir = Math.sign(dy);
    if (inVoyage(dir)) page(dir);
  });

  // a scrollbar drag (or any scroll the page did not make) settles on the nearest island
  let settleTimer = 0;
  addEventListener('scroll', () => {
    if (quietScroll) { quietScroll = false; return; }
    if (playing || scrollY > maxScroll() + 2) return;
    clearTimeout(settleTimer);
    settleTimer = setTimeout(() => {
      const c = chapterAt(scrollY);
      if (c !== world.target() && world.flyTo(c, elapsed)) document.body.classList.add('sailing');
    }, 180);
  }, { passive: true });

""" + a[s1:]

# the keyboard pages the same way
a = a.replace("    if (inVoyage(dir) && page(dir, 700)) e.preventDefault();\n", "    if (inVoyage(dir) && page(dir)) e.preventDefault();\n")

# the logo goes home in one flight
old = "    sailTo(0);   // from far away this is one straight flight home\n"
assert a.count(old) == 1
a = a.replace(old, "    goTo(0);   // one flight home, straight there\n")

# the frame loop follows the camera's own voyage instead of the scroll
f0 = a.index("      const r = world.routeAt(progress);\n      world.setCamera(progress, elapsed);\n")
old = "      const r = world.routeAt(progress);\n      world.setCamera(progress, elapsed);\n      const spec = ISLANDS[r.station];\n      const settled = !r.moving;\n"
new = ("      const r = world.setCamera(progress, elapsed);\n"
       "      const spec = ISLANDS[r.station];\n"
       "      const settled = !r.moving;\n"
       "      if (settled && document.body.classList.contains('sailing')) document.body.classList.remove('sailing');\n")
assert a.count(old) == 1
a = a.replace(old, new)
old = "        // and the island steps aside to the side the text leaves free\n        if (shown) world.setTextSide(shown.classList.contains('right') ? -1 : 1);\n"
assert a.count(old) == 1
a = a.replace(old, "")
old = "      if (spec.storm) state.storm = settled ? Math.min(1, r.local * 1.6) : 0.2;\n"
assert a.count(old) == 1
a = a.replace(old, "      if (spec.storm) state.storm = settled ? Math.min(1, r.holdFor * 0.6) : 0.2;\n")
old = "      if (chart.__place) chart.__place(r.u * (ISLANDS.length - 1), r.station);\n"
assert a.count(old) == 1
a = a.replace(old, "      if (chart.__place) chart.__place(Math.min(r.u, ISLANDS.length - 1.0001), r.station);\n")

# each chapter's text side, for the camera's offset (+1 text on the left, -1 on the right)
old = "  world.buildRoute();\n"
assert a.count(old) == 1
a = a.replace(old, "  world.buildRoute();\n  world.sides = ISLANDS.map((s) => {\n    const p = document.querySelector(`.panel[data-island=\"${s.id}\"]`);\n    return p && p.classList.contains('right') ? -1 : 1;\n  });\n")
io.open(app_p, "w", encoding="utf-8").write(a)
print("app ok")
