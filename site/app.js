/* Wiring: scroll sails the camera, each island shows its panel, the second one
   hands over the controls. */
import * as THREE from 'three';
import { World, LIGHT } from './world.js';
import { Fight } from './fight.js';
import { buildWeb } from './combo_web.js';
import { ISLANDS, ISLETS } from './archipelago.js';

const $ = (id) => document.getElementById(id);
const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;

/* ----------------------------------------------------------- language */
// The site is English only; the copy lives in the markup.
const lang = 'en';
document.documentElement.lang = lang;

/* ------------------------------------------------- names on the water */
const worldLabels = new Map();
function buildWorldLabels() {
  const host = document.getElementById('worldLabels');
  for (const isle of ISLANDS) {
    const el = document.createElement('span');
    el.className = 'worldlabel';
    el.textContent = (isle.name[lang] || isle.name.ru).toUpperCase();
    el.dataset.island = isle.id;
    host.appendChild(el);
    worldLabels.set(isle.id, el);
  }
}
function retitleWorldLabels() {
  for (const isle of ISLANDS) {
    const el = worldLabels.get(isle.id);
    if (el) el.textContent = (isle.name[lang] || isle.name.ru).toUpperCase();
  }
}

/* ----------------------------------------------------------- the chart */
/* The voyage drawn as an old sea chart on a torn scrap of parchment: the chapter
   islands and the islets around them inked schematically with water lines off their
   coasts, the route a curved red line - solid where the ship has been, dashed ahead -
   and a little ship where the camera is. The layout is a sketch, not a survey: the
   storm island far to the north is pulled in so the whole route fits. */
