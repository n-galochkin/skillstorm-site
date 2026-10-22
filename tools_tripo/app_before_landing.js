/* Wiring: scroll sails the camera, each island shows its panel, the second one
   hands over the controls. */
import * as THREE from 'three';
import { World, LIGHT } from './world.js';
import { Fight } from './fight.js';
import { ISLANDS } from './archipelago.js';

const $ = (id) => document.getElementById(id);
const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;

const SYNERGIES = ['Avalanche', 'TwinFang', 'Wildfire', 'FrostCrown', 'Bloodbath', 'Crossfire',
  'Hurricane', 'Shredder', 'AbsoluteZero', 'Berserker', 'Blizzard', 'Bloodhound', 'Buckshot',
  'BulletStorm', 'Bulwark', 'ColdBlood', 'Darkness', 'Epidemic', 'EyeOfTheStorm', 'Fractal',
  'Godspeed', 'Guillotine', 'Headhunter', 'Juggernaut', 'Plaguelord', 'Reaper', 'RedHarvest',
  'Riposte', 'Skewer', 'Sniper', 'Stormchaser', 'SunDance', 'ThermalShock', 'Titanheart',
  'TrophyHunter'];

/* ----------------------------------------------------------- language */
const EN = {
  'p1.where': 'Landing', 'p1.h': 'Everyone lands with nothing',
  'p1.a': 'The boats reach the island at first light. Each fighter has a linen shirt and whatever they managed to pick up. Eight minutes later the island belongs to one of them.',
  'p1.b': 'Five more islands lie ahead across the water, and each one tells its part. Sail on.',
  'p1.cta': 'Set sail', 'p1.hint': 'Six islands ahead',
  'p1.f1': '5–8 minute match', 'p1.f2': 'PC and Android', 'p1.f3': 'In development',
  'p2.where': 'How it plays', 'p2.h': 'The blade swings on its own',
  'p2.a': 'Stand still and you strike. Take a step and you stop. The whole game lives between those two states: finish the kill and take an arrow in the back, or break away and hand over the tempo.',
  'p2.b': 'Below is a real fight on the game’s own models. Take control and it is yours.',
  'p2.cta': 'Take control', 'p2.hint': 'WASD or drag',
  'p3.where': 'Building a run', 'p3.h': 'Two skills add up to a third',
  'p3.a': 'Every level offers three. The right pair fuses into a named synergy and the fight changes under your hands — no pause, no menu.',
  'p3.t1': 'skills', 'p3.t2': 'synergies',
  'p4.where': 'The zone', 'p4.h': 'The storm decides where the fight happens',
  'p4.a': 'Fog and lightning swallow the edge of the island. Outside it your health drains and the circle tightens, so whoever hid in the bushes walks into the middle just as the ones who have been fighting all along arrive.',
  'p4.b': 'Roaming bosses and mob waves around the best loot hold up the middle of the match, where battle royales usually sag.',
  'p5.where': 'Between runs', 'p5.h': 'Between runs, a kingdom of your own',
  'p5.a': 'An island gives up its resources, and out of them grow your character and your gear: a forge, a full set of armour, weapon mastery, a place on the regional ladder. The next island is always meaner than the last.',
  'p5.cap': 'Screens from the current build',
  'p6.where': 'Who makes it', 'p6.h': 'One person and a few AI agents are building this',
  'p6.a': 'Code, tests, armour fitting and clip editing all run at once across several sessions. Short videos about the process come out regularly.',
  'p6.foot': 'Bella Games · no release date yet',
  'g.landing': 'SHORE', 'g.combat': 'FIGHT', 'g.skills': 'SKILLS',
  'g.storm': 'STORM', 'g.forge': 'FORGE', 'g.devlog': 'YARD',
  'chart.h': 'Archipelago', 'cue': 'Scroll', 'play.exit': 'Leave', 'end.again': 'Again',
  'boot.load': 'Raising sail…',
};
const RU = {};
document.querySelectorAll('[data-i]').forEach((el) => { RU[el.dataset.i] = el.innerHTML; });
let lang = 'ru';
try { if (localStorage.getItem('ss-lang') === 'en') lang = 'en'; } catch (e) {}

