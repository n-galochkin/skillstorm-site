/* water.js — the sea for the Skillstorm site.
 *
 * One camera-centred radial mesh of water, drawn with a TSL node material under
 * WebGPURenderer (no GLSL anywhere). What it gives:
 *   - Gerstner swell (5 trains) displaced on the GPU, normals recomputed per pixel
 *     so the wave shading never shows the mesh grid;
 *   - depth colour from a shore-distance field baked once on the CPU: deep cobalt
 *     offshore, turquoise shelf hugging every island, pale sand right at the beach;
 *   - animated surf: a foam collar on the shoreline plus breaker lines rolling in,
 *     both surging with the swell;
 *   - sun glitter from a procedural detail normal map sampled at three scales;
 *   - optional drifting cloud shadows and exponential distance haze.
 *
 * Written from scratch for this site; the only borrowed pieces are the standard
 * Gerstner wave formulation and three.js' own TSL idioms (see examples/jsm/objects/
 * WaterMesh.js, MIT) for how a NodeMaterial takes a custom vertex/fragment node.
 *
 *   const ocean = new Ocean({ size: 1700, segments: 130, islands: [{pos:[x,z], radius}] });
 *   scene.add(ocean.object3D);
 *   ocean.update(dt, elapsed, camera);
 */

import {
  Group, Mesh, BufferGeometry, BufferAttribute, DataTexture, DataUtils,
  NodeMaterial, Color, Vector2, Vector3, Sphere,
  HalfFloatType, RGBAFormat, LinearFilter, ClampToEdgeWrapping, RepeatWrapping,
  FrontSide, NoColorSpace,
} from 'three';

import {
  Fn, float, vec2, vec3, vec4, uniform, texture,
  positionLocal, modelWorldMatrix, cameraProjectionMatrix, cameraViewMatrix, cameraPosition,
  varying, varyingProperty, normalize, dot, max, clamp, mix, pow, exp, sin, cos,
  smoothstep, fract, length, saturate, oneMinus,
} from 'three';

/* ------------------------------------------------------------------ noise */

/* Periodic value noise: a hash lattice that wraps on `period`, so every octave
   tiles and the textures below can be repeated over the sea without a seam. */
function makeLattice(period, seed) {
  const n = period * period;
  const v = new Float32Array(n);
  let s = seed >>> 0;
  for (let i = 0; i < n; i++) {
    s = (s * 1664525 + 1013904223) >>> 0;
    v[i] = (s >>> 8) / 16777216;
  }
  return v;
}

function latticeAt(lat, period, x, y) {
  const xi = Math.floor(x), yi = Math.floor(y);
  const fx = x - xi, fy = y - yi;
  const ux = fx * fx * (3 - 2 * fx), uy = fy * fy * (3 - 2 * fy);
  const x0 = ((xi % period) + period) % period, y0 = ((yi % period) + period) % period;
  const x1 = (x0 + 1) % period, y1 = (y0 + 1) % period;
  const a = lat[y0 * period + x0], b = lat[y0 * period + x1];
  const c = lat[y1 * period + x0], d = lat[y1 * period + x1];
  return (a + (b - a) * ux) + ((c + (d - c) * ux) - (a + (b - a) * ux)) * uy;
}

/* Tileable fBm sampled into a Float32Array of size*size, values ~0..1. */
export function fbmField(size, { octaves = 5, base = 4, gain = 0.5, seed = 1 } = {}) {
  const out = new Float32Array(size * size);
  let amp = 1, norm = 0, period = base;
  const lats = [];
  for (let o = 0; o < octaves; o++) {
    lats.push({ lat: makeLattice(period, seed * 7919 + o * 131), period, amp });
    norm += amp; amp *= gain; period *= 2;
  }
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      let v = 0;
      for (const o of lats) {
        v += latticeAt(o.lat, o.period, (x / size) * o.period, (y / size) * o.period) * o.amp;
      }
      out[y * size + x] = v / norm;
    }
  }
  return out;
}

/* A seamless detail normal map: fBm height turned into slopes. Used for the fine
   ripple that carries the sun glitter. */
