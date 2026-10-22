/* Props for the archipelago: boats, harbour buildings, piers, ruins and forest.

   Every .glb under assets/props/ is already one flat-shaded mesh with a baked
   COLOR_0 attribute and a single material, so loading is just "merge the parts and
   keep position/normal/color" -- the same preparation site/kit.js does for the
   Kenney Nature Kit, and the geometries coming out of here can be fed to that
   module's Instancer unchanged.

   Conventions (all models): metres, Y up, facing +Z, pivot on the ground at the
   base. The ONE exception is the pier modules, where y = 0 is the walking surface
   and the piles hang below it to about y = -2.3, so a run of deck can be laid at a
   constant height over the water. layoutPier() already accounts for that.

   Sources and licences: assets/props/provenance.json. */
import * as THREE from 'three';
import { GLTFLoader } from 'three/gltf';
import * as BufferGeometryUtils from 'three/bufferutils';

/* Resolved against this module rather than against the page, so the same import
   works from site/index.html and from a page nested deeper. */
export const PROPS_PATH = (() => {
  try {
    return new URL('assets/props/', import.meta.url).href;
  } catch (e) {
    return 'assets/props/';
  }
})();

const KEEP = ['position', 'normal', 'color'];
const WHITE = new THREE.Color(0xffffff);

/* Named groups, so a caller can ask for "the harbour" without listing files. */
export const PROP_SETS = {
  boats: ['boat_sail_a', 'boat_sail_b', 'boat_sail_c'],
  buildings: ['house_white_a', 'house_white_b', 'house_white_c',
    'lighthouse', 'watchtower', 'stilt_hut'],
  harbour: ['pier_straight', 'pier_end', 'pier_corner',
    'mooring_post', 'mooring_post_stone'],
  ruins: ['ruin_arch', 'ruin_arch_broken', 'ruin_column',
    'ruin_column_broken', 'ruin_wall'],
  conifers: ['conifer_xl', 'conifer_l', 'conifer_m', 'conifer_s', 'conifer_round',
    'conifer_spire_xl', 'conifer_spire_l', 'conifer_spire_m', 'conifer_spire_s'],
  palms: ['palm_tall', 'palm_bend', 'palm_short',
    'palm_fan_tall', 'palm_fan_mid', 'palm_fan_short'],
  scatter: ['bush_round', 'bush_small', 'rock_mossy'],
};

export const ALL_PROPS = Object.values(PROP_SETS).flat();

/* Rough footprint radius in metres, used to keep scattered props from overlapping
   and to keep a forest off the very edge of a cliff. */
export const PROP_RADIUS = {
  conifer_xl: 1.9, conifer_l: 1.6, conifer_m: 1.3, conifer_s: 0.9, conifer_round: 1.5,
  conifer_spire_xl: 2.0, conifer_spire_l: 1.6, conifer_spire_m: 1.2, conifer_spire_s: 0.8,
  palm_tall: 1.9, palm_bend: 1.7, palm_short: 1.3,
  palm_fan_tall: 2.1, palm_fan_mid: 1.7, palm_fan_short: 1.3,
  bush_round: 0.7, bush_small: 0.5, rock_mossy: 0.8,
};

/* ------------------------------------------------------------------ loading */

function mergeParts(root) {
  const parts = [];
  root.updateWorldMatrix(true, true);
  root.traverse((o) => {
    if (!o.isMesh) return;
    const geo = o.geometry.index ? o.geometry.toNonIndexed() : o.geometry.clone();
    geo.applyMatrix4(o.matrixWorld);
    for (const name of Object.keys(geo.attributes)) {
      if (!KEEP.includes(name)) geo.deleteAttribute(name);
    }
    if (!geo.attributes.normal) geo.computeVertexNormals();
    if (!geo.attributes.color) {
      // A model without COLOR_0 would otherwise render black under a
      // vertexColors material, so fall back to the material colour.
      const m = Array.isArray(o.material) ? o.material[0] : o.material;
      const col = (m && m.color) ? m.color : WHITE;
      const n = geo.attributes.position.count;
      const c = new Float32Array(n * 3);
      for (let i = 0; i < n; i++) { c[i * 3] = col.r; c[i * 3 + 1] = col.g; c[i * 3 + 2] = col.b; }
      geo.setAttribute('color', new THREE.BufferAttribute(c, 3));
    } else if (geo.attributes.color.itemSize === 4) {
      const src = geo.attributes.color;
      const c = new Float32Array(src.count * 3);
      for (let i = 0; i < src.count; i++) {
        c[i * 3] = src.getX(i); c[i * 3 + 1] = src.getY(i); c[i * 3 + 2] = src.getZ(i);
      }
      geo.setAttribute('color', new THREE.BufferAttribute(c, 3));
    }
    geo.clearGroups();
    parts.push(geo);
  });
  if (!parts.length) return null;
  return parts.length === 1 ? parts[0] : BufferGeometryUtils.mergeGeometries(parts, false);
}

