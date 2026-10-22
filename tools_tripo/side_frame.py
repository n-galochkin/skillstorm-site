"""The island stands beside its chapter's text, not under it (Nikita 2026-10-22: "камеру на
острова сдвинуть относительно текста: суть правее или левее, для мобилок сверху или снизу").
A wide screen slides the frame sideways toward the free side; a tall one keeps its lift."""
import io
import sys

world_p, app_p, cloud_p = sys.argv[1], sys.argv[2], sys.argv[3]

w = io.open(world_p, encoding="utf-8").read()
old = """    const lift = this.liftFrame !== false && w / h < 0.8 ? 0.22 : 0;
    if (lift) this.camera.setViewOffset(w, h, 0, h * lift, w, h);
    else this.camera.clearViewOffset();
    this.camera.updateProjectionMatrix();
    if (this.focusY) this.focusY.value = 0.53 - lift;
    if (this.cloudBank) {
      this.cloudBank.focusY = lift * 2;
      this.cloudBank.textTop = lift ? 0.2 : null;
    }
  }
"""
new = """    const lift = this.liftFrame !== false && w / h < 0.8 ? 0.22 : 0;
    // on a wide screen the chapter's text takes one side: the frame slides so the island
    // stands on the other (side +1 = text on the left, island to the right)
    const across = tall ? 0 : (this.side || 0) * 0.2;
    if (lift || Math.abs(across) > 1e-4) this.camera.setViewOffset(w, h, -across * w, h * lift, w, h);
    else this.camera.clearViewOffset();
    this.camera.updateProjectionMatrix();
    if (this.focusY) this.focusY.value = 0.53 - lift;
    if (this.cloudBank) {
      this.cloudBank.focusY = lift * 2;
      this.cloudBank.focusX = across * 2;
      this.cloudBank.textTop = lift ? 0.2 : null;
    }
  }

  /* where the chapter's text is: +1 left, -1 right, 0 none (the fight). The frame
     glides there in tick(), so a chapter change never jumps the picture. */
  setTextSide(side) { this.sideTarget = side; }
"""
assert w.count(old) == 1
w = w.replace(old, new)
old = "  tick(dt, elapsed, state) {\n"
new = ("  tick(dt, elapsed, state) {\n"
       "    if (this.size && this.sideTarget !== undefined && Math.abs((this.side || 0) - this.sideTarget) > 1e-3) {\n"
       "      this.side = THREE.MathUtils.damp(this.side || 0, this.sideTarget, 2.6, dt);\n"
       "      this.frameFor(this.size[0], this.size[1]);\n"
       "    }\n")
assert w.count(old) == 1
w = w.replace(old, new)
io.open(world_p, "w", encoding="utf-8").write(w)

a = io.open(app_p, encoding="utf-8").read()
old = "        if (shown) document.body.classList.toggle('text-right', shown.classList.contains('right'));\n"
new = ("        if (shown) document.body.classList.toggle('text-right', shown.classList.contains('right'));\n"
       "        // and the island steps aside to the side the text leaves free\n"
       "        if (shown) world.setTextSide(shown.classList.contains('right') ? -1 : 1);\n")
assert a.count(old) == 1
a = a.replace(old, new)
old = "    world.setLift(false);\n"
assert a.count(old) == 1
a = a.replace(old, "    world.setLift(false);\n    world.setTextSide(0);\n")
old = "    world.setLift(true);\n"
assert a.count(old) == 1
a = a.replace(old, "    world.setLift(true);\n    shownIsland = null;    // the next frame puts the chapter's text, and the island's side, back\n")
io.open(app_p, "w", encoding="utf-8").write(a)

c = io.open(cloud_p, encoding="utf-8").read()
old = "    this.focusY = 0;            // where the subject sits on screen, -1..1 (lifted on a tall screen)\n"
assert c.count(old) == 1
c = c.replace(old, old + "    this.focusX = 0;            // and across: slid aside from the chapter's text on a wide screen\n")
old = "Math.hypot(this._v.x * Math.min(1, camera.aspect), (this._v.y - this.focusY) * 1.2)"
assert c.count(old) == 1
c = c.replace(old, "Math.hypot((this._v.x - this.focusX) * Math.min(1, camera.aspect), (this._v.y - this.focusY) * 1.2)")
io.open(cloud_p, "w", encoding="utf-8").write(c)
print("ok")