let chartGoTo = () => {};
function drawChart() {
  const svg = $('chartSvg');
  const W = 300, H = 176;
  // pull far islands in: past 200 m the distance counts for a sixth
  const squeeze = (v) => (Math.abs(v) <= 200 ? v : Math.sign(v) * (200 + (Math.abs(v) - 200) / 10));
  const chapters = ISLANDS.map((i) => [i.pos[0], squeeze(i.pos[1])]);
  const minX = Math.min(...chapters.map((c) => c[0])) - 40, maxX = Math.max(...chapters.map((c) => c[0])) + 40;
  const minZ = Math.min(...chapters.map((c) => c[1])) - 30, maxZ = Math.max(...chapters.map((c) => c[1])) + 30;
  // a sketch, not a survey: the route fills the sheet both ways
  const kx = (W - 56) / (maxX - minX), kz = (H - 62) / (maxZ - minZ), k = Math.sqrt(kx * kz);
  const sx = (x) => 28 + (x - minX) * kx;
  const sy = (z) => 36 + (squeeze(z) - minZ) * kz;

  let seed = 11;
  const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
  // an island as a hand-drawn coast: a wobbling closed curve, the same wobble at every size
  const coast = (cx, cy, r, ph, grow = 1) => {
    const n = 14, pts = [];
    for (let i = 0; i < n; i++) {
      const a = (i / n) * Math.PI * 2;
      const w = (0.74 + 0.26 * Math.sin(a * 2 + ph) + 0.18 * Math.sin(a * 5 + ph * 2)) * grow;
      pts.push([cx + Math.cos(a) * r * w, cy + Math.sin(a) * r * w * 0.78]);
    }
    let d = '';
    for (let i = 0; i < n; i++) {   // smooth through the points (Catmull-Rom as cubic Beziers)
      const p0 = pts[(i - 1 + n) % n], p1 = pts[i], p2 = pts[(i + 1) % n], p3 = pts[(i + 2) % n];
      if (!i) d += `M${p1[0].toFixed(1)} ${p1[1].toFixed(1)}`;
      d += `C${(p1[0] + (p2[0] - p0[0]) / 6).toFixed(1)} ${(p1[1] + (p2[1] - p0[1]) / 6).toFixed(1)},`
        + `${(p2[0] - (p3[0] - p1[0]) / 6).toFixed(1)} ${(p2[1] - (p3[1] - p1[1]) / 6).toFixed(1)},`
        + `${p2[0].toFixed(1)} ${p2[1].toFixed(1)}`;
    }
    return d + 'Z';
  };
  // the parchment: a torn outline with an uneven edge
  const p = [];
  for (let x = 4; x < W - 4; x += 10 + rnd() * 9) p.push([x, 3 + rnd() * 5]);
  for (let y = 12; y < H - 10; y += 10 + rnd() * 8) p.push([W - 3 - rnd() * 5, y]);
  for (let x = W - 4; x > 4; x -= 10 + rnd() * 9) p.push([x, H - 3 - rnd() * 5]);
  for (let y = H - 12; y > 10; y -= 10 + rnd() * 8) p.push([3 + rnd() * 5, y]);
  const edge = 'M' + p.map(([x, y]) => `${x.toFixed(1)} ${y.toFixed(1)}`).join(' L') + 'Z';

  let html = `<defs>
    <radialGradient id="chartPaper" cx="45%" cy="40%" r="75%">
      <stop offset="0" stop-color="#f6e9c8"/><stop offset=".7" stop-color="#e8d4a6"/><stop offset="1" stop-color="#cdb07a"/></radialGradient>
    <radialGradient id="chartStain" r=".5"><stop offset="0" stop-color="#a77c3c" stop-opacity=".2"/><stop offset="1" stop-color="#a77c3c" stop-opacity="0"/></radialGradient>
    <clipPath id="chartClip"><path d="${edge}"/></clipPath>
  </defs>
  <path d="${edge}" fill="url(#chartPaper)" stroke="#8c6a35" stroke-width="1.2" stroke-linejoin="round"/>
  <g clip-path="url(#chartClip)">
    <ellipse cx="${W * 0.78}" cy="${H * 0.3}" rx="60" ry="40" fill="url(#chartStain)"/>
    <ellipse cx="${W * 0.18}" cy="${H * 0.8}" rx="70" ry="44" fill="url(#chartStain)"/>`;

  // sea: a few wave marks
  for (let i = 0; i < 16; i++) {
    const x = 20 + rnd() * (W - 40), y = 34 + rnd() * (H - 46);
    html += `<path d="M${x.toFixed(1)} ${y.toFixed(1)} q3 -2.4 6 0 t6 0" fill="none" stroke="#7a8f8a" stroke-width=".7" opacity=".55"/>`;
  }
  // the islets: small inked shapes, no names
  for (const isle of ISLETS) {
    const z = squeeze(isle.pos[1]);
    if (isle.pos[0] < minX || isle.pos[0] > maxX || z < minZ || z > maxZ) continue;
    // the islets stay small and pale, so the chapter islands read first
    const r = Math.min(4.2, Math.max(1.3, isle.radius * k * 0.32));
    html += `<path d="${coast(sx(isle.pos[0]), sy(isle.pos[1]), r, rnd() * 6.28)}" fill="#d6cb98" stroke="#7a5a30" stroke-width=".55" opacity=".85"/>`;
  }
  // the route: a smooth curve through the chapter islands, one path per leg
  const P = ISLANDS.map((i) => [sx(i.pos[0]), sy(i.pos[1])]);
  const legs = [];
  for (let i = 0; i < P.length - 1; i++) {
    const p0 = P[Math.max(0, i - 1)], p1 = P[i], p2 = P[i + 1], p3 = P[Math.min(P.length - 1, i + 2)];
    const c1 = [p1[0] + (p2[0] - p0[0]) / 5, p1[1] + (p2[1] - p0[1]) / 5];
    const c2 = [p2[0] - (p3[0] - p1[0]) / 5, p2[1] - (p3[1] - p1[1]) / 5];
    legs.push(`M${p1[0].toFixed(1)} ${p1[1].toFixed(1)} C${c1[0].toFixed(1)} ${c1[1].toFixed(1)},${c2[0].toFixed(1)} ${c2[1].toFixed(1)},${p2[0].toFixed(1)} ${p2[1].toFixed(1)}`);
  }
  html += legs.map((d) => `<path d="${d}" fill="none" stroke="#a23a22" stroke-width="1.3" stroke-dasharray="3.2 3.2" stroke-linecap="round" opacity=".75"/>`).join('');
  html += legs.map((d) => `<path class="sailed" d="${d}" fill="none" stroke="#a23a22" stroke-width="1.8" stroke-linecap="round"/>`).join('');

  // the chapter islands: water lines off the coast, a washed land fill, a name in ink.
  // Each name tries below, above, right and left of its island and takes the first place
  // that stays on the sheet and clear of the other names and islands.
  const R = ISLANDS.map((isle) => 7 + Math.min(isle.radius, 130) * 0.06);
  const boxes = P.map(([x, y], i) => [x - R[i] - 2, y - R[i] - 2, x + R[i] + 2, y + R[i] + 2]);
  boxes.push([W - 46, H - 54, W - 10, H - 14]);   // the compass rose
  const clear = (b) => b[0] > 8 && b[2] < W - 8 && b[1] > 30 && b[3] < H - 6
    && boxes.every((o) => b[2] < o[0] || b[0] > o[2] || b[3] < o[1] || b[1] > o[3]);
  ISLANDS.forEach((isle, i) => {
    const [x, y] = P[i];
    const r = R[i];
    const ph = rnd() * 6.28;
    const tw = isle.name[lang].length * 5.4, th = 11;
    const spots = [
      [x, y + r + 12, 'middle'], [x, y - r - 6, 'middle'],
      [x + r + 5, y + 4, 'start'], [x - r - 5, y + 4, 'end'],
    ];
    const boxOf = ([tx, ty, a]) => {
      const x0 = a === 'middle' ? tx - tw / 2 : a === 'start' ? tx : tx - tw;
      return [x0, ty - th + 2, x0 + tw, ty + 2];
    };
    const spot = spots.find((sp) => clear(boxOf(sp))) || spots[0];
    boxes.push(boxOf(spot));
    const [tx, ty, anchor] = spot;
    html += `<g class="dot" data-i="${i}">
      <path d="${coast(x, y, r, ph, 1.6)}" fill="none" stroke="#6f8b88" stroke-width=".5" stroke-dasharray="1.5 2" opacity=".7"/>
      <path d="${coast(x, y, r, ph, 1.3)}" fill="none" stroke="#6f8b88" stroke-width=".6" opacity=".85"/>
      <path class="land" d="${coast(x, y, r, ph)}" fill="#b9b06e" stroke="#4a3216" stroke-width="1.1"/>
      <circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${(r + 8).toFixed(1)}" fill="transparent"/>
      <text x="${tx.toFixed(1)}" y="${ty.toFixed(1)}" text-anchor="${anchor}">${isle.name[lang]}</text>
    </g>`;
  });

  // compass rose and the title, in the same ink
  html += `<g transform="translate(${W - 28},${H - 32})">
      <circle r="11" fill="none" stroke="#5a3e1c" stroke-width=".6"/><circle r="7" fill="none" stroke="#5a3e1c" stroke-width=".4" stroke-dasharray="1 1.6"/>
      <path d="M0 -15 L2.6 0 L0 3 L-2.6 0Z" fill="#a23a22"/><path d="M0 15 L2.6 0 L0 -3 L-2.6 0Z" fill="#5a3e1c"/>
      <path d="M-15 0 L0 -2 L15 0 L0 2Z" fill="#5a3e1c" opacity=".55"/>
      <text y="-18" text-anchor="middle" class="n">N</text></g>
    <text x="16" y="22" class="title">The Archipelago</text>
    <path d="M16 26 Q60 23 112 26" fill="none" stroke="#5a3e1c" stroke-width=".7"/>
  </g>`;

  // the ship: hull, sail and a pennant, nose up; the loop turns it along the route
  html += `<g id="chartHere"><path d="M-5.5 2 Q0 9 5.5 2 Z" fill="#5a3e1c"/><path d="M0 -9 V4" stroke="#3a2610" stroke-width="1"/>
      <path d="M.7 -8 Q7 -3 .7 2 Z" fill="#fff6e2" stroke="#3a2610" stroke-width=".55"/>
      <path d="M0 -9 l4.5 -1.5 l-4.5 -1.3" fill="#a23a22"/></g>`;
  svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
  svg.innerHTML = html;
  svg.querySelectorAll('.dot').forEach((g) => {
    g.addEventListener('click', () => chartGoTo(Number(g.dataset.i)));
  });

  // where the ship is: u runs 0..islands-1 along the route; the leg behind it is inked solid
  const legEls = [...svg.querySelectorAll('.sailed')];
  const lens = legEls.map((el) => el.getTotalLength());
  legEls.forEach((el, i) => { el.style.strokeDasharray = `${lens[i]} ${lens[i]}`; });
  const ship = svg.querySelector('#chartHere');
  svg.__place = (u, station) => {
    const i = Math.min(Math.floor(u), legEls.length - 1), f = Math.min(1, Math.max(0, u - i));
    legEls.forEach((el, j) => { el.style.strokeDashoffset = j < i ? 0 : j > i ? lens[j] : lens[j] * (1 - f); });
    const L = lens[i] * f;
    const a = legEls[i].getPointAtLength(L);
    const b = legEls[i].getPointAtLength(Math.min(lens[i], L + 2));
    const c = legEls[i].getPointAtLength(Math.max(0, L - 2));
    const head = Math.atan2(b.y - c.y, b.x - c.x);
    ship.setAttribute('transform', `translate(${a.x.toFixed(1)},${a.y.toFixed(1)}) rotate(${(head * 180 / Math.PI + 90).toFixed(1)})`);
    svg.querySelectorAll('.dot').forEach((g, j) => g.classList.toggle('here', j === station));
  };
  svg.__place(0, 0);
}
drawChart();