/* loadProps(['boat_sail_a', ...], onStep) -> { name: BufferGeometry }
   Names may also be set names ('boats', 'forest'), or omitted for everything.
   Each geometry is instance-ready: one buffer, baked `color`, bounding box set. */
export async function loadProps(names, onStep) {
  let list = names && names.length ? names : ALL_PROPS;
  list = list.flatMap((n) => (PROP_SETS[n] ? PROP_SETS[n] : [n]));
  list = [...new Set(list)];

  const loader = new GLTFLoader();
  const out = {};
  await Promise.all(list.map(async (name) => {
    try {
      const gltf = await loader.loadAsync(PROPS_PATH + name + '.glb');
      const geo = mergeParts(gltf.scene);
      if (geo) {
        geo.computeBoundingBox();
        geo.computeBoundingSphere();
        out[name] = geo;
      }
    } catch (e) {
      console.warn('prop missing:', name, e.message);
    }
    if (onStep) onStep(name);
  }));
  return out;
}

export function propsMaterial(opts = {}) {
  return new THREE.MeshStandardMaterial({
    vertexColors: true, flatShading: true, roughness: 1, metalness: 0, ...opts,
  });
}

/* Collects placements per prop and commits them as one InstancedMesh each.
   Interchangeable with the Instancer in kit.js. */
export class PropInstancer {
  constructor(props, material) {
    this.props = props;
    this.material = material || propsMaterial();
    this.buckets = new Map();
  }

  place(name, matrix, tint) {
    if (!this.props[name]) return this;
    if (!this.buckets.has(name)) this.buckets.set(name, []);
    this.buckets.get(name).push({ matrix: matrix.clone(), tint: tint ? tint.clone() : null });
    return this;
  }

  /* Convenience for the placement objects the layout helpers return. */
  placeAll(list) {
    const m = new THREE.Matrix4();
    for (const p of list) {
      matrixOf(p, m);
      this.place(p.name, m, p.tint);
    }
    return this;
  }

  commit(scene) {
    const meshes = [];
    for (const [name, list] of this.buckets) {
      const mesh = new THREE.InstancedMesh(this.props[name], this.material, list.length);
      const tinted = list.some((e) => e.tint);
      list.forEach((e, i) => {
        mesh.setMatrixAt(i, e.matrix);
        if (tinted) mesh.setColorAt(i, e.tint || WHITE);
      });
      mesh.instanceMatrix.needsUpdate = true;
      if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
      mesh.castShadow = true;
      mesh.receiveShadow = true;
      mesh.frustumCulled = false;
      scene.add(mesh);
      meshes.push(mesh);
    }
    this.buckets.clear();
    return meshes;
  }
}

const _q = new THREE.Quaternion();
const _e = new THREE.Euler();
const _v = new THREE.Vector3();
const _s = new THREE.Vector3();

/* placement -> Matrix4. A placement is { name, x, y, z, rotationY, scale, tiltX, tiltZ }. */
export function matrixOf(p, out) {
  const m = out || new THREE.Matrix4();
  _e.set(p.tiltX || 0, p.rotationY || 0, p.tiltZ || 0, 'YXZ');
  _q.setFromEuler(_e);
  _v.set(p.x, p.y, p.z);
  const s = p.scale === undefined ? 1 : p.scale;
  _s.set(s, s, s);
  return m.compose(_v, _q, _s);
}

/* ------------------------------------------------------------------- random */

