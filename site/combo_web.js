/* The combo web: every skill, every title and how they fuse, drawn as a passive-tree web.

   Skills sit on the outer ring, the gold second-tier titles on the middle one, the crimson
   third-tier titles in the centre; a thread runs from each ingredient to the title it makes.
   Pointing at a node lights its recipe (and, for a skill, what it goes into) and light runs
   along the threads; left alone, the web walks through its best recipes by itself. */
import { COMBOS } from './combos.js';

const NS = 'http://www.w3.org/2000/svg';
const R = { s: 226, 2: 152, 3: 72 };
const SIZE = { s: 30, 2: 32, 3: 40 };
const FEATURED = ['t_Darkness', 't_ThermalShock', 't_Hurricane', 't_BulletStorm', 't_Plaguelord', 't_Epidemic',
  't_AbsoluteZero', 't_Guillotine', 't_Reaper', 't_Bloodbath', 't_Titanheart', 't_Avalanche'];

const rad = (d) => (d * Math.PI) / 180;
const wrap = (d) => ((d % 360) + 360) % 360;
function circMean(angles) {
  let x = 0, y = 0;
  for (const a of angles) { x += Math.cos(rad(a)); y += Math.sin(rad(a)); }
  return wrap((Math.atan2(y, x) * 180) / Math.PI);
}
// spread nodes on one ring so no two sit closer than `gap` degrees, keeping their order and
// staying as near as they can to where their recipe puts them
function spread(items, gap) {
  if (items.length < 2) return;
  items.sort((a, b) => a.angle - b.angle);
  // open the ring at its widest empty stretch and lay the nodes out as a line from there
  let cut = 0, widest = -1;
  items.forEach((it, i) => {
    const next = items[(i + 1) % items.length];
    const d = wrap(next.angle - it.angle) || 360;
    if (d > widest) { widest = d; cut = (i + 1) % items.length; }
  });
  const line = items.slice(cut).concat(items.slice(0, cut));
  const want = [];
  line.forEach((it, i) => { want.push(i && it.angle < line[0].angle ? it.angle + 360 : it.angle); });
  const pos = want.slice();
  for (let pass = 0; pass < 80; pass++) {
    for (let i = 1; i < pos.length; i++) pos[i] = Math.max(pos[i], pos[i - 1] + gap);
    // the push only ever goes forward: slide the whole line back so it sits on its targets on average
    const drift = pos.reduce((s, p, i) => s + p - want[i], 0) / pos.length;
    for (let i = 0; i < pos.length; i++) pos[i] -= drift;
    for (let i = pos.length - 2; i >= 0; i--) pos[i] = Math.min(pos[i], pos[i + 1] - gap);
  }
  line.forEach((it, i) => { it.angle = wrap(pos[i]); });
}

