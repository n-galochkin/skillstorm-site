"""app.js: the bottom chart becomes an inked sea chart on torn parchment (Nikita 2026-10-22:
"в виде пергамента, где нарисованы острова схематично и пути кривыми линиями")."""
import io
import sys

p = sys.argv[1]
s = io.open(p, encoding="utf-8").read()
s = s.replace("import { ISLANDS } from './archipelago.js';", "import { ISLANDS, ISLETS } from './archipelago.js';", 1)

NEW = r"""/* ----------------------------------------------------------- the chart */
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
  const squeeze = (v) => (Math.abs(v) <= 200 ? v : Math.sign(v) * (200 + (Math.abs(v) - 200) / 6));
  const chapters = ISLANDS.map((i) => [i.pos[0], squeeze(i.pos[1])]);
  const minX = Math.min(...chapters.map((c) => c[0])) - 70, maxX = Math.max(...chapters.map((c) => c[0])) + 70;
  const minZ = Math.min(...chapters.map((c) => c[1])) - 60, maxZ = Math.max(...chapters.map((c) => c[1])) + 60;
  const k = Math.min((W - 40) / (maxX - minX), (H - 50) / (maxZ - minZ));
  const ox = (W - (maxX - minX) * k) / 2, oy = 30 + (H - 40 - (maxZ - minZ) * k) / 2;
  const sx = (x) => ox + (x - minX) * k;
  const sy = (z) => oy + (squeeze(z) - minZ) * k;

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
    const r = Math.max(1.6, isle.radius * k * 0.8);
    html += `<path d="${coast(sx(isle.pos[0]), sy(isle.pos[1]), r, rnd() * 6.28)}" fill="#cbbf8a" stroke="#5a3e1c" stroke-width=".7"/>`;
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

  // the chapter islands: water lines off the coast, a washed land fill, a name in ink
  ISLANDS.forEach((isle, i) => {
    const [x, y] = P[i];
    const r = 7 + Math.min(isle.radius, 130) * 0.06;
    const ph = rnd() * 6.28;
    const ty = y - r - 7 < 34 ? y + r + 13 : (i % 2 ? y - r - 7 : y + r + 13);
    html += `<g class="dot" data-i="${i}">
      <path d="${coast(x, y, r, ph, 1.6)}" fill="none" stroke="#6f8b88" stroke-width=".5" stroke-dasharray="1.5 2" opacity=".7"/>
      <path d="${coast(x, y, r, ph, 1.3)}" fill="none" stroke="#6f8b88" stroke-width=".6" opacity=".85"/>
      <path class="land" d="${coast(x, y, r, ph)}" fill="#b9b06e" stroke="#4a3216" stroke-width="1.1"/>
      <circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${(r + 8).toFixed(1)}" fill="transparent"/>
      <text x="${x.toFixed(1)}" y="${ty.toFixed(1)}" text-anchor="middle">${isle.name[lang]}</text>
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
"""
start = s.index("/* ----------------------------------------------------------- the chart */")
end = s.index("drawChart();\n") + len("drawChart();\n")
s = s[:start] + NEW + s[end:]

# the frame loop hands the route position to the chart instead of placing the old arrow itself
a0 = s.index("      const dot = here();\n")
tail = "        svg.querySelectorAll('.dot').forEach((g, i) => g.classList.toggle('here', i === r.station));\n      }\n"
a1 = s.index(tail, a0) + len(tail)
s = s[:a0] + "      const chart = $('chartSvg');\n      if (chart.__place) chart.__place(r.u * (ISLANDS.length - 1), r.station);\n" + s[a1:]
io.open(p, "w", encoding="utf-8").write(s)
print("ok")
