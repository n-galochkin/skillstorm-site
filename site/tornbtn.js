/* The site's buttons are scraps torn off the sea chart, and a sword cuts them.

   Every .plate (main action) and .ghost (secondary) on the page is rebuilt as a
   torn piece of parchment drawn to its own size. Hovering it (or the sword cursor
   meeting it) slashes it along a diagonal: two copies of the button, each clipped
   to one side of the cut, part and the cut glows.

   On a mouse the pointer is a sword: it follows the pointer, swings on a click and
   swings when it meets a button. Touch screens keep the plain tap. */

const SVGNS = 'http://www.w3.org/2000/svg';

function rng(text) {
  let seed = 7;
  for (const ch of text) seed = (seed * 31 + ch.charCodeAt(0)) % 2147483647;
  return () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
}

/* a torn outline for a w x h scrap: jittered points along all four edges */
function tornPath(w, h, text) {
  const r = rng(text);
  const p = [];
  const step = () => 12 + r() * 9;
  for (let x = 3; x < w - 3; x += step()) p.push([x, 2 + r() * 6]);
  for (let y = 10; y < h - 8; y += 9 + r() * 6) p.push([w - 2 - r() * 5, y]);
  for (let x = w - 3; x > 3; x -= step()) p.push([x, h - 2 - r() * 6]);
  for (let y = h - 10; y > 8; y -= 9 + r() * 6) p.push([2 + r() * 5, y]);
  return 'M' + p.map(([x, y]) => x.toFixed(1) + ' ' + y.toFixed(1)).join(' L') + ' Z';
}

/* the chart's red dashed route, drawn across the scrap */
function routePath(w, h, text) {
  const r = rng(text + '~');
  const y = () => (h * (0.62 + (r() - 0.5) * 0.3)).toFixed(1);
  return `M${(w * 0.1).toFixed(1)} ${y()} C${(w * 0.3).toFixed(1)} ${y()},${(w * 0.45).toFixed(1)} ${y()},${(w * 0.6).toFixed(1)} ${y()} S${(w * 0.85).toFixed(1)} ${y()},${(w * 0.92).toFixed(1)} ${y()}`;
}

function half(cls, label) {
  const s = document.createElement('span');
  s.className = 'half ' + cls;
  s.setAttribute('aria-hidden', 'true');   // the label is read once, from the sizer
  const svg = document.createElementNS(SVGNS, 'svg');
  svg.setAttribute('aria-hidden', 'true');
  const paper = document.createElementNS(SVGNS, 'path');
  paper.setAttribute('class', 'paper');
  const route = document.createElementNS(SVGNS, 'path');
  route.setAttribute('class', 'route');
  svg.append(paper, route);
  const l = document.createElement('span');
  l.className = 'lbl';
  l.textContent = label;
  s.append(svg, l);
  return s;
}

function build(el) {
  const label = el.textContent.trim();
  const main = el.classList.contains('plate');
  el.classList.remove('plate', 'ghost');
  el.classList.add('torn', main ? 'torn-main' : 'torn-sub');
  el.textContent = '';
  const sizer = document.createElement('span');     // keeps the button's natural size
  sizer.className = 'sizer';
  sizer.textContent = label;
  const glow = document.createElement('span');
  glow.className = 'glow';
  const cut = document.createElement('span');
  cut.className = 'cut';
  el.append(sizer, glow, half('h1', label), half('h2', label), cut);
  el.dataset.label = label;
  if (!el.getAttribute('aria-label')) el.setAttribute('aria-label', label);
}

function draw(el) {
  const w = el.offsetWidth, h = el.offsetHeight;
  if (!w || !h) return;
  const label = el.dataset.label;
  const d = tornPath(w, h, label);
  const route = routePath(w, h, label);
  for (const svg of el.querySelectorAll('svg')) {
    svg.setAttribute('viewBox', `0 0 ${w} ${h}`);
    svg.querySelector('.paper').setAttribute('d', d);
    svg.querySelector('.route').setAttribute('d', route);
  }
  // the cut runs corner to corner of the middle band, so its angle follows the shape
  el.style.setProperty('--ang', (-Math.atan2(h * 0.4, w) * 180 / Math.PI).toFixed(2) + 'deg');
}

const buttons = [...document.querySelectorAll('.plate, .ghost')];
buttons.forEach(build);
const redraw = () => buttons.forEach(draw);
redraw();
if (document.fonts) document.fonts.ready.then(redraw);
addEventListener('resize', redraw);
// buttons inside panels that fade in may have no size yet: draw them when they first show
const sizes = new ResizeObserver((entries) => entries.forEach((e) => draw(e.target)));
buttons.forEach((b) => sizes.observe(b));

/* ---- the sword cursor ---- */
if (matchMedia('(pointer:fine)').matches && !matchMedia('(prefers-reduced-motion: reduce)').matches) {
  const cur = document.createElement('div');
  cur.id = 'sword';
  cur.setAttribute('aria-hidden', 'true');
  cur.innerHTML = `<svg viewBox="-4 -4 56 56"><g transform="rotate(-45) translate(-22 0)">
    <path d="M22 0 L25.5 5 L25.5 30 L22 30 Z" fill="#b9c6d2"/><path d="M22 0 L18.5 5 L18.5 30 L22 30 Z" fill="#f4f7fa"/>
    <path d="M22 4 V28" stroke="#8796a5" stroke-width=".8"/>
    <path d="M12 30 H32 L30 34 H14 Z" fill="#f2c55c" stroke="#5a3a10" stroke-width="1"/>
    <rect x="19.6" y="34" width="4.8" height="9" rx="1.5" fill="#6a3e1c" stroke="#2e1a08" stroke-width=".8"/>
    <circle cx="22" cy="45.5" r="3" fill="#f2c55c" stroke="#5a3a10" stroke-width="1"/>
    <path d="M22 0 L25.5 5 V30 H18.5 V5 Z" fill="none" stroke="#1d2b38" stroke-width="1.1" stroke-linejoin="round"/>
  </g></svg>`;
  document.body.appendChild(cur);
  document.documentElement.classList.add('sword-cursor');
  let x = -100, y = -100;
  // the blade's tip is the hot spot; it sits a few pixels into the drawing's corner
  addEventListener('pointermove', (e) => {
    if (e.pointerType !== 'mouse') return;
    x = e.clientX; y = e.clientY;
    cur.style.transform = `translate(${x - 4}px,${y - 4}px)`;
  }, { passive: true });
  const swing = () => {
    cur.classList.remove('swing'); void cur.offsetWidth; cur.classList.add('swing');
    const a = document.createElement('div');
    a.className = 'sword-arc';
    a.style.left = (x + 18) + 'px'; a.style.top = (y + 18) + 'px';
    document.body.appendChild(a);
    setTimeout(() => a.remove(), 420);
  };
  addEventListener('pointerdown', (e) => { if (e.pointerType === 'mouse') swing(); });
  document.addEventListener('pointerover', (e) => {
    const b = e.target.closest && e.target.closest('.torn');
    if (b && !b.contains(e.relatedTarget)) { cur.classList.add('over'); swing(); }
  });
  document.addEventListener('pointerout', (e) => {
    const b = e.target.closest && e.target.closest('.torn');
    if (b && !b.contains(e.relatedTarget)) cur.classList.remove('over');
  });
  document.addEventListener('mouseleave', () => { cur.style.transform = 'translate(-100px,-100px)'; });
}
