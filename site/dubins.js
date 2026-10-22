/* Dubins paths: the shortest way between two poses (point + heading) for something that can only
   move forward and turn no tighter than a radius - a car, a glider, a bird. Six candidate words
   (LSL, RSR, LSR, RSL, RLR, LRL: L = turn left, S = straight, R = turn right); the shortest wins.
   Angles are counter-clockwise in the (x, y) plane; the camera feeds world (x, z) in as (x, y).
   After L. E. Dubins (1957) and the closed forms in Shkel & Lumelsky (2001). */
const TAU = Math.PI * 2;
const mod2pi = (a) => ((a % TAU) + TAU) % TAU;

function words(alpha, beta, d) {
  const sa = Math.sin(alpha), sb = Math.sin(beta), ca = Math.cos(alpha), cb = Math.cos(beta);
  const cab = Math.cos(alpha - beta);
  const out = [];
  {   // LSL
    const p2 = 2 + d * d - 2 * cab + 2 * d * (sa - sb);
    if (p2 >= 0) {
      const t1 = Math.atan2(cb - ca, d + sa - sb);
      out.push(['LSL', mod2pi(-alpha + t1), Math.sqrt(p2), mod2pi(beta - t1)]);
    }
  }
  {   // RSR
    const p2 = 2 + d * d - 2 * cab + 2 * d * (sb - sa);
    if (p2 >= 0) {
      const t1 = Math.atan2(ca - cb, d - sa + sb);
      out.push(['RSR', mod2pi(alpha - t1), Math.sqrt(p2), mod2pi(-beta + t1)]);
    }
  }
  {   // LSR
    const p2 = -2 + d * d + 2 * cab + 2 * d * (sa + sb);
    if (p2 >= 0) {
      const p = Math.sqrt(p2);
      const t2 = Math.atan2(-ca - cb, d + sa + sb) - Math.atan2(-2, p);
      out.push(['LSR', mod2pi(-alpha + t2), p, mod2pi(-mod2pi(beta) + t2)]);
    }
  }
  {   // RSL
    const p2 = d * d - 2 + 2 * cab - 2 * d * (sa + sb);
    if (p2 >= 0) {
      const p = Math.sqrt(p2);
      const t2 = Math.atan2(ca + cb, d - sa - sb) - Math.atan2(2, p);
      out.push(['RSL', mod2pi(alpha - t2), p, mod2pi(beta - t2)]);
    }
  }
  {   // RLR
    const tmp = (6 - d * d + 2 * cab + 2 * d * (sa - sb)) / 8;
    if (Math.abs(tmp) <= 1) {
      const p = mod2pi(TAU - Math.acos(tmp));
      const t = mod2pi(alpha - Math.atan2(ca - cb, d - sa + sb) + p / 2);
      out.push(['RLR', t, p, mod2pi(alpha - beta - t + p)]);
    }
  }
  {   // LRL
    const tmp = (6 - d * d + 2 * cab + 2 * d * (sb - sa)) / 8;
    if (Math.abs(tmp) <= 1) {
      const p = mod2pi(TAU - Math.acos(tmp));
      const t = mod2pi(-alpha - Math.atan2(ca - cb, d + sa - sb) + p / 2);
      out.push(['LRL', t, p, mod2pi(mod2pi(beta) - alpha - t + p)]);
    }
  }
  return out;
}

/* The shortest path from (x0, y0, heading th0) to (x1, y1, th1) with turning radius r, sampled
   every `step` units of length: [{x, y, th}], first and last exactly the two poses. */
export function dubins(x0, y0, th0, x1, y1, th1, r, step = 30) {
  const dx = x1 - x0, dy = y1 - y0;
  const d = Math.hypot(dx, dy) / r;
  const theta = mod2pi(Math.atan2(dy, dx));
  const alpha = mod2pi(th0 - theta), beta = mod2pi(th1 - theta);
  const best = words(alpha, beta, d).reduce((b, w) => (!b || w[1] + w[2] + w[3] < b[1] + b[2] + b[3] ? w : b), null);
  const pts = [{ x: x0, y: y0, th: th0 }];
  if (!best) { pts.push({ x: x1, y: y1, th: th1 }); return { pts, length: Math.hypot(dx, dy) }; }
  let x = x0, y = y0, th = th0;
  const segs = [[best[0][0], best[1]], [best[0][1], best[2]], [best[0][2], best[3]]];
  const ds = step / r;
  for (const [kind, len] of segs) {
    let done = 0;
    while (done < len - 1e-9) {
      const h = Math.min(ds, len - done);
      if (kind === 'S') { x += r * Math.cos(th) * h; y += r * Math.sin(th) * h; }
      else if (kind === 'L') { x += r * (Math.sin(th + h) - Math.sin(th)); y += r * (Math.cos(th) - Math.cos(th + h)); th += h; }
      else { x += r * (Math.sin(th) - Math.sin(th - h)); y += r * (Math.cos(th - h) - Math.cos(th)); th -= h; }
      done += h;
      pts.push({ x, y, th });
    }
  }
  pts[pts.length - 1] = { x: x1, y: y1, th: th1 };
  return { pts, length: (best[1] + best[2] + best[3]) * r, word: best[0] };
}