export function makeDetailNormalTexture(size = 256, strength = 2.1) {
  const h = fbmField(size, { octaves: 5, base: 4, gain: 0.55, seed: 3 });
  const data = new Uint8Array(size * size * 4);
  const at = (x, y) => h[((y % size) + size) % size * size + (((x % size) + size) % size)];
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const dx = (at(x + 1, y) - at(x - 1, y)) * strength;
      const dy = (at(x, y + 1) - at(x, y - 1)) * strength;
      let nx = -dx, ny = -dy, nz = 1 / size * 24;
      const l = Math.hypot(nx, ny, nz) || 1;
      const i = (y * size + x) * 4;
      data[i] = Math.round((nx / l * 0.5 + 0.5) * 255);
      data[i + 1] = Math.round((ny / l * 0.5 + 0.5) * 255);
      data[i + 2] = Math.round((nz / l * 0.5 + 0.5) * 255);
      data[i + 3] = 255;
    }
  }
  const tex = new DataTexture(data, size, size);
  tex.wrapS = tex.wrapT = RepeatWrapping;
  tex.minFilter = tex.magFilter = LinearFilter;
  tex.colorSpace = NoColorSpace;
  tex.generateMipmaps = false;
  tex.needsUpdate = true;
  return tex;
}

/* A seamless soft cloud mask, shared by the cloud shadows here and by the puffs
   in atmosphere.js. */
export function makeCloudMaskTexture(size = 256, { seed = 9, octaves = 6 } = {}) {
  const h = fbmField(size, { octaves, base: 3, gain: 0.52, seed });
  const data = new Uint8Array(size * size * 4);
  for (let i = 0; i < size * size; i++) {
    const v = Math.max(0, Math.min(1, (h[i] - 0.38) * 2.5));
    const s = v * v * (3 - 2 * v);
    data[i * 4] = data[i * 4 + 1] = data[i * 4 + 2] = Math.round(s * 255);
    data[i * 4 + 3] = 255;
  }
  const tex = new DataTexture(data, size, size);
  tex.wrapS = tex.wrapT = RepeatWrapping;
  tex.minFilter = tex.magFilter = LinearFilter;
  tex.colorSpace = NoColorSpace;
  tex.generateMipmaps = false;
  tex.needsUpdate = true;
  return tex;
}

/* --------------------------------------------------------- shore distance */

/* Bakes, once, a half-float RGBA map over the islands' bounding box:
 *   R  signed distance to the nearest shore, metres (negative inside an island)
 *   G  the same distance normalised by that island's shelf width (0 beach .. 1 deep)
 *   BA unit vector pointing away from the nearest shore, on the sea plane
 * Half float keeps the surf line smooth; 8-bit quantised into visible contours.
 */