/* ----------------------------------------------------------- boot */
async function boot() {
  const canvas = $('sea');
  const bootEl = $('boot');
  const bar = $('bootBar');

  let world;
  try {
    world = await new World(canvas).init();
  } catch (err) {
    $('bootText').textContent = lang === 'en' ? 'The scene could not start' : 'Сцену не удалось запустить';
    console.error(err);
    return;
  }

  await world.load((f) => { bar.style.width = Math.round(f * 100) + '%'; });
  world.build(lang);
  buildWorldLabels();
  world.buildRoute();

  const islandSpec = ISLANDS.find((i) => i.arena);
  // the fight stands on the flattest dry ground of its island, not at the centre,
  // which on a generated island can be a mesa or a lagoon
  const combatSpec = islandSpec.arenaPos
    ? { ...islandSpec, pos: islandSpec.arenaPos, radius: islandSpec.arenaRadius / 0.66 }
    : islandSpec;
  const fight = new Fight(world, world.assets, combatSpec);
  fight.spawn(5);

  bootEl.classList.add('gone');
  setTimeout(() => { bootEl.hidden = true; }, 900);

  /* ---- scroll track ---- */
  const n = ISLANDS.length;
  const TOTAL = n * 1.0 + (n - 1) * 1.45;
  const track = $('track');
  const unitVh = LIGHT ? 48 : 58;
  track.style.height = (TOTAL * unitVh) + 'vh';

  let progress = 0;
  let playing = false;
  let lockY = 0;

  // the voyage is the scroll track only; the end section (call to action, questions,
  // footer) follows it in ordinary page flow with the camera resting on the last island
  function maxScroll() { return Math.max(track.offsetHeight - innerHeight, 1); }

  /* ---- chapter paging ----
     One flick of the wheel, one swipe or one key press sails to the next island:
     nobody should have to roll the wheel through the whole crossing. The voyage
     pages chapter by chapter; past the last island the page scrolls as usual
     (call to action, questions, footer), and rolling back up from there lands on
     the last island again. */
  // the cover is the top of the page itself; every other island is held mid-stop
  const holdTop = (index) => (index ? ((index * 2.45 + 0.5) / TOTAL) * maxScroll() : 0);
  const chapterAt = (y) => {
    let best = 0;
    for (let i = 1; i < n; i++) if (Math.abs(holdTop(i) - y) < Math.abs(holdTop(best) - y)) best = i;
    return best;
  };
  /* The page moves on a spring, not a timed tween: the first touch of the wheel already
     gives it a push in that direction (so the visitor sees at once that it took), and the
     spring then carries it on to the next island and settles there. A finger drags the
     page like a rubber band; letting go either sails on or springs back. */
  const W = 3.9;                // spring stiffness: about 1.7 s, long enough for a manoeuvre to read
  let sailing = null;           // { to } while the page is gliding
  let pos = 0, vel = 0;
  let quietUntil = 0;           // a trackpad keeps sending wheel events after a flick
  let lastWheel = 0;

  function glide(now, last) {
    if (!sailing) return;
    const dt = Math.min(0.05, (now - last) / 1000);
    const acc = W * W * (sailing.to - pos) - 2 * W * vel;   // critically damped: no overshoot
    vel += acc * dt;
    pos += vel * dt;
    if (Math.abs(sailing.to - pos) < 0.6 && Math.abs(vel) < 8) {
      pos = sailing.to; scrollTo(0, pos); sailing = null; vel = 0;
      quietUntil = performance.now() + 250;
      return;
    }
    scrollTo(0, pos);
    requestAnimationFrame((t) => glide(t, now));
  }

  function sailTo(index, kick = 0) {
    index = THREE.MathUtils.clamp(index, 0, n - 1);
    const to = holdTop(index);
    if (reduced) { scrollTo(0, to); return; }
    if (!sailing) { pos = scrollY; vel = 0; }
    const dist = to - pos;
    // the push points at the target and never outruns what the spring can stop without overshoot
    if (kick) vel = Math.sign(dist) * Math.min(Math.abs(kick), Math.abs(dist) * W * 0.9);
    const was = sailing;
    sailing = { to, index };
    if (!was) { const t = performance.now(); requestAnimationFrame((now) => glide(now, t)); }
  }
  chartGoTo = (index) => sailTo(index);

  // inside the voyage, or in the first few pixels past it when heading back up
  const inVoyage = (dir) => scrollY < maxScroll() - 2 || (dir < 0 && scrollY <= maxScroll() + innerHeight * 0.15);
  // the island the page is at or heading to
  const current = () => (sailing ? sailing.index : chapterAt(Math.min(scrollY, maxScroll())));
  function page(dir, kick) {
    const here = current();
    if (!sailing && dir > 0 && here === n - 1 && scrollY >= holdTop(n - 1) - 2) return false;   // on into the end section
    if (dir < 0 && scrollY > maxScroll() + 2) { sailTo(n - 1, kick); return true; }
    const y = sailing ? sailing.to : scrollY;
    const target = dir > 0 ? (y < holdTop(here) - 2 ? here : here + 1) : (y > holdTop(here) + 2 ? here : here - 1);
    sailTo(target, kick);
    return true;
  }

  addEventListener('wheel', (e) => {
    if (playing || e.ctrlKey) return;
    const dir = Math.sign(e.deltaY);
    if (!dir || !inVoyage(dir)) return;
    const now = performance.now();
    // only the first event of a gesture turns the page; the rest of it (a trackpad's long
    // tail, a wheel's extra notches) is swallowed. Another gesture while gliding goes one further.
    const fresh = now - lastWheel > 220;
    lastWheel = now;
    if (!fresh || now < quietUntil) { e.preventDefault(); return; }
    const px = Math.abs(e.deltaY) * (e.deltaMode === 1 ? 32 : 1);
    if (page(dir, 420 + Math.min(px, 120) * 6)) e.preventDefault();
  }, { passive: false });

  // touch: the page follows the finger (a little stiffer than the finger), then sails or springs back
  let touchY = null, touchFrom = 0, touchLastY = 0, touchLastT = 0, touchV = 0, dragging = false;
  addEventListener('touchstart', (e) => {
    if (playing) { touchY = null; return; }
    touchY = touchLastY = e.touches[0].clientY; touchLastT = performance.now(); touchV = 0;
    touchFrom = scrollY; dragging = false;
    if (sailing) { sailing = null; vel = 0; }            // a finger on the glass catches the page
  }, { passive: true });
  addEventListener('touchmove', (e) => {
    if (touchY === null) return;
    const y = e.touches[0].clientY, now = performance.now();
    const dy = touchY - y;
    const dir = Math.sign(dy);
    if (!dir || !inVoyage(dir) || (!dragging && dir > 0 && chapterAt(scrollY) === n - 1 && scrollY >= holdTop(n - 1) - 2)) return;
    e.preventDefault();
    dragging = true;
    touchV = (touchLastY - y) / Math.max(1, now - touchLastT) * 1000;
    touchLastY = y; touchLastT = now;
    scrollTo(0, touchFrom + dy * 0.6);
  }, { passive: false });
  addEventListener('touchend', () => {
    if (touchY === null || !dragging) { touchY = null; return; }
    const moved = scrollY - touchFrom;
    touchY = null;
    pos = scrollY; vel = 0;
    const here = chapterAt(touchFrom);
    if (Math.abs(moved) < 30 && Math.abs(touchV) < 350) { sailTo(here); return; }   // springs back
    const dir = Math.sign(moved || touchV);
    sailTo(here + dir, Math.abs(touchV) * 0.6 + 300);
  });

  addEventListener('keydown', (e) => {
    if (playing || (e.target.closest && e.target.closest('input, textarea, video, summary'))) return;
    const dir = { ArrowDown: 1, PageDown: 1, ' ': 1, ArrowUp: -1, PageUp: -1 }[e.key];
    if (!dir || (e.key === ' ' && e.shiftKey)) return;
    if (inVoyage(dir) && page(dir, 700)) e.preventDefault();
  });

  const panels = [...document.querySelectorAll('.panel')];
  const panelFor = (id) => panels.find((p) => p.dataset.island === id);

  function onScroll() {
    if (playing) { scrollTo(0, lockY); return; }
    progress = Math.min(1, scrollY / maxScroll());
    $('cue').style.opacity = progress > 0.03 ? '0' : '1';
    document.body.classList.toggle('at-end', scrollY > maxScroll() + innerHeight * 0.12);
  }
  addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  /* ---- play mode ---- */
  const hud = $('hud');
  const verdict = $('verdict');

  function enterPlay() {
    playing = true;
    lockY = scrollY;
    document.body.classList.add('playing');
    world.setLift(false);
    world.setTextSide(0);
    fight.playerControlled = true;
    fight.restart();
    hud.classList.add('on');
    verdict.classList.remove('on');
  }
  function exitPlay() {
    playing = false;
    document.body.classList.remove('playing');
    world.setLift(true);
    shownIsland = null;    // the next frame puts the chapter's text, and the island's side, back
    fight.playerControlled = false;
    hud.classList.remove('on');
    verdict.classList.remove('on');
    $('stick').classList.remove('on');
  }
  $('playBtn').addEventListener('click', enterPlay);
  const sail = $('sailBtn');
  // "Play in your browser": straight into the fight (the camera finds the arena by
  // itself); Leave brings the visitor back to where they pressed it
  if (sail) sail.addEventListener('click', enterPlay);
  $('exitBtn').addEventListener('click', exitPlay);
  $('againBtn').addEventListener('click', () => { verdict.classList.remove('on'); fight.restart(); });
  addEventListener('keydown', (e) => { if (e.key === 'Escape' && playing) exitPlay(); });

  fight.onChange = (s) => {
    $('hpFill').style.width = Math.round((s.hp / s.maxHp) * 100) + '%';
    $('statKills').textContent = (lang === 'en' ? 'kills ' : 'убито ') + s.kills;
    $('statFoes').textContent = (lang === 'en' ? 'left ' : 'осталось ') + s.enemies;
  };
  fight.onEnd = (won, kills) => {
    if (!playing) { fight.restart(); return; }       // the idle demo just starts over
    $('verdictTitle').textContent = won
      ? (lang === 'en' ? 'Island taken' : 'Остров твой')
      : (lang === 'en' ? 'Run over' : 'Поход завершён');
    $('verdictLine').textContent = (lang === 'en' ? 'Enemies defeated: ' : 'Противников повержено: ') + kills;
    verdict.classList.add('on');
  };

  /* ---- input ---- */
  const keys = new Set();
  addEventListener('keydown', (e) => {
    if (!playing) return;
    const k = e.key.toLowerCase();
    if ('wasd'.includes(k) || k.startsWith('arrow')) { keys.add(k); e.preventDefault(); }
  });
  addEventListener('keyup', (e) => keys.delete(e.key.toLowerCase()));

  const stick = $('stick');
  const nub = $('stickNub');
  let pointerId = null, originX = 0, originY = 0, dragX = 0, dragY = 0;
  addEventListener('pointerdown', (e) => {
    if (!playing || e.target.closest('button')) return;
    pointerId = e.pointerId;
    originX = e.clientX; originY = e.clientY; dragX = dragY = 0;
    stick.style.left = (e.clientX - 64) + 'px';
    stick.style.top = (e.clientY - 64) + 'px';
    stick.classList.add('on');
  });
  addEventListener('pointermove', (e) => {
    if (e.pointerId !== pointerId) return;
    dragX = THREE.MathUtils.clamp((e.clientX - originX) / 58, -1, 1);
    dragY = THREE.MathUtils.clamp((e.clientY - originY) / 58, -1, 1);
    nub.style.transform = `translate(${dragX * 34}px, ${dragY * 34}px)`;
  });
  const endDrag = (e) => {
    if (e.pointerId !== pointerId) return;
    pointerId = null; dragX = dragY = 0;
    nub.style.transform = '';
    stick.classList.remove('on');
  };
  addEventListener('pointerup', endDrag);
  addEventListener('pointercancel', endDrag);

  function readInput() {
    let x = 0, y = 0;
    if (keys.has('a') || keys.has('arrowleft')) x -= 1;
    if (keys.has('d') || keys.has('arrowright')) x += 1;
    if (keys.has('w') || keys.has('arrowup')) y -= 1;
    if (keys.has('s') || keys.has('arrowdown')) y += 1;
    if (pointerId !== null) { x += dragX; y += dragY; }
    fight.setInput(THREE.MathUtils.clamp(x, -1, 1), THREE.MathUtils.clamp(y, -1, 1));
  }

  /* ---- the mouse lean: the frame drifts a little toward the pointer (mouse only) ---- */
  if (matchMedia('(pointer:fine)').matches && !reduced) {
    world.leanTarget = new THREE.Vector2();
    addEventListener('pointermove', (e) => {
      if (e.pointerType !== 'mouse' || playing) { world.leanTarget.set(0, 0); return; }
      world.leanTarget.set(e.clientX / innerWidth * 2 - 1, e.clientY / innerHeight * 2 - 1);
    }, { passive: true });
  }

  /* ---- size ---- */
  function resize() { world.resize(innerWidth, innerHeight); }
  resize();
  addEventListener('resize', resize);

  /* ---- loop ---- */
  let elapsed = 0;
  let shownIsland = null;
  const here = () => $('chartHere');

  function frame() {
    const dt = Math.min(world.clock.getDelta(), 0.05);
    elapsed += dt;
    readInput();

    let state = { storm: 0 };
    if (playing) {
      // close enough that a fighter reads as a person, not a speck: the islands are
      // painting-sized now, several times the old arena
      world.focusIsland(combatSpec, 0.24);
    } else {
      const r = world.routeAt(progress);
      world.setCamera(progress, elapsed);
      const spec = ISLANDS[r.station];
      const settled = !r.moving;

      // the panel belongs to the island the camera is holding on
      const wantId = settled ? spec.id : null;
      if (wantId !== shownIsland) {
        panels.forEach((p) => {
          const on = p.dataset.island === wantId;
          p.classList.toggle('on', on);
          // a chapter's clip plays only while its chapter is on screen; it loads on first show
          const v = p.querySelector('.beat video');
          if (v) { if (on) { v.preload = 'auto'; v.play().catch(() => {}); } else v.pause(); }
        });
        document.body.classList.toggle('hero-on', wantId === 'landing');
        // the sea chart keeps to the side the chapter text leaves free
        const shown = panels.find((p) => p.dataset.island === wantId);
        if (shown) document.body.classList.toggle('text-right', shown.classList.contains('right'));
        // and the island steps aside to the side the text leaves free
        if (shown) world.setTextSide(shown.classList.contains('right') ? -1 : 1);
        shownIsland = wantId;
      }
      // the island's name, drawn in real type and pinned to the water; on a tall
      // screen the chapter text fills the lower frame, so the name stays above it
      const tall = innerWidth / innerHeight < 0.8;
      const textPanel = tall && shownIsland ? panels.find((p) => p.dataset.island === shownIsland) : null;
      const ceiling = textPanel ? textPanel.getBoundingClientRect().top - 22 : Infinity;
      for (const isle of ISLANDS) {
        const el = worldLabels.get(isle.id);
        if (!el) continue;
        const p = world.projectLabel(isle, innerWidth, innerHeight);
        const near = isle.id === spec.id ? (settled ? 1 : 0.4) : 0;
        if (!p || near < 0.02) { el.style.opacity = '0'; continue; }
        el.style.transform = `translate(-50%,-50%) translate(${p.x.toFixed(1)}px,${Math.min(p.y, ceiling).toFixed(1)}px)`;
        el.style.opacity = String(near);
      }
      if (spec.storm) state.storm = settled ? Math.min(1, r.local * 1.6) : 0.2;

      const chart = $('chartSvg');
      if (chart.__place) chart.__place(r.u * (ISLANDS.length - 1), r.station);
    }

    world.tick(dt, elapsed, state);
    fight.update(dt, elapsed);
    world.render();
  }
  world.renderer.setAnimationLoop(frame);

  // the builds chapter: every skill and title and how they fuse
  buildWeb($('comboWeb'));

  /* a console handle, and a way to grab frames without relying on the page being painted */
  window.__ss = {
    world, fight, ISLANDS,
    get progress() { return progress; },
    step(seconds = 1 / 60, times = 1) {
      for (let k = 0; k < times; k++) { elapsed += seconds; world.tick(seconds, elapsed, { storm: 1 }); fight.update(seconds, elapsed); }
    },
    async shot(name, p, opts = {}) {
      if (p !== undefined) { progress = p; world.setCamera(p, elapsed); }
      if (opts.island !== undefined) world.focusIsland(ISLANDS[opts.island], opts.zoom || 1);
      world.labels.forEach((l) => { l.mesh.material.opacity = 1; });
      world.tick(0.016, elapsed, { storm: opts.storm ?? 1 });
      fight.update(0.016, elapsed);
      const data = await world.grab(opts.w || 1280, opts.h || 720);
      const res = await fetch('/__shot', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, data }),
      });
      return res.json();
    },
  };
}

boot();
