"""app.js for the English-only landing: drop the dictionaries and the language
switch, measure the voyage on the scroll track alone (the end section follows it in
ordinary flow), and let the hero's first button go straight into the fight."""
import io
import sys

p = sys.argv[1]
s = io.open(p, encoding="utf-8").read()

a = s.index("/* ----------------------------------------------------------- language */")
b = s.index("/* ----------------------------------------------------------- synergy wall */")
s = s[:a] + ("/* ----------------------------------------------------------- language */\n"
             "// The site is English only; the copy lives in the markup.\n"
             "const lang = 'en';\n"
             "document.documentElement.lang = lang;\n"
             "const retitleWorldLabels = () => {};\n\n") + s[b:]

old = "  function maxScroll() { return Math.max(document.body.scrollHeight - innerHeight, 1); }\n"
new = ("  // the voyage is the scroll track only; the end section (call to action, questions,\n"
       "  // footer) follows it in ordinary page flow with the camera resting on the last island\n"
       "  function maxScroll() { return Math.max(track.offsetHeight - innerHeight, 1); }\n")
if s.count(old) != 1:
    raise SystemExit("maxScroll not found")
s = s.replace(old, new)

old = ("    progress = scrollY / maxScroll();\n"
       "    $('cue').style.opacity = progress > 0.03 ? '0' : '1';\n")
new = ("    progress = Math.min(1, scrollY / maxScroll());\n"
       "    $('cue').style.opacity = progress > 0.03 ? '0' : '1';\n"
       "    document.body.classList.toggle('at-end', scrollY > maxScroll() + innerHeight * 0.12);\n")
if s.count(old) != 1:
    raise SystemExit("onScroll body not found")
s = s.replace(old, new)

old = "  if (sail) sail.addEventListener('click', () => chartGoTo(1));\n"
new = ("  // \"Play in your browser\": sail to the fight and hand over the controls\n"
       "  if (sail) sail.addEventListener('click', () => { chartGoTo(1); setTimeout(enterPlay, reduced ? 0 : 1200); });\n")
if s.count(old) != 1:
    raise SystemExit("sail handler not found")
s = s.replace(old, new)

io.open(p, "w", encoding="utf-8").write(s)
print("ok")