function buildShoreField(islands, { texel = 0.7, range = 150, maxDim = 2048 } = {}) {
  if (!islands || islands.length === 0) {
    const data = new Uint16Array(4 * 4 * 4);
    const far = DataUtils.toHalfFloat(range), one = DataUtils.toHalfFloat(1);
    for (let i = 0; i < 16; i++) {
      data[i * 4] = far; data[i * 4 + 1] = one; data[i * 4 + 2] = 0; data[i * 4 + 3] = one;
    }
    const tex = new DataTexture(data, 4, 4, RGBAFormat, HalfFloatType);
    tex.wrapS = tex.wrapT = ClampToEdgeWrapping;
    tex.minFilter = tex.magFilter = LinearFilter;
    tex.colorSpace = NoColorSpace;
    tex.generateMipmaps = false;
    tex.needsUpdate = true;
    return { texture: tex, min: new Vector2(-1, -1), size: new Vector2(2, 2), range };
  }

  const isl = islands.map((i) => {
    const r = i.radius ?? i.r ?? 10;
    return { x: i.pos ? i.pos[0] : i.x, z: i.pos ? i.pos[1] : i.z, r, shelf: Math.max(14, Math.min(58, r * 1.35)) };
  });

  let minX = Infinity, minZ = Infinity, maxX = -Infinity, maxZ = -Infinity;
  for (const i of isl) {
    minX = Math.min(minX, i.x - i.r - range); maxX = Math.max(maxX, i.x + i.r + range);
    minZ = Math.min(minZ, i.z - i.r - range); maxZ = Math.max(maxZ, i.z + i.r + range);
  }
  const spanX = maxX - minX, spanZ = maxZ - minZ;
  let w = Math.min(maxDim, Math.max(64, Math.round(spanX / texel)));
  let h = Math.min(maxDim, Math.max(64, Math.round(spanZ / texel)));
  const dx = spanX / w, dz = spanZ / h;

  const data = new Uint16Array(w * h * 4);
  const halfRange = DataUtils.toHalfFloat(range), halfOne = DataUtils.toHalfFloat(1);
  // Everything starts as open sea; each island then paints only the texels it can reach.
  for (let i = 0; i < w * h; i++) {
    data[i * 4] = halfRange; data[i * 4 + 1] = halfOne; data[i * 4 + 2] = 0; data[i * 4 + 3] = halfOne;
  }
  const best = new Float32Array(w * h).fill(range);

  for (const island of isl) {
    const reach = island.r + range;
    const x0 = Math.max(0, Math.floor((island.x - reach - minX) / dx));
    const x1 = Math.min(w - 1, Math.ceil((island.x + reach - minX) / dx));
    const z0 = Math.max(0, Math.floor((island.z - reach - minZ) / dz));
    const z1 = Math.min(h - 1, Math.ceil((island.z + reach - minZ) / dz));
    for (let y = z0; y <= z1; y++) {
      const wz = minZ + (y + 0.5) * dz;
      for (let x = x0; x <= x1; x++) {
        const wx = minX + (x + 0.5) * dx;
        const ox = wx - island.x, oz = wz - island.z;
        const len = Math.hypot(ox, oz) || 1e-5;
        const d = len - island.r;
        const idx = y * w + x;
        if (d < best[idx]) {
          best[idx] = d;
          data[idx * 4] = DataUtils.toHalfFloat(Math.max(-60, d));
          data[idx * 4 + 1] = DataUtils.toHalfFloat(Math.max(-1, Math.min(1.6, d / island.shelf)));
          data[idx * 4 + 2] = DataUtils.toHalfFloat(ox / len);
          data[idx * 4 + 3] = DataUtils.toHalfFloat(oz / len);
        }
      }
    }
  }

  const tex = new DataTexture(data, w, h, RGBAFormat, HalfFloatType);
  tex.wrapS = tex.wrapT = ClampToEdgeWrapping;
  tex.minFilter = tex.magFilter = LinearFilter;
  tex.colorSpace = NoColorSpace;
  tex.generateMipmaps = false;
  tex.needsUpdate = true;
  return { texture: tex, min: new Vector2(minX, minZ), size: new Vector2(spanX, spanZ), range };
}

/* The same field, measured from the islands' real outlines instead of circles.
 * Each island brings its own height lookup (sampled from the heightmap baked off its
 * mesh); a texel is land where any island stands above the water there. Distance to
 * the shore is then spread out from the coastline with a two-pass chamfer transform
 * that also carries the nearest shore point along, which gives the direction too.
 * A lobed island gets a lobed shelf, and a bay stays a bay.
 */
