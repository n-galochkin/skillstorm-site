/* Islands laid out of the Nature Kit's cliff tileset.

   The kit is a tileset, not a pile of cubes: every piece has its cliff face on +Z,
   footprint 1x1, pivot on the floor. So a cell looks at its four neighbours and picks
   a wall, an outer corner or an inner corner, and the wall is stretched once to the
   full height of the column — one continuous face, not a stack of blocks. Inside the
   coastline there is no geometry at all, only a flat grass tile. */
import * as THREE from 'three';
import { heightFieldFor } from './islands.js';

export const CELL = 1.6;               // metres per tile

const PINES = ['tree_pineTallA', 'tree_pineTallB', 'tree_pineTallC', 'tree_pineRoundA',
  'tree_pineRoundC', 'tree_pineSmallA', 'tree_pineSmallB', 'tree_pineDefaultA'];
const PALMS = ['tree_palm', 'tree_palmBend', 'tree_palmTall', 'tree_palmShort', 'tree_palmDetailedTall'];
const BROADLEAF = ['tree_default', 'tree_oak', 'tree_blocks', 'tree_thin', 'tree_small'];
const ROCKS = ['rock_largeA', 'rock_largeB', 'rock_largeC', 'rock_smallA', 'rock_smallB', 'rock_smallC'];
const SCRUB = ['grass', 'grass_large', 'plant_bush', 'plant_bushLarge', 'flower_redA', 'flower_yellowA'];

const SAND = new THREE.Color(0xeedcaa);
const GRASS_TINT = new THREE.Color(0xffffff);

// directions, in the order used for the neighbour mask
const DIRS = [
  { dx: 0, dz: 1, yaw: 0 },            // +Z, the face the pieces are modelled on
  { dx: 1, dz: 0, yaw: Math.PI / 2 },
  { dx: 0, dz: -1, yaw: Math.PI },
  { dx: -1, dz: 0, yaw: -Math.PI / 2 },
];
// an outer corner covers {-X, +Z}; these yaws carry that pair onto each other pair
const CORNER_YAW = { '0,3': 0, '0,1': Math.PI / 2, '1,2': Math.PI, '2,3': -Math.PI / 2 };

function pick(list, r) { return list[Math.floor(r * list.length) % list.length]; }

export function blockHeightFor(spec) {
  const field = heightFieldFor(spec);
  const step = CELL;
  return (lx, lz) => {
    const h = field(lx, lz);
    if (h < 0.1) return h;
    return Math.max(1, Math.round(h / step)) * step;
  };
}