export function makeRng(seed = 1) {
  let a = (seed >>> 0) || 1;
  return function rng() {
    a |= 0; a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function pick(rng, entries) {
  let total = 0;
  for (const e of entries) total += (e.weight === undefined ? 1 : e.weight);
  let r = rng() * total;
  for (const e of entries) {
    r -= (e.weight === undefined ? 1 : e.weight);
    if (r <= 0) return e;
  }
  return entries[entries.length - 1];
}

/* ------------------------------------------------------------------- forest */

/* The default planting rules, in metres above sea level. They are what make the
   island read like the painting: palms on the beach, a dark conifer belt over the
   middle slopes, bare rock on the steep faces and above the treeline. */
export const DEFAULT_SPECIES = [
  { name: 'palm_fan_tall', weight: 2, minY: 0.6, maxY: 7, maxSlope: 0.30, scale: [0.85, 1.15] },
  { name: 'palm_tall', weight: 2, minY: 0.6, maxY: 7, maxSlope: 0.30, scale: [0.85, 1.2] },
  { name: 'palm_bend', weight: 2, minY: 0.4, maxY: 6, maxSlope: 0.34, scale: [0.85, 1.2] },
  { name: 'palm_fan_mid', weight: 2, minY: 0.5, maxY: 8, maxSlope: 0.32, scale: [0.85, 1.2] },
  { name: 'palm_short', weight: 1.5, minY: 0.3, maxY: 6, maxSlope: 0.38, scale: [0.8, 1.2] },
  { name: 'palm_fan_short', weight: 1.5, minY: 0.3, maxY: 6, maxSlope: 0.38, scale: [0.8, 1.2] },

  { name: 'conifer_spire_xl', weight: 1.4, minY: 6, maxY: 46, maxSlope: 0.52, scale: [0.85, 1.15] },
  { name: 'conifer_xl', weight: 1.2, minY: 7, maxY: 46, maxSlope: 0.50, scale: [0.85, 1.15] },
  { name: 'conifer_spire_l', weight: 2.6, minY: 4, maxY: 52, maxSlope: 0.58, scale: [0.8, 1.2] },
  { name: 'conifer_l', weight: 2.4, minY: 4, maxY: 52, maxSlope: 0.58, scale: [0.8, 1.2] },
  { name: 'conifer_round', weight: 1.4, minY: 4, maxY: 44, maxSlope: 0.56, scale: [0.85, 1.15] },
  { name: 'conifer_spire_m', weight: 2.6, minY: 3, maxY: 58, maxSlope: 0.66, scale: [0.8, 1.25] },
  { name: 'conifer_m', weight: 2.2, minY: 3, maxY: 58, maxSlope: 0.66, scale: [0.8, 1.25] },
  { name: 'conifer_spire_s', weight: 1.8, minY: 2, maxY: 64, maxSlope: 0.78, scale: [0.8, 1.3] },
  { name: 'conifer_s', weight: 1.4, minY: 2, maxY: 64, maxSlope: 0.78, scale: [0.8, 1.3] },

  { name: 'bush_round', weight: 2.2, minY: 0.4, maxY: 60, maxSlope: 0.8, scale: [0.8, 1.4] },
  { name: 'bush_small', weight: 2.6, minY: 0.2, maxY: 60, maxSlope: 0.9, scale: [0.8, 1.5] },
  { name: 'rock_mossy', weight: 1.0, minY: 0.2, maxY: 70, maxSlope: 1.0, scale: [0.5, 1.5] },
];

/* Default density curve: thin on the beach, thickest on the lower-middle slopes,
   thinning out again towards the summit, and nothing on near-vertical rock. */
export function defaultDensity(y, slope) {
  if (y < 0.25) return 0;
  const alt = y < 2 ? y / 2
    : y < 10 ? 1
      : y < 40 ? 1 - (y - 10) / 30 * 0.45
        : Math.max(0, 1 - (y - 40) / 28);
  const steep = slope > 1.05 ? 0 : 1 - Math.pow(Math.min(1, slope / 1.05), 2.1);
  return Math.max(0, alt) * steep;
}

function gradient(sampleHeight, x, z, h) {
  const d = h || 0.75;
  const dx = (sampleHeight(x + d, z) - sampleHeight(x - d, z)) / (2 * d);
  const dz = (sampleHeight(x, z + d) - sampleHeight(x, z - d)) / (2 * d);
  return Math.hypot(dx, dz);
}

/* scatterForest(options) -> [placement]

   options:
     sampleHeight(x, z)   required; terrain height in metres, <= 0 means water
     bounds               {minX, maxX, minZ, maxZ}  or  {cx, cz, radius}
     count                how many candidates to try (default 600)
     density(y, slope)    0..1 chance of planting; defaults to defaultDensity
     species              defaults to DEFAULT_SPECIES
     seed, spacing        spacing multiplies PROP_RADIUS (default 1)
     mask(x, z)           optional; return false to keep an area clear (paths, town)
     jitterY              how far a trunk may sink into the ground (default 0.12)

   Candidates are laid on a jittered grid and rejected against what is already
   planted, which gives an even cover without a real Poisson pass. */
export function scatterForest(options) {
  const o = options || {};
  const sampleHeight = o.sampleHeight;
  if (typeof sampleHeight !== 'function') throw new Error('scatterForest needs sampleHeight(x, z)');
  const density = o.density || defaultDensity;
  const species = o.species || DEFAULT_SPECIES;
  const rng = makeRng(o.seed === undefined ? 7 : o.seed);
  const spacing = o.spacing === undefined ? 1 : o.spacing;
  const jitterY = o.jitterY === undefined ? 0.12 : o.jitterY;

  let minX; let maxX; let minZ; let maxZ; let circle = null;
  const b = o.bounds || {};
  if (b.radius !== undefined) {
    circle = { cx: b.cx || 0, cz: b.cz || 0, r: b.radius };
    minX = circle.cx - circle.r; maxX = circle.cx + circle.r;
    minZ = circle.cz - circle.r; maxZ = circle.cz + circle.r;
  } else {
    minX = b.minX === undefined ? -100 : b.minX;
    maxX = b.maxX === undefined ? 100 : b.maxX;
    minZ = b.minZ === undefined ? -100 : b.minZ;
    maxZ = b.maxZ === undefined ? 100 : b.maxZ;
  }

  const count = o.count === undefined ? 600 : o.count;
  const cols = Math.max(1, Math.round(Math.sqrt(count * (maxX - minX) / Math.max(1e-3, maxZ - minZ))));
  const rows = Math.max(1, Math.ceil(count / cols));
  const cw = (maxX - minX) / cols;
  const ch = (maxZ - minZ) / rows;

  // uniform grid for the overlap test, cell size from the biggest footprint
  const cell = 4;
  const grid = new Map();
  const key = (ix, iz) => ix + ',' + iz;
  const fits = (x, z, r) => {
    const ix = Math.floor(x / cell); const iz = Math.floor(z / cell);
    for (let a = ix - 1; a <= ix + 1; a++) {
      for (let c = iz - 1; c <= iz + 1; c++) {
        const list = grid.get(key(a, c));
        if (!list) continue;
        for (const p of list) {
          const need = (r + p.r) * spacing;
          const dx = p.x - x; const dz = p.z - z;
          if (dx * dx + dz * dz < need * need) return false;
        }
      }
    }
    return true;
  };
  const remember = (x, z, r) => {
    const k = key(Math.floor(x / cell), Math.floor(z / cell));
    if (!grid.has(k)) grid.set(k, []);
    grid.get(k).push({ x, z, r });
  };

  const out = [];
  for (let gz = 0; gz < rows; gz++) {
    for (let gx = 0; gx < cols; gx++) {
      const x = minX + (gx + rng()) * cw;
      const z = minZ + (gz + rng()) * ch;
      if (circle) {
        const dx = x - circle.cx; const dz = z - circle.cz;
        if (dx * dx + dz * dz > circle.r * circle.r) continue;
      }
      if (o.mask && !o.mask(x, z)) continue;
      const y = sampleHeight(x, z);
      if (!(y > 0)) continue;
      const slope = gradient(sampleHeight, x, z, o.sampleStep);
      if (rng() > density(y, slope)) continue;

      const ok = species.filter((sp) => y >= (sp.minY === undefined ? -1e9 : sp.minY)
        && y <= (sp.maxY === undefined ? 1e9 : sp.maxY)
        && slope <= (sp.maxSlope === undefined ? 1e9 : sp.maxSlope));
      if (!ok.length) continue;
      const sp = pick(rng, ok);
      const lo = sp.scale ? sp.scale[0] : 0.85;
      const hi = sp.scale ? sp.scale[1] : 1.15;
      const scale = lo + rng() * (hi - lo);
      const r = (PROP_RADIUS[sp.name] || 1) * scale;
      if (!fits(x, z, r)) continue;
      remember(x, z, r);
      out.push({
        name: sp.name,
        x,
        y: y - rng() * jitterY,
        z,
        rotationY: rng() * Math.PI * 2,
        scale,
        // a trunk leans a little with the hill, which hides the flat pivot
        tiltX: (rng() - 0.5) * 0.05 + 0,
        tiltZ: (rng() - 0.5) * 0.05,
      });
    }
  }
  return out;
}

/* ------------------------------------------------------------------ harbour */

/* layoutPier(options) -> { placements, deckPoints, tip }

   Walks a pier out from a shore point. The pier models put y = 0 at the walking
   surface with the piles hanging below, so every deck piece is placed at deckY no
   matter how deep the water is under it.

   options:
     from       {x, z}    where the pier meets the shore
     angle      radians, the direction it walks out (0 = +Z, matching prop facing)
     length     metres (rounded to whole 2 m tiles)
     deckY      walking height above sea level (default 1.1)
     end        true to cap the far end with pier_end (ladder + bollards)
     corner     optional { atTile, angle } to turn the pier partway along
     bollardEvery  tiles between mooring posts (0 for none)
     bollard    which post to use (default alternates wood and stone)
     seed */
export const PIER_TILE = 2.0;

export function layoutPier(options) {
  const o = options || {};
  const from = o.from || { x: 0, z: 0 };
  const angle = o.angle === undefined ? 0 : o.angle;
  const deckY = o.deckY === undefined ? 1.1 : o.deckY;
  const tiles = Math.max(1, Math.round((o.length === undefined ? 12 : o.length) / PIER_TILE));
  const rng = makeRng(o.seed === undefined ? 3 : o.seed);
  const every = o.bollardEvery === undefined ? 3 : o.bollardEvery;

  const placements = [];
  const deckPoints = [];
  let a = angle;
  let x = from.x;
  let z = from.z;
  const step = (ang, d) => { x += Math.sin(ang) * d; z += Math.cos(ang) * d; };

  // start half a tile out so the first plank meets the shore
  step(a, PIER_TILE * 0.5);
  for (let i = 0; i < tiles; i++) {
    const last = i === tiles - 1;
    const turning = o.corner && o.corner.atTile === i;
    const name = turning ? 'pier_corner' : (last && o.end !== false ? 'pier_end' : 'pier_straight');
    placements.push({ name, x, y: deckY, z, rotationY: a });
    deckPoints.push({ x, y: deckY, z });
    if (every > 0 && !last && i % every === every - 1) {
      const side = rng() < 0.5 ? 1 : -1;
      placements.push({
        name: rng() < 0.55 ? 'mooring_post' : 'mooring_post_stone',
        x: x + Math.cos(a) * side * 0.78,
        y: deckY,
        z: z - Math.sin(a) * side * 0.78,
        rotationY: rng() * Math.PI * 2,
        scale: 0.92 + rng() * 0.2,
      });
    }
    if (turning) a += (o.corner.angle === undefined ? Math.PI / 2 : o.corner.angle);
    if (!last) step(a, PIER_TILE);
  }
  return { placements, deckPoints, tip: { x, y: deckY, z }, angle: a };
}

/* mooredBoats(pier, options) -> [placement]
   Ties boats alongside the deck points of a pier, alternating sides and facing
   roughly along the pier. Boat pivots are at the waterline, so y is sea level. */
export function mooredBoats(pier, options) {
  const o = options || {};
  const rng = makeRng(o.seed === undefined ? 11 : o.seed);
  const names = o.names || PROP_SETS.boats;
  const seaY = o.seaY === undefined ? 0 : o.seaY;
  const offset = o.offset === undefined ? 2.5 : o.offset;
  const every = o.every === undefined ? 2 : o.every;
  const out = [];
  const pts = pier.deckPoints || [];
  for (let i = 1; i < pts.length - 1; i += every) {
    if (rng() < (o.skip === undefined ? 0.25 : o.skip)) continue;
    const p = pts[i];
    const q = pts[i + 1] || pts[i - 1];
    const a = Math.atan2(q.x - p.x, q.z - p.z);
    const side = (i % 4 < 2) ? 1 : -1;
    out.push({
      name: names[Math.floor(rng() * names.length)],
      x: p.x + Math.cos(a) * side * offset,
      y: seaY,
      z: p.z - Math.sin(a) * side * offset,
      rotationY: a + (rng() - 0.5) * 0.22 + (side > 0 ? 0 : Math.PI) * 0,
      scale: 0.92 + rng() * 0.18,
      tiltZ: (rng() - 0.5) * 0.05,
    });
  }
  return out;
}

/* layoutHarbourTown(options) -> [placement]
   A row of houses stood along a shoreline, gable ends to the water, with the
   lighthouse on the seaward end. `shoreAt(t)` returns {x, z, angle} for t in 0..1;
   sampleHeight gives the ground. */
export function layoutHarbourTown(options) {
  const o = options || {};
  const shoreAt = o.shoreAt;
  const sampleHeight = o.sampleHeight || (() => 0);
  if (typeof shoreAt !== 'function') throw new Error('layoutHarbourTown needs shoreAt(t)');
  const rng = makeRng(o.seed === undefined ? 5 : o.seed);
  const n = o.count === undefined ? 7 : o.count;
  const back = o.setback === undefined ? 5.5 : o.setback;
  const kinds = o.kinds || ['house_white_a', 'house_white_a', 'house_white_b', 'house_white_c'];
  const out = [];
  for (let i = 0; i < n; i++) {
    const t = (i + 0.5) / n;
    const s = shoreAt(t);
    const a = s.angle === undefined ? 0 : s.angle;
    const d = back + rng() * (o.setbackJitter === undefined ? 4 : o.setbackJitter)
      + (i % 2) * 2.2;
    const x = s.x + Math.sin(a) * d;
    const z = s.z + Math.cos(a) * d;
    out.push({
      name: kinds[Math.floor(rng() * kinds.length)],
      x,
      y: sampleHeight(x, z),
      z,
      rotationY: a + Math.PI + (rng() - 0.5) * 0.30,
      scale: 0.92 + rng() * 0.22,
    });
  }
  if (o.lighthouse !== false) {
    const s = shoreAt(o.lighthouseAt === undefined ? 0.04 : o.lighthouseAt);
    const a = s.angle === undefined ? 0 : s.angle;
    const x = s.x + Math.sin(a) * (back * 0.5);
    const z = s.z + Math.cos(a) * (back * 0.5);
    out.push({ name: 'lighthouse', x, y: sampleHeight(x, z), z, rotationY: a + Math.PI });
  }
  return out;
}

/* scatterRuins(options) -> [placement]
   Drops an arch-and-columns site on a flattish patch, loosely aligned, the way the
   ruins sit on the island sheet. */
export function scatterRuins(options) {
  const o = options || {};
  const sampleHeight = o.sampleHeight || (() => 0);
  const rng = makeRng(o.seed === undefined ? 17 : o.seed);
  const cx = o.x === undefined ? 0 : o.x;
  const cz = o.z === undefined ? 0 : o.z;
  const a0 = o.angle === undefined ? rng() * Math.PI : o.angle;
  const r = o.radius === undefined ? 9 : o.radius;
  const pieces = o.pieces || [
    { name: 'ruin_arch', weight: 1.2 },
    { name: 'ruin_arch_broken', weight: 1 },
    { name: 'ruin_column', weight: 1.6 },
    { name: 'ruin_column_broken', weight: 1.6 },
    { name: 'ruin_wall', weight: 0.9 },
  ];
  const n = o.count === undefined ? 6 : o.count;
  const out = [];
  for (let i = 0; i < n; i++) {
    const t = i / n;
    const ang = a0 + t * Math.PI * 2 * (o.spread === undefined ? 1 : o.spread);
    const rad = r * (0.25 + rng() * 0.75);
    const x = cx + Math.cos(ang) * rad;
    const z = cz + Math.sin(ang) * rad;
    const sp = pick(rng, pieces);
    out.push({
      name: sp.name,
      x,
      y: sampleHeight(x, z) - rng() * 0.2,
      z,
      rotationY: a0 + (rng() - 0.5) * 0.5 + (rng() < 0.4 ? Math.PI / 2 : 0),
      scale: 0.9 + rng() * 0.3,
      tiltX: (rng() - 0.5) * 0.07,
      tiltZ: (rng() - 0.5) * 0.07,
    });
  }
  return out;
}
