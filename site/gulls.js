/* Gulls over the archipelago, drawn with the game's own bird: the painted 4x4
   flipbook from the main-menu hall (Content/SourceArt/HallLayers/BirdFlipbook.png),
   sixteen frames of one wingbeat.

   Each gull is a sprite that plays the flipbook at its own phase and rate, and the
   flocks wheel in slow loose circles over the islands. The drawing faces right, so a
   gull that crosses the screen leftward is mirrored to fly head first. */
import * as THREE from 'three';
import { texture, uv, uniform, vec2, float, select } from 'three/tsl';

const DEFAULTS = {
  flocks: 6,
  perFlock: [4, 7],
  radius: [26, 70],         // how wide a flock wheels
  altitude: [26, 62],       // under the clouds, over the trees
  span: [8.0, 11.0],        // sprite width in metres: far bigger than life, they must read from 150 m up
  speed: [0.10, 0.18],      // radians per second around the circle
  flapRate: [9, 13],        // flipbook frames per second
  seed: 23,
};

function mulberry(a) {
  return () => {
    a |= 0; a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const lerp = (r, [a, b]) => a + (b - a) * r;

export class Gulls {
  /* `centres` is either [[x, z], ...] (flocks wheel over those points at the default
     heights) or a list of ready flock plans {cx, cz, r, y, span}, which is how the
     scene spreads them over the whole archipelago at different heights. */
  constructor(tex, centres, opts = {}) {
    const o = { ...DEFAULTS, ...opts };
    this.object3D = new THREE.Group();
    this.object3D.name = 'Gulls';
    const rnd = mulberry(o.seed);
    this.birds = [];
    this._a = new THREE.Vector3();
    this._b = new THREE.Vector3();

    const plans = Array.isArray(centres[0]) ? null : centres;
    const count = plans ? plans.length : o.flocks;
    for (let f = 0; f < count; f++) {
      let flock;
      if (plans) {
        const pl = plans[f];
        flock = { cx: pl.cx, cz: pl.cz, r: pl.r, y: pl.y, span: pl.span, perFlock: pl.perFlock };
      } else {
        const c = centres[f % centres.length];
        flock = {
          cx: c[0] + (rnd() - 0.5) * 40, cz: c[1] + (rnd() - 0.5) * 40,
          r: lerp(rnd(), o.radius), y: lerp(rnd(), o.altitude),
        };
      }
      flock.w = lerp(rnd(), o.speed) * (rnd() < 0.5 ? -1 : 1) * (flock.r < 30 ? 1.6 : 1);
      flock.a0 = rnd() * Math.PI * 2;
      const n = Math.round(lerp(rnd(), flock.perFlock || o.perFlock));
      for (let i = 0; i < n; i++) {
        const frame = uniform(0);
        const mirror = uniform(0);
        // one cell of the 4x4 sheet; rows count from the top of the image
        const cell = Fn_cell(frame, mirror);
        const mat = new THREE.SpriteNodeMaterial({ transparent: true, depthWrite: false, fog: true });
        mat.colorNode = texture(tex, cell);
        const s = new THREE.Sprite(mat);
        const span = lerp(rnd(), flock.span || o.span);
        s.scale.set(span, span, 1);
        s.renderOrder = 7;
        s.userData = {
          flock, frame, mirror,
          lag: i * 0.11 + rnd() * 0.05,                // trailing along the circle
          off: [(rnd() - 0.5) * 9, (rnd() - 0.5) * 4, (rnd() - 0.5) * 9],
          rate: lerp(rnd(), o.flapRate), phase: rnd() * 16,
        };
        this.object3D.add(s);
        this.birds.push(s);
      }
    }
  }

  update(dt, elapsed, camera) {
    for (const s of this.birds) {
      const u = s.userData, f = u.flock;
      const a = f.a0 + f.w * elapsed - Math.sign(f.w) * u.lag;
      s.position.set(
        f.cx + Math.cos(a) * f.r + u.off[0],
        f.y + u.off[1] + Math.sin(elapsed * 0.7 + u.phase) * 0.8,
        f.cz + Math.sin(a) * f.r + u.off[2],
      );
      u.frame.value = Math.floor(elapsed * u.rate + u.phase) % 16;
      if (camera) {
        // which way it crosses the screen decides which way the drawing faces
        const ahead = a + Math.sign(f.w) * 0.05;
        this._a.copy(s.position).project(camera);
        this._b.set(f.cx + Math.cos(ahead) * f.r + u.off[0], s.position.y,
          f.cz + Math.sin(ahead) * f.r + u.off[2]).project(camera);
        if (Number.isFinite(this._a.x) && Number.isFinite(this._b.x)) {
          u.mirror.value = this._b.x < this._a.x ? 1 : 0;
        }
      }
    }
  }
}

/* uv of frame `frame` (0..15, row-major from the top-left), mirrored when asked */
function Fn_cell(frame, mirror) {
  const col = frame.mod(4);
  const row = frame.div(4).floor();
  const base = uv();
  const ux = select(mirror.greaterThan(0.5), float(1).sub(base.x), base.x);
  return vec2(ux.add(col).mul(0.25), base.y.add(float(3).sub(row)).mul(0.25));
}
