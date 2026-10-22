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
// The site is English only; the copy lives in the markup.
const lang = 'en';
document.documentElement.lang = lang;

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
  const W = 5.2;                // spring stiffness: about 1.2 s from island to island
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
    fight.playerControlled = true;
    fight.restart();
    hud.classList.add('on');
    verdict.classList.remove('on');
  }
  function exitPlay() {
    playing = false;
    document.body.classList.remove('playing');
    world.setLift(true);
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