function buildShoreFieldFromLand(islands, { texel = 0.8, range = 150, maxDim = 2048, landAbove = 0.15 } = {}) {
  let minX = Infinity, minZ = Infinity, maxX = -Infinity, maxZ = -Infinity;
  for (const i of islands) {
    const r = i.radius * 1.7;
    minX = Math.min(minX, i.pos[0] - r - range); maxX = Math.max(maxX, i.pos[0] + r + range);
    minZ = Math.min(minZ, i.pos[1] - r - range); maxZ = Math.max(maxZ, i.pos[1] + r + range);
  }
  const spanX = maxX - minX, spanZ = maxZ - minZ;
  const w = Math.min(maxDim, Math.max(64, Math.round(spanX / texel)));
  const h = Math.min(maxDim, Math.max(64, Math.round(spanZ / texel)));
  const dx = spanX / w, dz = spanZ / h;
  const n = w * h;

  // who owns each land texel; -1 is sea
  const owner = new Int16Array(n).fill(-1);
  islands.forEach((isl, k) => {
    const r = isl.radius * 1.7;
    const x0 = Math.max(0, Math.floor((isl.pos[0] - r - minX) / dx));
    const x1 = Math.min(w - 1, Math.ceil((isl.pos[0] + r - minX) / dx));
    const z0 = Math.max(0, Math.floor((isl.pos[1] - r - minZ) / dz));
    const z1 = Math.min(h - 1, Math.ceil((isl.pos[1] + r - minZ) / dz));
    for (let y = z0; y <= z1; y++) {
      const wz = minZ + (y + 0.5) * dz;
      for (let x = x0; x <= x1; x++) {
        const wx = minX + (x + 0.5) * dx;
        if (isl.heightAt(wx, wz) > landAbove) owner[y * w + x] = k;
      }
    }
  });

  // nearest coastline texel for every texel, chamfer-propagated both ways
  const INF = 1e9;
  const dist = new Float32Array(n).fill(INF);
  const srcX = new Int32Array(n).fill(-1), srcY = new Int32Array(n).fill(-1);
  const shoreOwner = new Int16Array(n).fill(-1);   // which island a coastline texel belongs to
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      const i = y * w + x;
      const land = owner[i] >= 0;
      // a coastline texel is land with sea beside it (or sea with land beside it)
      let other = -1;
      if (x > 0 && (owner[i - 1] >= 0) !== land) other = i - 1;
      else if (x < w - 1 && (owner[i + 1] >= 0) !== land) other = i + 1;
      else if (y > 0 && (owner[i - w] >= 0) !== land) other = i - w;
      else if (y < h - 1 && (owner[i + w] >= 0) !== land) other = i + w;
      if (other >= 0) {
        dist[i] = 0; srcX[i] = x; srcY[i] = y;
        shoreOwner[i] = land ? owner[i] : owner[other];
      }
    }
  }
  const relax = (i, j) => {
    if (srcX[j] < 0) return;
    const x = i % w, y = (i - x) / w;
    const ex = (x - srcX[j]) * dx, ez = (y - srcY[j]) * dz;
    const d = ex * ex + ez * ez;
    if (d < dist[i]) { dist[i] = d; srcX[i] = srcX[j]; srcY[i] = srcY[j]; }
  };
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      const i = y * w + x;
      if (x > 0) relax(i, i - 1);
      if (y > 0) { relax(i, i - w); if (x > 0) relax(i, i - w - 1); if (x < w - 1) relax(i, i - w + 1); }
    }
  }
  for (let y = h - 1; y >= 0; y--) {
    for (let x = w - 1; x >= 0; x--) {
      const i = y * w + x;
      if (x < w - 1) relax(i, i + 1);
      if (y < h - 1) { relax(i, i + w); if (x < w - 1) relax(i, i + w + 1); if (x > 0) relax(i, i + w - 1); }
    }
  }

  const data = new Uint16Array(n * 4);
  const T = DataUtils.toHalfFloat;
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      const i = y * w + x;
      const land = owner[i] >= 0;
      let d = Math.sqrt(dist[i]);
      if (!isFinite(d) || d > range) d = range;
      const sx = srcX[i] >= 0 ? srcX[i] : x, sy = srcY[i] >= 0 ? srcY[i] : y;
      let ox = (x - sx) * dx, oz = (y - sy) * dz;
      const len = Math.hypot(ox, oz) || 1;
      ox /= len; oz /= len;
      if (land) { d = -d; ox = -ox; oz = -oz; }
      // the shelf belongs to the island whose shore this is
      const k = shoreOwner[sy * w + sx];
      const isl = islands[k >= 0 ? k : 0];
      const shelf = Math.max(7, Math.min(24, isl.radius * 0.42));
      data[i * 4] = T(Math.max(-60, d));
      data[i * 4 + 1] = T(Math.max(-1, Math.min(1.6, d / shelf)));
      data[i * 4 + 2] = T(ox);
      data[i * 4 + 3] = T(oz);
    }
  }

  const tex = new DataTexture(data, w, h, RGBAFormat, HalfFloatType);
  tex.wrapS = tex.wrapT = ClampToEdgeWrapping;
  tex.minFilter = tex.magFilter = LinearFilter;
  tex.colorSpace = NoColorSpace;
  tex.generateMipmaps = false;
  tex.needsUpdate = true;
  return { texture: tex, min: new Vector2(minX, minZ), size: new Vector2(spanX, spanZ), range };
}

/* ------------------------------------------------------------- geometry */

/* A disc whose rings grow with a power curve: fine quads under the camera,
   coarse ones out at the haze, roughly constant cost in screen space. */
