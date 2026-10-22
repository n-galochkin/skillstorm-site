"""Builds chapter: the wall of combo-title names becomes a diagram of real recipes with the
game's own skill icons (Nikita 2026-10-22: "не текстом показывал, а схемой и с иконками").
Devlog chapter: the copy stops talking about AI (Nikita 2026-10-22: "антимаркетинг")."""
import io
import sys

html_path, app_path = sys.argv[1], sys.argv[2]
s = io.open(html_path, encoding="utf-8").read()


def sk(name, label):
    return (f'<span class="sk"><img src="assets/skills/{name}.webp" alt="" width="160" height="160">'
            f'<b>{label}</b></span>')


def title(name, line, tier):
    return f'<span class="ttl t{tier}"><b>{name}</b><small>{line}</small></span>'


PLUS = '<i class="op">+</i>'
ARROW = '<i class="to" aria-hidden="true"></i>'
rows = [
    sk("blaze", "Blaze") + PLUS + sk("freeze", "Freeze") + ARROW + title("Thermal Shock", "burning and frozen at once: stunned", 2),
    '<span class="sk chip">Thermal Shock</span>' + PLUS + sk("lightning", "Lightning") + ARROW + title("Darkness", "every kill opens a vortex that drags the crowd in", 3),
    sk("executioner", "Executioner") + PLUS + sk("power", "Power") + ARROW + title("Guillotine", "an execution reloads your shot", 2),
]
diagram = ('    <div class="fusion" id="fusion" aria-label="How skills fuse into combo titles">\n'
           + ''.join(f'      <div class="recipe">{r}</div>\n' for r in rows)
           + '    </div>\n')
a = '    <div class="wall" id="wall" aria-label="Combo titles"></div>\n'
assert s.count(a) == 1
s = s.replace(a, diagram)

old_h2 = '    <h2>One developer and a crew of AI agents</h2>\n'
i = s.index(old_h2)
j = s.index('</p>\n', i) + len('</p>\n')
s = s[:i] + ('    <h2>Made by one developer, out in the open</h2>\n'
             '    <p>Every new weapon, boss and bug shows up in a short clip first. Watch the game grow week by week, and tell us what it needs next.</p>\n') + s[j:]

css = """
/* ---- builds: recipes drawn as a diagram, with the game's own skill icons ---- */
.fusion{display:flex; flex-direction:column; gap:12px; margin-top:22px; min-width:0}
.recipe{display:flex; align-items:center; gap:10px; min-width:0; transition:opacity .4s}
.panel.right .recipe{justify-content:flex-end}
.recipe .sk{display:flex; flex-direction:column; align-items:center; gap:4px; flex:none; transition:transform .45s cubic-bezier(.34,1.56,.64,1)}
.recipe .sk img{width:50px; height:50px; clip-path:inset(5% round 14%); filter:drop-shadow(0 3px 4px rgba(0,0,0,.4))}
.recipe .sk b{font-family:var(--ui); font-weight:700; font-size:9.5px; letter-spacing:.1em; text-transform:uppercase; color:var(--mist)}
.recipe .chip{align-self:center; justify-content:center; height:50px; padding:0 12px; border-radius:6px; margin-bottom:17px;
  font-family:var(--ui); font-weight:900; font-size:11px; letter-spacing:.08em; text-transform:uppercase; color:#3a2410;
  background:linear-gradient(180deg,#ffe39a,#e2b04a); box-shadow:0 0 0 1.5px #8a6324}
.recipe .op{font-style:normal; font-family:var(--ui); font-weight:900; font-size:20px; color:var(--gold); margin-bottom:17px}
.recipe .to{width:30px; height:2px; background:var(--gold); position:relative; margin-bottom:17px; flex:none}
.recipe .to::after{content:''; position:absolute; right:-1px; top:-4px; border:5px solid transparent; border-left:7px solid var(--gold); border-right:0}
.recipe .ttl{display:flex; flex-direction:column; gap:3px; min-width:0; padding:8px 12px; border-radius:6px; margin-bottom:17px;
  transition:box-shadow .45s, transform .45s cubic-bezier(.34,1.56,.64,1)}
.recipe .ttl b{font-family:var(--ui); font-weight:900; font-size:14px; letter-spacing:.1em; text-transform:uppercase}
.recipe .ttl small{font-family:var(--voice); font-size:14px; line-height:1.25; color:#e6f1f8}
/* the game's own title colours: gold for a second-tier title, crimson for a third */
.recipe .ttl.t2{background:rgba(242,197,92,.13); box-shadow:inset 0 0 0 1.5px rgba(242,197,92,.7)}
.recipe .ttl.t2 b{color:var(--gold)}
.recipe .ttl.t3{background:rgba(214,62,62,.16); box-shadow:inset 0 0 0 1.5px rgba(232,90,80,.8)}
.recipe .ttl.t3 b{color:#ff8a7a}
.fusion.cycling .recipe{opacity:.55}
.fusion .recipe.lit{opacity:1}
.fusion .recipe.lit .sk:first-child{transform:translateX(6px)}
.fusion .recipe.lit .sk:nth-child(3){transform:translateX(-6px)}
.fusion .recipe.lit .ttl{transform:scale(1.04)}
.fusion .recipe.lit .ttl.t2{box-shadow:inset 0 0 0 1.5px var(--gold), 0 0 22px rgba(242,197,92,.45)}
.fusion .recipe.lit .ttl.t3{box-shadow:inset 0 0 0 1.5px #ff8a7a, 0 0 22px rgba(232,90,80,.45)}
@media (max-width:860px){
  .fusion{gap:8px; margin-top:12px}
  .recipe{gap:6px}
  .recipe .sk img{width:34px; height:34px}
  .recipe .sk b{display:none}
  .recipe .op, .recipe .to, .recipe .ttl, .recipe .chip{margin-bottom:0}
  .recipe .chip{height:34px; padding:0 8px; font-size:9px}
  .recipe .to{width:16px}
  .recipe .ttl{padding:5px 8px}
  .recipe .ttl b{font-size:11px}
  .recipe .ttl small{display:none}
}
"""
a = "</style>"
assert s.count(a) == 1
s = s.replace(a, css + a)
io.open(html_path, "w", encoding="utf-8").write(s)

a = io.open(app_path, encoding="utf-8").read()
w0 = a.index("/* ----------------------------------------------------------- synergy wall */")
w1 = a.index("/* ------------------------------------------------- names on the water */")
a = a[:w0] + a[w1:]
s0 = a.index("  // synergy wall: a slow sweep, so the list reads as alive rather than as a dump\n")
s1 = a.index("  }\n", a.index("    }, 1300);\n", s0)) + len("  }\n")
a = a[:s0] + """  // the builds diagram: the recipes light up one after another, like a fusion in the game
  const fusion = $('fusion');
  if (fusion && !reduced) {
    const rows = [...fusion.querySelectorAll('.recipe')];
    let k = 0;
    fusion.classList.add('cycling');
    const lightNext = () => { rows.forEach((r, i) => r.classList.toggle('lit', i === k % rows.length)); k++; };
    lightNext();
    setInterval(lightNext, 2400);
  }
""" + a[s1:]
a = a.replace("const SYNERGIES = [", "const SYNERGIES_UNUSED = [", 1)
io.open(app_path, "w", encoding="utf-8").write(a)
print("ok")
