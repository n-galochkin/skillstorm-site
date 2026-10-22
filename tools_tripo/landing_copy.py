"""Rewrite the site's copy as an English-only landing page.

Structure (from the landing research, proposals/site-landing.md): a hero with the
hook and the calls to action, short chapter plaques on the islands, then the end
of the voyage in ordinary page flow: a call to action, questions, a footer."""
import io
import re
import sys

p = sys.argv[1]
s = io.open(p, encoding="utf-8").read()

s = s.replace("<title>Skillstorm</title>\n",
 "<title>Skillstorm</title>\n"
 '<meta name="description" content="Skillstorm is an Archero-style auto-battle royale roguelite for PC and Android: you steer, your weapon fires on its own, the storm closes in, and the last one standing takes the island.">\n'
 '<meta property="og:title" content="Skillstorm — the auto-battle royale roguelite">\n'
 '<meta property="og:description" content="Land with nothing. Build your run mid-fight. Be the last one standing and the island is yours.">\n', 1)

lang_start = s.index('  <div class="lang" role="group" aria-label="Language">')
lang_end = s.index("</header>")
s = s[:lang_start] + ('  <a class="ghost follow" href="https://www.youtube.com/@NikitaGalochkin" '
                      'target="_blank" rel="noopener">Follow the devlog</a>\n') + s[lang_end:]

YT = "https://www.youtube.com/@NikitaGalochkin"
TT = "https://www.tiktok.com/@solodevich"
IG = "https://www.instagram.com/your_sillity/"

panels = f'''<div class="panels" id="panels">

  <article class="panel left hero" data-island="landing">
    <p class="where ui"><span>Auto-battle royale roguelite</span></p>
    <h2>Land with nothing.<br>Leave the last one standing.</h2>
    <p>You steer &mdash; your weapon fires on its own. Ten to fifteen rivals, a storm closing in, six-minute matches, and the island goes to whoever is left.</p>
    <div class="act">
      <button class="plate" id="sailBtn">Play in your browser</button>
      <a class="ghost" href="{YT}" target="_blank" rel="noopener">Follow development</a>
    </div>
    <div class="facts ui">
      <span>PC (Steam) &amp; Android</span>
      <span>5&ndash;8 minute matches</span>
      <span>In development</span>
    </div>
  </article>

  <article class="panel right" data-island="combat">
    <span class="watermark">FIGHT</span>
    <p class="where ui"><span>How it plays</span></p>
    <h2>Move to live.<br>Stand still to strike.</h2>
    <p>You only steer. Stop and your weapon fires by itself; move and it holds. Every fight is the same choice: finish the kill, or get out of the arrows.</p>
    <p>Below is a live fight on the game&rsquo;s own models, running in your browser.</p>
    <div class="act">
      <button class="plate" id="playBtn">Take control</button>
      <span class="hint ui">WASD or drag</span>
    </div>
  </article>

  <article class="panel left" data-island="skills">
    <span class="watermark">BUILDS</span>
    <p class="where ui"><span>Builds</span></p>
    <h2>Two skills fuse into a title</h2>
    <p>Every level-up offers three skills. Pick the right pair and they fuse into a combo title &mdash; the game names your build out loud, mid-fight, no menus.</p>
    <div class="tally">
      <div><b>28</b><span>skills</span></div>
      <div><b>35</b><span>combo titles</span></div>
      <div><b>12</b><span>weapon types</span></div>
    </div>
    <div class="wall" id="wall" aria-label="Combo titles"></div>
  </article>

  <article class="panel right" data-island="storm">
    <span class="watermark">STORM</span>
    <p class="where ui"><span>The zone</span></p>
    <h2>The storm picks the battlefield</h2>
    <p>Fog and lightning eat the island&rsquo;s edge and the circle keeps closing. Roaming bosses and mob packs guard the best loot, so the middle of a match never goes quiet.</p>
  </article>

  <article class="panel left" data-island="forge">
    <span class="watermark">FORGE</span>
    <p class="where ui"><span>Between runs</span></p>
    <h2>From a linen shirt to king of the archipelago</h2>
    <p>Every island you take pays out: resources, gear, rare finds. Forge your weapon, complete your armour, sail for meaner islands. The kingdom you build is yours alone.</p>
    <div class="shots">
      <img src="assets/ui-map.webp" alt="Map of holdings" width="560" height="995" loading="lazy">
      <img src="assets/ui-forge.webp" alt="The forge" width="560" height="995" loading="lazy">
      <img src="assets/ui-equipment.webp" alt="Equipment" width="560" height="995" loading="lazy">
    </div>
    <p class="note">Screens from the current build</p>
  </article>

  <article class="panel right" data-island="devlog">
    <span class="watermark">DEVLOG</span>
    <p class="where ui"><span>Built in the open</span></p>
    <h2>One developer and a crew of AI agents</h2>
    <p>Code, tests, armour fitting and clip editing run in parallel sessions. The whole build is shared as it happens.</p>
    <div class="clip">
      <video src="assets/devlog-clip.mp4" poster="assets/devlog-poster.webp" muted loop playsinline controls preload="none" width="540" height="960"></video>
    </div>
    <div class="links">
      <a href="{YT}" target="_blank" rel="noopener"><b>YouTube</b><span>@NikitaGalochkin</span></a>
      <a href="{TT}" target="_blank" rel="noopener"><b>TikTok</b><span>@solodevich</span></a>
      <a href="{IG}" target="_blank" rel="noopener"><b>Instagram</b><span>@your_sillity</span></a>
    </div>
  </article>
</div>

'''
start = s.index('<div class="panels" id="panels">')
end = s.index('<aside class="chart">')
s = s[:start] + panels + s[end:]