function radialGrid(rings, sectors, inner, outer, curve = 2.6) {
  const vCount = rings * sectors + 1;
  const pos = new Float32Array(vCount * 3);
  let p = 0;
  pos[p++] = 0; pos[p++] = 0; pos[p++] = 0;
  for (let i = 0; i < rings; i++) {
    const t = (i + 1) / rings;
    const r = inner + (outer - inner) * Math.pow(t, curve);
    for (let j = 0; j < sectors; j++) {
      const a = (j / sectors) * Math.PI * 2;
      pos[p++] = Math.cos(a) * r; pos[p++] = 0; pos[p++] = Math.sin(a) * r;
    }
  }
  const idx = [];
  for (let j = 0; j < sectors; j++) {
    const a = 1 + j, b = 1 + ((j + 1) % sectors);
    idx.push(0, b, a);
  }
  for (let i = 0; i < rings - 1; i++) {
    const r0 = 1 + i * sectors, r1 = 1 + (i + 1) * sectors;
    for (let j = 0; j < sectors; j++) {
      const jn = (j + 1) % sectors;
      idx.push(r0 + j, r1 + jn, r1 + j);
      idx.push(r0 + j, r0 + jn, r1 + jn);
    }
  }
  const geo = new BufferGeometry();
  geo.setAttribute('position', new BufferAttribute(pos, 3));
  geo.setIndex(idx.length > 65535 ? new BufferAttribute(new Uint32Array(idx), 1)
                                  : new BufferAttribute(new Uint16Array(idx), 1));
  geo.boundingSphere = new Sphere(new Vector3(0, 0, 0), outer * 1.2);
  return geo;
}

/* ------------------------------------------------------------------ ocean */

const DEFAULTS = {
  size: 1700,
  segments: 130,
  islands: [],
  seaLevel: 0,
  follow: true,
  sunDirection: new Vector3(0.42, 0.52, -0.74).normalize(),
  sunColor: 0xfff3dc,
  /* Every colour below is pre-compensated for ACES tone mapping at exposure 1.22
     (what world.js renders with): e.g. deepColor 0x155d7e lands on #016995 on
     screen, the deep cobalt sampled from T_ArchipelagoSource.png. */
  skyColor: 0x54c1ff,       // what the water reflects at grazing angles -> #9ed3f0
  horizonColor: 0x2c89ce,   // the sea's own haze -> #45a6d7
  fogDensity: 0.0013,
  deepColor: 0x155d7e,      // -> #016995
  midColor: 0x096b94,       // -> #0d7fae
  shelfColor: 0x049897,     // -> #26b5b3
  sandColor: 0x10c4b4,      // -> #82d5cb
  foamColor: 0xffffff,
  waveScale: 1,
  waveSpeed: 0.45,
  detail: true,
  quality: 'high',          // 'low' drops the finest ripple layer and the second
                            // mottle sample: about a fifth off the pixel cost
};

/* The swell: five Gerstner trains, long and calm, the way the key art reads. */
const WAVES = [
  { dir: [1.0, 0.22], len: 64, amp: 0.80, steep: 0.62 },
  { dir: [0.72, -0.80], len: 41, amp: 0.50, steep: 0.55 },
  { dir: [-0.42, 1.0], len: 24.5, amp: 0.27, steep: 0.5 },
  { dir: [0.95, 0.62], len: 13.5, amp: 0.13, steep: 0.45 },
  { dir: [-0.80, -0.47], len: 7.8, amp: 0.062, steep: 0.4 },
];
/* where the main swell comes from, for the surf on the windward shore */
const SWELL_DIR = [-1.0 / Math.hypot(1.0, 0.22), -0.22 / Math.hypot(1.0, 0.22)];