export function buildWeb(host) {
  if (!host) return;
  const nodes = new Map();
  const nS = COMBOS.ring.length;
  COMBOS.ring.forEach((id, i) => {
    const s = COMBOS.skills.find((k) => k.id === id);
    nodes.set(id, { id, name: s.name, kind: 's', angle: wrap(-90 + (i * 360) / nS) });
  });
  for (const tier of [2, 3]) {
    const row = COMBOS.titles.filter((t) => t.tier === tier).map((t) => ({
      id: t.id, name: t.name, kind: tier, req: t.req, twist: t.twist,
      angle: circMean(t.req.map((r) => nodes.get(r).angle)),
    }));
    spread(row, tier === 2 ? 12.6 : 46);
    row.forEach((n) => nodes.set(n.id, n));
  }
  for (const n of nodes.values()) {
    const r = R[n.kind];
    n.x = Math.cos(rad(n.angle)) * r;
    n.y = Math.sin(rad(n.angle)) * r;
  }

  const svg = document.createElementNS(NS, 'svg');
  svg.setAttribute('viewBox', '-262 -262 524 524');
  svg.setAttribute('role', 'img');
  svg.setAttribute('aria-label', `${COMBOS.skills.length} skills fuse into ${COMBOS.titles.length} combo titles`);
  let html = `<g class="rings">${[R.s, R[2], R[3]].map((r) => `<circle r="${r}"/>`).join('')}</g><g class="threads">`;
  const threads = [];
  for (const n of nodes.values()) {
    if (!n.req) continue;
    for (const r of n.req) {
      const a = nodes.get(r);
      // the thread bows toward the centre, the way passive-tree links curve along their rings
      const mx = (a.x + n.x) / 2 * 0.82, my = (a.y + n.y) / 2 * 0.82;
      html += `<path data-from="${r}" data-to="${n.id}" class="t${n.kind}" d="M${a.x.toFixed(1)} ${a.y.toFixed(1)} Q${mx.toFixed(1)} ${my.toFixed(1)} ${n.x.toFixed(1)} ${n.y.toFixed(1)}"/>`;
      threads.push([r, n.id]);
    }
  }
  html += '</g><g class="nodes">';
  for (const n of nodes.values()) {
    const s = SIZE[n.kind];
    html += `<g class="node k${n.kind}" data-id="${n.id}" tabindex="0" transform="translate(${n.x.toFixed(1)},${n.y.toFixed(1)})">
      <circle class="halo" r="${(s * 0.78).toFixed(1)}"/>
      <image href="assets/icons/${n.id}.webp" x="${-s / 2}" y="${-s / 2}" width="${s}" height="${s}"/>
      <title>${n.name}</title></g>`;
  }
  html += '</g>';
  svg.innerHTML = html;

  const cap = document.createElement('div');
  cap.className = 'web-cap';
  cap.setAttribute('aria-live', 'polite');
  host.append(svg, cap);

  const pathEls = [...svg.querySelectorAll('.threads path')];
  pathEls.forEach((p) => { const L = p.getTotalLength(); p.style.setProperty('--len', L.toFixed(1)); });
  const nodeEl = new Map([...svg.querySelectorAll('.node')].map((g) => [g.dataset.id, g]));

  // a title's whole recipe, down to the skills; a skill's direct uses
  const recipe = (id, set = new Set()) => {
    set.add(id);
    const n = nodes.get(id);
    if (n.req) n.req.forEach((r) => recipe(r, set));
    return set;
  };
  function show(id) {
    const n = nodes.get(id);
    let lit;
    if (n.kind === 's') {
      lit = new Set([id]);
      for (const t of nodes.values()) if (t.req && t.req.includes(id)) lit.add(t.id);
    } else lit = recipe(id);
    svg.classList.add('focus');
    nodeEl.forEach((g, k) => g.classList.toggle('on', lit.has(k)));
    nodeEl.forEach((g, k) => g.classList.toggle('lead', k === id));
    pathEls.forEach((p) => {
      const on = lit.has(p.dataset.from) && lit.has(p.dataset.to) && (n.kind !== 's' || p.dataset.from === id);
      p.classList.toggle('on', on);
      if (on) { p.classList.remove('flow'); void p.getBBox(); p.classList.add('flow'); } else p.classList.remove('flow');
    });
    if (n.kind === 's') {
      const uses = [...lit].filter((k) => k !== id).map((k) => nodes.get(k).name);
      cap.innerHTML = `<b class="ks">${n.name}</b><span>goes into ${uses.join(', ')}</span>`;
    } else {
      const parts = n.req.map((r) => `<i><img src="assets/icons/${r}.webp" alt="">${nodes.get(r).name}</i>`).join('<em>+</em>');
      cap.innerHTML = `<b class="k${n.kind}">${n.name}</b><span class="rec">${parts}</span><span class="tw">${n.twist}</span>`;
    }
  }

  let k = 0, pausedUntil = 0;
  const step = () => { if (performance.now() < pausedUntil) return; show(FEATURED[k++ % FEATURED.length]); };
  step();
  if (!matchMedia('(prefers-reduced-motion: reduce)').matches) setInterval(step, 2800);
  const pick = (e) => {
    const g = e.target.closest && e.target.closest('.node');
    if (!g) return;
    pausedUntil = performance.now() + 5000;
    show(g.dataset.id);
  };
  svg.addEventListener('pointerover', pick);
  svg.addEventListener('focusin', pick);
  svg.addEventListener('pointerleave', () => { pausedUntil = performance.now() + 1200; });
}
