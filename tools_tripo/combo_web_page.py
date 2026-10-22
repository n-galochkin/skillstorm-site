"""Builds chapter: the three recipe rows become the combo web (combo_web.js); the camera gets
a wind sway while it holds over an island (Nikita 2026-10-22)."""
import io
import sys

html_p, app_p, world_p = sys.argv[1:4]

s = io.open(html_p, encoding="utf-8").read()
a0 = s.index('    <div class="fusion" id="fusion"')
a1 = s.index('    </div>\n', s.index('</div>\n', a0 + 60) - 10)
# the fusion block ends with its own closing div line after the three recipe rows
end = s.index('    </div>\n', a0) + len('    </div>\n')
s = s[:a0] + '    <div class="web" id="comboWeb"></div>\n' + s[end:]
# the web shows the numbers itself; the tally and the second half of the pitch make room for it
t0 = s.index('    <div class="tally">', s.index('data-island="skills"'))
t1 = s.index('    </div>\n', t0) + len('    </div>\n')
s = s[:t0] + s[t1:]
old = "<p>Every level-up offers three skills. Pick the right pair and they fuse into a combo title &mdash; the game names your build out loud, mid-fight, no menus.</p>"
new = "<p>Every level-up offers three skills. The right pair fuses into a combo title, and titles fuse again into deeper ones: 26 skills, 35 titles.</p>"
assert s.count(old) == 1
s = s.replace(old, new)
css = """
/* ---- builds: the combo web ---- */
.web{margin-top:14px; min-width:0; max-width:460px}
.web svg{display:block; width:100%; height:auto; overflow:visible}
.web .rings circle{fill:none; stroke:rgba(168,195,214,.14); stroke-width:1; stroke-dasharray:2 5}
.web .threads path{fill:none; stroke:rgba(242,197,92,.2); stroke-width:1.2; transition:stroke .3s, opacity .3s}
.web .threads path.t3{stroke:rgba(232,90,80,.26)}
.web svg.focus .threads path{opacity:.35}
.web .threads path.on{opacity:1; stroke:#f2c55c; stroke-width:2.2}
.web .threads path.t3.on{stroke:#ff8a7a}
.web .threads path.flow{stroke-dasharray:6 var(--len); animation:webFlow 1.1s linear 2}
@keyframes webFlow{from{stroke-dashoffset:var(--len)}to{stroke-dashoffset:0}}
.web .node{cursor:pointer; outline:none; transition:opacity .3s}
.web .node image{transition:transform .35s cubic-bezier(.34,1.56,.64,1); transform-box:fill-box; transform-origin:center}
.web .node .halo{fill:transparent; transition:fill .3s}
.web svg.focus .node{opacity:.38}
.web .node.on{opacity:1}
.web .node.on .halo{fill:rgba(242,197,92,.22)}
.web .node.k3.on .halo{fill:rgba(232,90,80,.3)}
.web .node.lead image{transform:scale(1.22)}
.web .node.lead .halo{fill:rgba(242,197,92,.45)}
.web .node.k3.lead .halo{fill:rgba(232,90,80,.55)}
.web-cap{min-height:58px; margin-top:6px; display:flex; flex-direction:column; gap:4px}
.web-cap b{font-family:var(--ui); font-weight:900; font-size:14px; letter-spacing:.12em; text-transform:uppercase}
.web-cap b.k2{color:var(--gold)} .web-cap b.k3{color:#ff8a7a} .web-cap b.ks{color:var(--ink)}
.web-cap .rec{display:flex; flex-wrap:wrap; align-items:center; gap:4px 8px; font-family:var(--ui); font-weight:700; font-size:10.5px; letter-spacing:.08em; text-transform:uppercase; color:var(--mist)}
.web-cap .rec i{font-style:normal; display:inline-flex; align-items:center; gap:5px}
.web-cap .rec img{width:20px; height:20px}
.web-cap .rec em{font-style:normal; color:var(--gold)}
.web-cap .tw, .web-cap span:not(.rec){font-family:var(--voice); font-size:15px; color:#e6f1f8}
@media (max-width:860px){
  .panel[data-island="skills"] .web{grid-column:1 / -1; max-width:none; margin-top:8px}
  .web-cap{min-height:46px}
  .web-cap .tw{font-size:14px}
}
"""
a = "</style>"
assert s.count(a) == 1
s = s.replace(a, css + a)
io.open(html_p, "w", encoding="utf-8").write(s)

a = io.open(app_p, encoding="utf-8").read()
a = a.replace("import { Fight } from './fight.js';\n", "import { Fight } from './fight.js';\nimport { buildWeb } from './combo_web.js';\n", 1)
f0 = a.index("  // the builds diagram: the recipes light up one after another, like a fusion in the game\n")
f1 = a.index("    setInterval(lightNext, 2400);\n  }\n", f0) + len("    setInterval(lightNext, 2400);\n  }\n")
a = a[:f0] + "  // the builds chapter: every skill and title and how they fuse\n  buildWeb($('comboWeb'));\n" + a[f1:]
io.open(app_p, "w", encoding="utf-8").write(a)

w = io.open(world_p, encoding="utf-8").read()
old = """    const sway = r.moving ? 0 : 1;
    pos.x += Math.sin(elapsed * 0.17) * 2.4 * sway;
    pos.z += Math.cos(elapsed * 0.13) * 1.7 * sway;
    pos.y += Math.sin(elapsed * 0.21) * 1.0;
    this.camera.position.copy(pos);
    this.camera.lookAt(look);
"""
new = """    // holding over an island the camera hangs in the wind like a drone: a slow drift, a
    // gentle roll, and now and then a gust that leans it a little further. Several unrelated
    // sines, so the motion never repeats and never reads as a loop.
    this.holdSway = THREE.MathUtils.damp(this.holdSway || 0, r.moving ? 0 : 1, 1.6, 1 / 60);
    const sway = this.holdSway;
    const gust = Math.max(0, Math.sin(elapsed * 0.31) * Math.sin(elapsed * 0.113 + 1.3)) ** 2;
    pos.x += (Math.sin(elapsed * 0.17) * 3.2 + Math.sin(elapsed * 0.53 + 2) * 0.9 + gust * 4.5) * sway;
    pos.z += (Math.cos(elapsed * 0.13) * 2.4 + Math.sin(elapsed * 0.41) * 0.7) * sway;
    pos.y += Math.sin(elapsed * 0.21) * 1.4 + Math.sin(elapsed * 0.67 + 1) * 0.5 * sway;
    look.x += (Math.sin(elapsed * 0.11 + 0.7) * 1.6 + gust * 1.5) * sway;
    look.z += Math.cos(elapsed * 0.09 + 0.3) * 1.2 * sway;
    this.camera.position.copy(pos);
    this.camera.lookAt(look);
    this.camera.rotateZ((Math.sin(elapsed * 0.23) * 0.55 + Math.sin(elapsed * 0.61 + 0.4) * 0.2 + gust * 0.6) * sway * Math.PI / 180);
"""
assert w.count(old) == 1
w = w.replace(old, new)
io.open(world_p, "w", encoding="utf-8").write(w)
print("ok")