export class Ocean {
  constructor(opts = {}) {
    const o = { ...DEFAULTS, ...opts };
    this.options = o;

    this.object3D = new Group();
    this.object3D.name = 'Ocean';

    // islands that carry a height lookup get a shoreline traced from their real
    // outline; plain {pos, radius} islands fall back to circles
    const field = o.islands.length && o.islands.every((i) => i.heightAt)
      ? buildShoreFieldFromLand(o.islands, { texel: 0.8, range: 150 })
      : buildShoreField(o.islands, { texel: 0.7, range: 150 });
    this.field = field;

    this.detailTex = o.detail ? makeDetailNormalTexture(256, 2.1) : null;
    this.cloudTex = makeCloudMaskTexture(256, { seed: 17, octaves: 6 });

    /* ---- uniforms (all animation is driven from `elapsed`, so a frame grab is
       reproducible: the same elapsed always gives the same sea) ---- */
    const U = this.u = {
      time: uniform(0),
      sunDir: uniform(new Vector3().copy(o.sunDirection).normalize()),
      sunColor: uniform(new Color(o.sunColor)),
      skyColor: uniform(new Color(o.skyColor)),
      horizon: uniform(new Color(o.horizonColor)),
      fogDensity: uniform(o.fogDensity),
      deep: uniform(new Color(o.deepColor)),
      mid: uniform(new Color(o.midColor)),
      shelf: uniform(new Color(o.shelfColor)),
      sand: uniform(new Color(o.sandColor)),
      foam: uniform(new Color(o.foamColor)),
      fieldMin: uniform(new Vector2().copy(field.min)),
      fieldSize: uniform(new Vector2().copy(field.size)),
      waveScale: uniform(o.waveScale),
      cloudShadow: uniform(0.0),
      cloudScale: uniform(0.0016),
      cloudDrift: uniform(new Vector2(-0.9, 0.35)),
      cloudCoverage: uniform(0.42),
    };

    const fieldTex = texture(field.texture);
    const uvForField = (xz) => xz.sub(U.fieldMin).div(U.fieldSize);

    /* ------------------------------------------------ the swell, in nodes */
    // Returns { offset, normal, height } for a world xz, damped near the shore.
    const swell = (xz, damp) => {
      const G = 9.81;
      let offX = float(0), offY = float(0), offZ = float(0);
      let nx = float(0), ny = float(1), nz = float(0);
      for (let i = 0; i < WAVES.length; i++) {
        const w = WAVES[i];
        const dl = Math.hypot(w.dir[0], w.dir[1]);
        const dx = w.dir[0] / dl, dz = w.dir[1] / dl;
        const k = (Math.PI * 2) / w.len;
        const speed = Math.sqrt(G / k) * DEFAULTS.waveSpeed;
        const A = w.amp;
        const Q = w.steep / (k * A * WAVES.length);
        const phase = xz.x.mul(dx * k).add(xz.y.mul(dz * k)).sub(U.time.mul(k * speed)).add(i * 1.7);
        const s = sin(phase), c = cos(phase);
        const amp = damp.mul(U.waveScale);
        offX = offX.add(c.mul(Q * A * dx).mul(amp));
        offZ = offZ.add(c.mul(Q * A * dz).mul(amp));
        offY = offY.add(s.mul(A).mul(amp));
        // analytic Gerstner normal
        nx = nx.sub(c.mul(dx * k * A).mul(amp));
        nz = nz.sub(c.mul(dz * k * A).mul(amp));
        ny = ny.sub(s.mul(Q * k * A).mul(amp));
      }
      return {
        offset: vec3(offX, offY, offZ),
        normal: normalize(vec3(nx, max(ny, 0.25), nz)),
        height: offY,
      };
    };

    /* ------------------------------------------------------- vertex stage */
    const vertexNode = Fn(() => {
      const base = modelWorldMatrix.mul(vec4(positionLocal, 1.0)).xyz.toVar();
      const fuv = uvForField(base.xz);
      const shore = fieldTex.uv(fuv).level(0).toVar();
      // waves lie down as the water shallows, so no crest climbs onto a beach
      const damp = smoothstep(float(-1.0), float(10.0), shore.x).toVar();
      const w = swell(base.xz, damp);
      const world = base.add(w.offset).toVar();
      // Under an island the sea is pushed well down, so a wave can never show through
      // a quay, a beach or a flat village street that sits close to sea level. The
      // shoreline itself is drawn per pixel in the fragment stage, so this costs nothing.
      world.y.subAssign(oneMinus(smoothstep(float(-4.0), float(0.5), shore.x)).mul(3.0));
      varyingProperty('vec3', 'vWorld').assign(world);
      return cameraProjectionMatrix.mul(cameraViewMatrix).mul(vec4(world, 1.0));
    })();

    /* ----------------------------------------------------- fragment stage */
    const fragmentNode = Fn(() => {
      const world = varying(vec3(), 'vWorld');

      // Re-read per pixel, so the shoreline stays crisp between vertices. The
      // field is clamp-to-edge and padded by `range`, so outside its box the
      // sample is simply open sea.
      const shore = fieldTex.uv(clamp(uvForField(world.xz), vec2(0.0), vec2(1.0))).toVar();

      const dist = shore.x.toVar();            // metres to the nearest shore
      const shelfT = shore.y.toVar();          // 0 at the beach .. 1 open sea
      const damp = smoothstep(float(-1.0), float(10.0), dist).toVar();

      const w = swell(world.xz, damp);
      const N = w.normal.toVar();

      const toEye = cameraPosition.sub(world).toVar();
      const viewDist = length(toEye).toVar();
      const V = normalize(toEye).toVar();

      /* ---- fine ripple: three scrolling octaves of the detail normal ---- */
      if (this.detailTex) {
        const dTex = texture(this.detailTex);
        const near = exp(viewDist.mul(-0.0045)).toVar();   // fade before it aliases
        const bump = vec2(0).toVar();
        // three scales, each rotated, so the tile never lines up with itself
        const layers = [
          { s: 1 / 46, a: 0.0, v: [0.0045, 0.0032], w: 0.55 },
          { s: 1 / 17, a: 2.1, v: [-0.010, 0.0065], w: 0.40 },
          { s: 1 / 6.2, a: 4.3, v: [0.016, -0.011], w: 0.30 },
        ];
        if (o.quality === 'low') layers.pop();
        for (const l of layers) {
          const ca = Math.cos(l.a), sa = Math.sin(l.a);
          const rx = world.x.mul(ca).sub(world.z.mul(sa));
          const rz = world.x.mul(sa).add(world.z.mul(ca));
          const uv = vec2(rx, rz).mul(l.s).add(vec2(l.v[0], l.v[1]).mul(U.time));
          const t = dTex.uv(uv).xy.mul(2).sub(1);
          bump.addAssign(t.mul(l.w));
        }
        N.assign(normalize(N.add(vec3(bump.x, 0, bump.y).mul(near.mul(0.30).add(0.04)))));
      }

      /* ------------------------------------------------ depth colour ---- */
      const col = mix(U.mid, U.deep, smoothstep(float(0.25), float(1.15), shelfT)).toVar();
      col.assign(mix(U.shelf, col, smoothstep(float(0.05), float(0.66), shelfT)));
      col.assign(mix(U.sand, col, smoothstep(float(-0.01), float(0.13), shelfT)));

      // the turquoise is brightest where the shelf is shallowest, as in the painting
      const glow = oneMinus(smoothstep(float(0.0), float(0.5), shelfT)).mul(0.10);
      col.addAssign(U.shelf.mul(glow));

      // Painted seas are never one flat blue: a very low frequency mottle keeps
      // the open water alive without reading as noise.
      const mTex = texture(this.cloudTex);
      const mottle = o.quality === 'low'
        ? mTex.uv(world.xz.mul(1 / 700).add(U.time.mul(0.00004))).x
        : mTex.uv(world.xz.mul(1 / 1450).add(U.time.mul(0.00004))).x
          .add(mTex.uv(world.xz.mul(1 / 430).add(vec2(0.31, 0.77))).x).mul(0.5);
      col.mulAssign(mix(float(0.93), float(1.09), mottle));

      /* --------------------------------------------- sky and sun light ---- */
      const fres = pow(oneMinus(saturate(dot(N, V))), 5.0).mul(0.88).add(0.035).toVar();
      // a lighter sky reflection: at the page's steeper camera the full amount
      // drew pale streaks along every swell
      col.assign(mix(col, U.skyColor, fres.mul(0.2)));

      const sun = U.sunDir;
      const H = normalize(sun.add(V));
      // the painting has a soft sheen on the sea, not a field of white sparks;
      // under ACES at 1.22 the old strength blew whole wave faces out to white
      // (with bloom on top, even half the old strength still sparkled across whole
      //  swaths of sea; the glint now stays a glint)
      // the broad lobe painted the sun's whole reflection zone as pale streaks along
      // the ripple detail; the painting's sea has none, so only a faint pin glint stays
      const spec = pow(saturate(dot(N, H)), 300.0).mul(0.06);
      const wide = float(0.0);
      col.addAssign(U.sunColor.mul(spec.add(wide)));

      // the lit face of every wave, which is what makes the swell readable
      col.addAssign(U.sunColor.mul(saturate(dot(N, sun)).mul(0.025)));

      /* ------------------------------------------------- cloud shadows ---- */
      const cTex = texture(this.cloudTex);
      const cuv = world.xz.mul(U.cloudScale).add(U.cloudDrift.mul(U.time).mul(U.cloudScale));
      const cloud = cTex.uv(cuv).x.mul(0.65).add(cTex.uv(cuv.mul(0.37).add(vec2(0.3, 0.7))).x.mul(0.35));
      const blot = smoothstep(U.cloudCoverage, U.cloudCoverage.add(0.22), cloud).mul(U.cloudShadow);
      col.assign(mix(col, col.mul(vec3(0.62, 0.72, 0.86)), blot));

      /* --------------------------------------------------------- surf ---- */
      // The foam line surges with the swell and wobbles with a slow noise, so no
      // island wears a perfect circle of white.
      const wob = sin(world.x.mul(0.26).add(world.z.mul(0.17)).add(U.time.mul(0.35)))
        .mul(sin(world.x.mul(-0.11).add(world.z.mul(0.19)).add(U.time.mul(0.21))).mul(0.7).add(0.5))
        .mul(2.0);
      const d = dist.add(w.height.mul(2.2)).add(wob).toVar();

      // the swell piles up on the windward shore and leaves the lee side quieter
      const facing = saturate(shore.z.mul(SWELL_DIR[0]).add(shore.w.mul(SWELL_DIR[1])))
        .mul(0.75).add(0.45).toVar();

      // collar: white where the water meets rock and sand, broken up along the shore
      const ragged = sin(world.x.mul(0.55).add(world.z.mul(0.47)).add(U.time.mul(0.5)))
        .mul(0.22).add(0.86);
      const collar = oneMinus(smoothstep(float(-0.4), float(1.5), d)).mul(ragged).mul(facing.mul(0.78).add(0.22)).toVar();
      // breakers: lines marching shoreward, fading out over the shelf
      const roll = fract(d.mul(1 / 13.0).add(U.time.mul(0.075))).toVar();
      const line = smoothstep(float(0.74), float(0.95), roll).mul(oneMinus(smoothstep(float(0.95), float(1.0), roll)));
      const band = oneMinus(smoothstep(float(0.5), float(9.5), d)).mul(saturate(d.mul(0.5)));
      const breakers = line.mul(band).mul(facing).mul(0.5);
      const foam = saturate(max(collar, breakers)).mul(saturate(dist.add(30).mul(0.12))).toVar();

      col.assign(mix(col, U.foam, foam.mul(0.88)));

      /* --------------------------------------------------------- haze ---- */
      const fogAmt = oneMinus(exp(U.fogDensity.mul(viewDist).mul(U.fogDensity.mul(viewDist)).negate()));
      col.assign(mix(col, U.horizon, saturate(fogAmt)));

      return vec4(col, 1.0);
    })();

    const material = new NodeMaterial();
    material.vertexNode = vertexNode;
    material.fragmentNode = fragmentNode;
    material.side = FrontSide;
    material.fog = false;
    this.material = material;

    const rings = Math.max(24, Math.round(o.segments));
    const sectors = Math.max(48, Math.min(512, Math.round(o.segments * 2)));
    this.geometry = radialGrid(rings, sectors, 6, o.size * 1.55, 2.6);
    this.mesh = new Mesh(this.geometry, material);
    this.mesh.frustumCulled = false;
    this.mesh.renderOrder = -1;
    this.mesh.name = 'OceanSurface';
    this.object3D.position.y = o.seaLevel;
    this.object3D.add(this.mesh);

    this._tmp = new Vector3();
  }