function applyLang() {
  const dict = lang === 'en' ? EN : RU;
  document.querySelectorAll('[data-i]').forEach((el) => {
    const v = dict[el.dataset.i];
    if (v !== undefined) el.innerHTML = v;
  });
  document.documentElement.lang = lang;
  $('lang-ru').setAttribute('aria-pressed', String(lang === 'ru'));
  $('lang-en').setAttribute('aria-pressed', String(lang === 'en'));
}
function setLang(code) {
  lang = code;
  try { localStorage.setItem('ss-lang', code); } catch (e) {}
  const run = () => { applyLang(); drawChart(); retitleWorldLabels(); };
  if (document.startViewTransition && !reduced) document.startViewTransition(run); else run();
}
$('lang-ru').addEventListener('click', () => setLang('ru'));
$('lang-en').addEventListener('click', () => setLang('en'));
applyLang();

/* ----------------------------------------------------------- synergy wall */
const wall = $('wall');
SYNERGIES.forEach((n) => {
  const s = document.createElement('span');
  s.textContent = n;
  wall.appendChild(s);
});

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
let chartGoTo = () => {};
function drawChart() {
  const svg = $('chartSvg');
  const xs = ISLANDS.map((i) => i.pos[0]);
  const zs = ISLANDS.map((i) => i.pos[1]);
  const padX = 15, padY = 17;
  const minX = Math.min(...xs), maxX = Math.max(...xs);
  const minZ = Math.min(...zs), maxZ = Math.max(...zs);
  const sx = (x) => padX + (x - minX) / (maxX - minX) * (140 - padX * 2);
  const sy = (z) => 34 + (z - (minZ + maxZ) / 2) / Math.max(maxZ - minZ, 1) * 30;

  // an island mark drawn as a small coastline, not a dot
  const blob = (cx, cy, r, seed) => {
    const pts = [];
    for (let k = 0; k < 11; k++) {
      const ang = (k / 11) * Math.PI * 2;
      const wob = 0.72 + ((Math.sin(seed * 2.3 + k * 1.7) + 1) / 2) * 0.55;
      pts.push(`${(cx + Math.cos(ang) * r * wob).toFixed(2)},${(cy + Math.sin(ang) * r * wob * 0.8).toFixed(2)}`);
    }
    return `M${pts.join('L')}Z`;
  };

  let html = `<defs>
    <radialGradient id="shoal"><stop offset="0%" stop-color="#2ea3d8" stop-opacity=".5"/>
    <stop offset="100%" stop-color="#2ea3d8" stop-opacity="0"/></radialGradient>
  </defs>`;

  // compass rose
  html += `<g transform="translate(12,12)" opacity=".62">
    <circle r="7.4" fill="none" stroke="#2a5572" stroke-width=".45"/>
    <circle r="4.6" fill="none" stroke="#2a5572" stroke-width=".3"/>
    ${[0, 45, 90, 135, 180, 225, 270, 315].map((d) => {
      const rad = (d - 90) * Math.PI / 180;
      const r0 = d % 90 === 0 ? 4.6 : 6.1;
      return `<line x1="${(Math.cos(rad) * r0).toFixed(2)}" y1="${(Math.sin(rad) * r0).toFixed(2)}"
        x2="${(Math.cos(rad) * 7.4).toFixed(2)}" y2="${(Math.sin(rad) * 7.4).toFixed(2)}"
        stroke="#2a5572" stroke-width=".4"/>`;
    }).join('')}
    <path d="M0,-8.6 L1.7,0 L0,2.4 L-1.7,0 Z" fill="#f2c55c"/>
    <path d="M0,8.6 L1.7,0 L0,-2.4 L-1.7,0 Z" fill="#2a5572"/>
  </g>`;

  const route = ISLANDS.map((i) => `${sx(i.pos[0]).toFixed(1)},${sy(i.pos[1]).toFixed(1)}`).join(' ');
  html += `<polyline points="${route}" fill="none" stroke="#f2c55c" stroke-width=".65"
      stroke-dasharray="2.6 3" opacity=".42" stroke-linecap="round"/>`;

  ISLANDS.forEach((isle, i) => {
    const x = sx(isle.pos[0]), y = sy(isle.pos[1]);
    const r = 2.4 + (isle.radius - 25) * 0.09;
    const above = isle.pos[1] > (minZ + maxZ) / 2;      // label away from the route
    const ty = above ? y + r + 5.4 : y - r - 3.2;
    html += `<g class="dot" data-i="${i}">
      <circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${(r + 3.4).toFixed(1)}" fill="url(#shoal)"/>
      <path d="${blob(x, y, r, isle.seed)}" fill="#4b8a52" stroke="#e8dcc0" stroke-width=".4"/>
      <text x="${x.toFixed(1)}" y="${ty.toFixed(1)}" text-anchor="middle">${(isle.name[lang] || isle.name.ru).toUpperCase()}</text>
    </g>`;
  });

  html += `<g id="chartHere" transform="translate(${sx(ISLANDS[0].pos[0])},${sy(ISLANDS[0].pos[1])})">
      <path d="M0,-3 L2,2.4 L0,1.3 L-2,2.4 Z" fill="#f2c55c"/></g>`;
  svg.innerHTML = html;
  svg.querySelectorAll('.dot').forEach((g) => {
    g.addEventListener('click', () => chartGoTo(Number(g.dataset.i)));
  });
  svg.__sx = sx; svg.__sy = sy;
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

  function maxScroll() { return Math.max(document.body.scrollHeight - innerHeight, 1); }

  chartGoTo = (index) => {
    // scroll so that the camera settles in the middle of that island's hold
    const before = index * 1.0 + index * 1.45;
    const p = (before + 0.5) / TOTAL;
    scrollTo({ top: p * maxScroll(), behavior: reduced ? 'auto' : 'smooth' });
  };

  const panels = [...document.querySelectorAll('.panel')];
  const panelFor = (id) => panels.find((p) => p.dataset.island === id);

  function onScroll() {
    if (playing) { scrollTo(0, lockY); return; }
    progress = scrollY / maxScroll();
    $('cue').style.opacity = progress > 0.03 ? '0' : '1';
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
    fight.playerControlled = true;
    fight.restart();
    hud.classList.add('on');
    verdict.classList.remove('on');
  }
  function exitPlay() {
    playing = false;
    document.body.classList.remove('playing');
    fight.playerControlled = false;
    hud.classList.remove('on');
    verdict.classList.remove('on');
    $('stick').classList.remove('on');
  }
  $('playBtn').addEventListener('click', enterPlay);
  const sail = $('sailBtn');
  if (sail) sail.addEventListener('click', () => chartGoTo(1));
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
        panels.forEach((p) => p.classList.toggle('on', p.dataset.island === wantId));
        shownIsland = wantId;
      }
      // the island's name, drawn in real type and pinned to the water
      for (const isle of ISLANDS) {
        const el = worldLabels.get(isle.id);
        if (!el) continue;
        const p = world.projectLabel(isle, innerWidth, innerHeight);
        const near = isle.id === spec.id ? (settled ? 1 : 0.4) : 0;
        if (!p || near < 0.02) { el.style.opacity = '0'; continue; }
        el.style.transform = `translate(-50%,-50%) translate(${p.x.toFixed(1)}px,${p.y.toFixed(1)}px)`;
        el.style.opacity = String(near);
      }
      if (spec.storm) state.storm = settled ? Math.min(1, r.local * 1.6) : 0.2;

      const dot = here();
      if (dot) {
        const svg = $('chartSvg');
        const u = r.u * (ISLANDS.length - 1);
        const i0 = Math.floor(u), i1 = Math.min(i0 + 1, ISLANDS.length - 1);
        const f = u - i0;
        const x = THREE.MathUtils.lerp(ISLANDS[i0].pos[0], ISLANDS[i1].pos[0], f);
        const z = THREE.MathUtils.lerp(ISLANDS[i0].pos[1], ISLANDS[i1].pos[1], f);
        const ax = svg.__sx(ISLANDS[i0].pos[0]), ay = svg.__sy(ISLANDS[i0].pos[1]);
        const bx = svg.__sx(ISLANDS[i1].pos[0]), by = svg.__sy(ISLANDS[i1].pos[1]);
        const head = Math.atan2(by - ay, bx - ax) * 180 / Math.PI + 90;
        dot.setAttribute('transform',
          `translate(${svg.__sx(x).toFixed(1)},${svg.__sy(z).toFixed(1)}) rotate(${head.toFixed(1)})`);
        svg.querySelectorAll('.dot').forEach((g, i) => g.classList.toggle('here', i === r.station));
      }
    }

    world.tick(dt, elapsed, state);
    fight.update(dt, elapsed);
    world.render();
  }
  world.renderer.setAnimationLoop(frame);

  // synergy wall: a slow sweep, so the list reads as alive rather than as a dump
  if (!reduced) {
    const spans = [...wall.children];
    let i = 0;
    setInterval(() => {
      spans.forEach((s) => s.classList.remove('lit'));
      for (let k = 0; k < 3; k++) spans[(i + k * 9) % spans.length].classList.add('lit');
      i = (i + 1) % spans.length;
    }, 1300);
  }

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