outro = f'''
<section class="outro" id="outro">
  <div class="cta-band">
    <p class="where ui"><span>Coming to PC and Android</span></p>
    <h2>Be there when the boats land</h2>
    <p>Skillstorm is in development. Follow the devlog to hear first about the Steam page and the demo.</p>
    <div class="act">
      <a class="plate" href="{YT}" target="_blank" rel="noopener">YouTube</a>
      <a class="ghost" href="{TT}" target="_blank" rel="noopener">TikTok</a>
      <a class="ghost" href="{IG}" target="_blank" rel="noopener">Instagram</a>
    </div>
  </div>

  <div class="faq">
    <h3 class="ui">Questions</h3>
    <details><summary>When does it come out?</summary>
      <p>There is no date yet. Next come a Steam page and a playable demo; follow the devlog to catch both.</p></details>
    <details><summary>Which platforms?</summary>
      <p>PC through Steam, and Android. One game, one progression, controls made for each.</p></details>
    <details><summary>How much will it cost?</summary>
      <p>On PC, early access at a modest price. On Android, free to play &mdash; with no pay-to-win.</p></details>
    <details><summary>Is it PvP?</summary>
      <p>No, and we say so plainly: your rivals are bots that play like people, with names, builds and gear of their own. That means no queues and no cheaters &mdash; a match starts the moment you want one.</p></details>
    <details><summary>What does &ldquo;auto-battle&rdquo; mean here?</summary>
      <p>Archero-style: your character attacks on its own; you control movement and choose skills on level-up. It is not a unit-placing autobattler.</p></details>
    <details><summary>Can I play with friends?</summary>
      <p>Each player builds a kingdom of their own, and friends are allies. Shared runs are planned.</p></details>
  </div>

  <footer class="foot ui">
    <img src="assets/logo.webp" alt="Skillstorm" width="900" height="233">
    <nav>
      <a href="{YT}" target="_blank" rel="noopener">YouTube</a>
      <a href="{TT}" target="_blank" rel="noopener">TikTok</a>
      <a href="{IG}" target="_blank" rel="noopener">Instagram</a>
    </nav>
    <small>&copy; 2026 Skillstorm &middot; in development &middot; no release date yet</small>
  </footer>
</section>
'''
s = s.replace('<div id="track"></div>\n', '<div id="track"></div>\n' + outro, 1)

reps = {
    '<span data-i="chart.h">Архипелаг</span>': "<span>Archipelago</span>",
    'data-i="play.exit">Выйти</button>': ">Leave</button>",
    'data-i="end.again">Ещё раз</button>': ">Again</button>",
    '<span class="ui" data-i="cue">Листай</span>': '<span class="ui">Scroll</span>',
    '<small id="bootText" data-i="boot.load">Поднимаем паруса…</small>': '<small id="bootText">Raising sail…</small>',
}
for a, b in reps.items():
    if s.count(a) != 1:
        raise SystemExit("not found once: " + a)
    s = s.replace(a, b)

io.open(p, "w", encoding="utf-8").write(s)
body = s[s.index("<canvas"):]
print("ok; cyrillic left in body:", re.findall(r"[А-Яа-яЁё]{3,}", body)[:12])