export function buildBlockIsland(spec, inst, rngSeed = 1) {
  const field = heightFieldFor(spec);
  const reach = Math.ceil((spec.radius * 1.35) / CELL);
  const m = new THREE.Matrix4();
  const q = new THREE.Quaternion();
  const up = new THREE.Vector3(0, 1, 0);
  const pos = new THREE.Vector3();
  const scl = new THREE.Vector3();

  const levels = new Map();
  const key = (i, j) => i + ',' + j;
  let maxLevel = 1;
  for (let i = -reach; i <= reach; i++) {
    for (let j = -reach; j <= reach; j++) {
      const h = field(i * CELL, j * CELL);
      if (h < 0.25) continue;
      const lv = THREE.MathUtils.clamp(Math.round(h / CELL), 1, 12);
      levels.set(key(i, j), lv);
      maxLevel = Math.max(maxLevel, lv);
    }
  }

  let rnd = (rngSeed * 9301 + 49297) % 233280;
  const rand = () => { rnd = (rnd * 9301 + 49297) % 233280; return rnd / 233280; };

  const wall = spec.stone ? 'cliff_large_stone' : 'cliff_large_rock';
  const thinWall = spec.stone ? 'cliff_stone' : 'cliff_rock';
  const corner = spec.stone ? 'cliff_corner_stone' : 'cliff_corner_rock';
  const innerCorner = spec.stone ? 'cliff_cornerInner_stone' : 'cliff_cornerInner_rock';
  const trees = spec.palms ? PALMS : (spec.broadleaf ? BROADLEAF : PINES);

  for (const [k, lv] of levels) {
    const [i, j] = k.split(',').map(Number);
    const wx = spec.pos[0] + i * CELL;
    const wz = spec.pos[1] + j * CELL;
    const top = lv * CELL;

    // which sides look out over lower ground
    const open = [];
    for (let d = 0; d < 4; d++) {
      const n = levels.get(key(i + DIRS[d].dx, j + DIRS[d].dz)) || 0;
      if (n < lv) open.push(d);
    }

    const beach = lv <= 1;
    const tint = beach ? SAND : GRASS_TINT;

    // the flat top of the column
    q.setFromAxisAngle(up, 0);
    pos.set(wx, top, wz);
    scl.set(CELL, CELL, CELL);
    m.compose(pos, q, scl);
    inst.place('ground_grass', m, tint);

    if (!open.length) continue;

    // how far down the face has to reach: to the tallest neighbour that is lower
    let drop = top;
    for (const d of open) {
      const n = levels.get(key(i + DIRS[d].dx, j + DIRS[d].dz)) || 0;
      drop = Math.min(drop, top - n * CELL);
    }
    drop = Math.max(drop, CELL);
    const base = top - drop;

    const pairKey = open.length === 2 ? [open[0], open[1]].sort((a, b) => a - b).join(',') : null;
    if (pairKey && CORNER_YAW[pairKey] !== undefined) {
      // two sides open and adjacent: one outer corner piece carries both faces
      q.setFromAxisAngle(up, CORNER_YAW[pairKey]);
      m.compose(pos.set(wx, base, wz), q, scl.set(CELL, drop, CELL));
      inst.place(corner, m, tint);
    } else {
      for (const d of open) {
        q.setFromAxisAngle(up, DIRS[d].yaw);
        m.compose(pos.set(wx, base, wz), q, scl.set(CELL, drop, CELL));
        inst.place(open.length >= 3 ? thinWall : wall, m, tint);
      }
    }

    // an inner corner where two solid neighbours meet but the diagonal is missing
    if (open.length === 0) continue;
    for (let d = 0; d < 4; d++) {
      const a = DIRS[d], b = DIRS[(d + 1) % 4];
      const sideA = levels.get(key(i + a.dx, j + a.dz)) || 0;
      const sideB = levels.get(key(i + b.dx, j + b.dz)) || 0;
      const diag = levels.get(key(i + a.dx + b.dx, j + a.dz + b.dz)) || 0;
      if (sideA >= lv && sideB >= lv && diag < lv) {
        q.setFromAxisAngle(up, CORNER_YAW[[d, (d + 1) % 4].sort((x, y) => x - y).join(',')] || 0);
        m.compose(pos.set(wx, base, wz), q, scl.set(CELL, drop, CELL));
        inst.place(innerCorner, m, tint);
      }
    }
  }

  // what grows on top, placed from the column list so nothing floats
  for (const [k, lv] of levels) {
    const [i, j] = k.split(',').map(Number);
    if (lv <= 1) continue;                                   // the beach stays open
    const wx = spec.pos[0] + i * CELL;
    const wz = spec.pos[1] + j * CELL;
    if (spec.arena && Math.hypot(i * CELL, j * CELL) < spec.radius * 0.6) continue;
    const r = rand();
    const put = (name, s, yScale = 1) => {
      q.setFromAxisAngle(up, rand() * Math.PI * 2);
      m.compose(
        pos.set(wx + (rand() - 0.5) * CELL * 0.7, lv * CELL, wz + (rand() - 0.5) * CELL * 0.7),
        q, scl.set(s, s * yScale, s),
      );
      inst.place(name, m, GRASS_TINT);
    };
    const highUp = lv / maxLevel > 0.45;
    if (r < (highUp ? 0.2 : 0.07)) put(pick(trees, rand()), (1.5 + rand() * 1.3), 0.9 + rand() * 0.4);
    else if (r < 0.19) put(pick(ROCKS, rand()), 0.7 + rand() * 0.6);
    else if (r < 0.44) put(pick(SCRUB, rand()), 0.8 + rand() * 0.7);
  }

  return { levels, field, maxLevel };
}

/* Per-island landmarks, standing on the blocks. */
export function placeFeature(spec, inst, heightAt) {
  const m = new THREE.Matrix4();
  const q = new THREE.Quaternion();
  const up = new THREE.Vector3(0, 1, 0);
  const white = new THREE.Color(0xffffff);
  const put = (name, lx, lz, s, rot = 0) => {
    const y = heightAt(lx, lz);
    if (y < 0.2) return;
    q.setFromAxisAngle(up, rot);
    m.compose(new THREE.Vector3(spec.pos[0] + lx, y, spec.pos[1] + lz), q, new THREE.Vector3(s, s, s));
    inst.place(name, m, white);
  };

  if (spec.feature === 'ruins') {
    put('statue_obelisk', 0, 0, 3.4);
    put('statue_column', -5, -3, 3, 0.3);
    put('statue_columnDamaged', 5, 2, 3, 1.1);
    put('statue_column', 2, 6, 2.6, 2.0);
    put('statue_ring', -2, 7, 2.4, 0.6);
  }
  if (spec.feature === 'village') {
    put('tent_smallOpen', -5, -3, 2.4, 0.4);
    put('tent_smallOpen', 4, 2, 2.1, 2.1);
    put('campfire_logs', 0, 0, 2.4, 0);
    put('fence_simple', -2, 5, 2.4, 0.2);
    put('log', 3, -5, 2.2, 1.3);
  }
  if (spec.feature === 'pier') {
    const dir = spec.pierAngle !== undefined ? spec.pierAngle : Math.PI * 0.3;
    const cx = Math.cos(dir), cz = Math.sin(dir);
    for (let d = spec.radius * 0.45; d < spec.radius * 1.2; d += 1.6) {
      q.setFromAxisAngle(up, dir);
      m.compose(new THREE.Vector3(spec.pos[0] + cx * d, 1.1, spec.pos[1] + cz * d),
        q, new THREE.Vector3(1.6, 1.6, 1.6));
      inst.place('bridge_center_wood', m, white);
    }
  }
}
