"""Add the styles for the landing's new parts: the standing call to action in the
header, the hero plaque, and the end of the voyage (call to action, questions,
footer). Same language as the rest: the game's faces, gold, the deep sea."""
import io
import sys

p = sys.argv[1]
s = io.open(p, encoding="utf-8").read()

css = """
/* ---- landing: header call to action ---- */
.masthead .follow{pointer-events:auto; font-size:11px; padding:9px 16px}

/* ---- landing: the hero plaque says what the game is in ten seconds ---- */
.panel.hero{width:min(640px, 56vw)}
.panel.hero h2{font-size:calc(var(--t-h2) * 1.18)}
.panel.hero .act{gap:14px; flex-wrap:wrap}
.panel .act a.ghost{text-decoration:none}
.tally{flex-wrap:wrap}

/* ---- landing: the end of the voyage, in ordinary page flow ---- */
.outro{
  position:relative; z-index:12;
  padding-block:clamp(70px, 12vh, 140px) 40px;
  padding-left:max(16px, env(safe-area-inset-left, 0px));
  padding-right:max(16px, env(safe-area-inset-right, 0px));
  background:linear-gradient(180deg, rgba(6,23,42,0) 0, rgba(6,23,42,.86) 140px, var(--abyss) 320px);
  display:flex; flex-direction:column; align-items:center; gap:clamp(56px, 9vh, 96px);
}
.outro .cta-band{max-width:44rem; text-align:center; display:flex; flex-direction:column; align-items:center}
.outro .cta-band .where{justify-content:center; opacity:1; transform:none}
.outro .cta-band .where::after{display:none}
.outro .cta-band h2{font-size:var(--t-h2); line-height:1.05; margin-bottom:18px}
.outro .cta-band p{color:#e6f1f8; font-size:var(--t-body); max-width:34rem}
.outro .act{display:flex; flex-wrap:wrap; justify-content:center; gap:14px; margin-top:28px; opacity:1; transform:none}
.outro a.plate, .outro a.ghost{text-decoration:none}

.faq{width:min(44rem, 100%); min-width:0}
.faq h3{font-size:11px; letter-spacing:.22em; text-transform:uppercase; color:var(--gold);
  margin-bottom:14px; font-weight:700}
.faq details{border-top:1px solid var(--line)}
.faq details:last-child{border-bottom:1px solid var(--line)}
.faq summary{
  list-style:none; cursor:pointer; padding:18px 36px 18px 0; position:relative;
  font-size:calc(var(--t-body) * 1.12); color:var(--ink);
}
.faq summary::-webkit-details-marker{display:none}
.faq summary::after{
  content:''; position:absolute; right:6px; top:50%; width:9px; height:9px;
  border-right:1.5px solid var(--gold); border-bottom:1.5px solid var(--gold);
  transform:translateY(-70%) rotate(45deg); transition:transform .25s ease;
}
.faq details[open] summary::after{transform:translateY(-30%) rotate(-135deg)}
.faq summary:hover{color:var(--gold)}
.faq details p{color:#cfe0ec; font-size:var(--t-body); line-height:1.6; padding:0 0 20px; max-width:38rem}

.foot{width:min(44rem, 100%); display:flex; flex-direction:column; align-items:center; gap:18px;
  padding-top:28px; border-top:1px solid var(--line); color:var(--mist)}
.foot img{width:120px; opacity:.9}
.foot nav{display:flex; flex-wrap:wrap; justify-content:center; gap:10px 26px}
.foot a{color:var(--mist); text-decoration:none; font-size:11px; letter-spacing:.18em; text-transform:uppercase; font-weight:700}
.foot a:hover{color:var(--gold)}
.foot small{font-size:10px; letter-spacing:.16em; text-transform:uppercase}

/* while the end section is on screen the floating chapter furniture steps aside */
body.at-end .panel, body.at-end .chart, body.at-end .cue{opacity:0 !important; pointer-events:none !important}
.chart{transition:opacity .4s ease}
"""
anchor = "</style>"
i = s.index(anchor)
s = s[:i] + css + s[i:]
io.open(p, "w", encoding="utf-8").write(s)
print("ok")