  /* The sun the water answers to. `dir` points towards the sun. */
  setSun(dir, colorHex) {
    this.u.sunDir.value.copy(dir).normalize();
    if (colorHex !== undefined) this.u.sunColor.value.set(colorHex);
    return this;
  }

  /* Tie the water's shadow blots to a Clouds instance (or any {scaleMeters,
     driftX, driftZ, coverage, strength}). Call with null to switch them off. */
  setCloudShadow(cfg) {
    if (!cfg) { this.u.cloudShadow.value = 0; return this; }
    this.u.cloudShadow.value = cfg.strength ?? 0.5;
    this.u.cloudScale.value = 1 / (cfg.scaleMeters ?? 620);
    this.u.cloudDrift.value.set(cfg.driftX ?? -0.9, cfg.driftZ ?? 0.35);
    this.u.cloudCoverage.value = cfg.coverage ?? 0.42;
    return this;
  }

  /* Haze: give it the same colour and density as the scene fog. */
  setHaze(colorHex, density) {
    this.u.horizon.value.set(colorHex);
    if (density !== undefined) this.u.fogDensity.value = density;
    return this;
  }

  update(dt, elapsed, camera) {
    this.u.time.value = elapsed;
    if (this.options.follow && camera) {
      // keep the dense middle of the disc under the camera, in the group's space
      this._tmp.copy(camera.position);
      this.object3D.worldToLocal(this._tmp);
      this.mesh.position.set(this._tmp.x, 0, this._tmp.z);
    }
  }

  dispose() {
    this.geometry.dispose();
    this.material.dispose();
    this.field.texture.dispose();
    this.cloudTex.dispose();
    if (this.detailTex) this.detailTex.dispose();
  }
}

export default Ocean;
