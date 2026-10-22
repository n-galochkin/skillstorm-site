/* Islands built to the game's own island art: a chunky low-poly disc — pale sand at
   the waterline, a faceted rock collar, a bright grass cap — with conifers on top and
   one feature per island that says what it is. */
import * as THREE from 'three';

/* ------------------------------------------------------------------ noise */
function hash2(x, y) {
  const s = Math.sin(x * 127.1 + y * 311.7) * 43758.5453;
  return s - Math.floor(s);
}
function noise2(x, y) {
  const ix = Math.floor(x), iy = Math.floor(y);
  const fx = x - ix, fy = y - iy;
  const sx = fx * fx * (3 - 2 * fx), sy = fy * fy * (3 - 2 * fy);
  const a = hash2(ix, iy), b = hash2(ix + 1, iy);
  const c = hash2(ix, iy + 1), d = hash2(ix + 1, iy + 1);
  return (a * (1 - sx) + b * sx) * (1 - sy) + (c * (1 - sx) + d * sx) * sy;
}
export function fbm(x, y, oct = 4) {
  let v = 0, amp = 0.5, fx = x, fy = y;
  for (let i = 0; i < oct; i++) { v += amp * noise2(fx, fy); fx *= 2.03; fy *= 2.03; amp *= 0.5; }
  return v;
}

export const PALETTE = {
  sand: 0xf0e2b6,
  grass: 0x7cc24a,
  grassDark: 0x4f9138,
  rock: 0x9299a1,
  rockDark: 0x6e757e,
  conifer: 0x3f8f4b,
  coniferDark: 0x2f6f3c,
  trunk: 0x6b4a2f,
  snow: 0xf2f6fa,
  lava: 0xff7a1a,
  lagoon: 0x56c8f0,
  lagoonDeep: 0x1d8fd1,
};

/* --------------------------------------------------------------- conifer */
// The art uses simple stacked cones. Built once, cloned per tree.
export function makeConifer() {
  const g = new THREE.Group();
  const trunk = new THREE.Mesh(
    new THREE.CylinderGeometry(0.17, 0.24, 1.1, 5),
    new THREE.MeshStandardMaterial({ color: PALETTE.trunk, flatShading: true, roughness: 1 }),
  );
  trunk.position.y = 0.55;
  g.add(trunk);
  const mat = new THREE.MeshStandardMaterial({ color: PALETTE.conifer, flatShading: true, roughness: 1 });
  const tiers = [[1.5, 1.15, 0.95], [1.15, 1.25, 1.85], [0.8, 1.2, 2.7]];
  for (const [r, h, y] of tiers) {
    const cone = new THREE.Mesh(new THREE.ConeGeometry(r, h, 6), mat);
    cone.position.y = y;
    g.add(cone);
  }
  return g;
}

export function makeRockSpire() {
  const geo = new THREE.ConeGeometry(1, 2.4, 5, 1);
  geo.scale(1, 1, 0.8);
  return new THREE.Mesh(geo, new THREE.MeshStandardMaterial({
    color: PALETTE.rockDark, flatShading: true, roughness: 1,
  }));
}

/* ----------------------------------------------------------------- island */
/* The start-screen painting is the brief: islands are flat-topped plateaus with
   sheer rock walls, their outlines broken into lobes, headlands and bays — never
   a disc. The field below is a union of a few overlapping lobes, so coves and
   peninsulas fall out of the shape instead of being added on top. */
function lobesFor(spec) {
  const { radius, seed } = spec;
  const n = spec.lobes || 3;
  const out = [{ x: 0, z: 0, r: radius * 0.62 }];
  for (let i = 1; i < n; i++) {
    const a = hash2(seed * 3.1 + i, seed * 7.7 - i) * Math.PI * 2;
    const d = radius * (0.3 + hash2(seed + i * 5.3, i) * 0.42);
    out.push({
      x: Math.cos(a) * d,
      z: Math.sin(a) * d,
      r: radius * (0.3 + hash2(i * 2.7, seed - i) * 0.34),
    });
  }
  return out;
}

export function heightFieldFor(spec) {
  const { radius, height, seed } = spec;
  const shape = spec.shape || 'plateau';
  const lobes = lobesFor(spec);

  return (lx, lz) => {
    // union of the lobes, softened; 1 well inside the island, 0 out at sea
    let mask = 0;
    for (const l of lobes) {
      const d = Math.hypot(lx - l.x, lz - l.z) / l.r;
      mask = Math.max(mask, 1 - d);
    }
    // a bitten, rocky coastline
    mask += (fbm(lx * 0.07 + seed * 4.3, lz * 0.07 - seed * 2.1, 4) - 0.5) * 0.42;

    if (mask <= 0) return -2.2 - 18 * Math.min(-mask, 1);

    // sheer walls, flat top: almost all of the rise happens in a narrow band
    const plateau = THREE.MathUtils.smoothstep(mask, 0.04, 0.3);
    let h = plateau * height;

    // horizontal strata on the walls, the way the painting's limestone reads
    const strata = Math.sin(h * 1.5) * 0.28 * (1 - plateau) * height * 0.12;
    h += strata;

    if (shape === 'volcano') {
      const cone = Math.max(0, 1 - Math.hypot(lx, lz) / (radius * 0.55));
      h += Math.pow(cone, 1.5) * height * 1.3;
      const crater = Math.max(0, 1 - Math.hypot(lx, lz) / (radius * 0.14));
      h -= Math.pow(crater, 2) * height * 0.5;
    } else if (shape === 'peak') {
      const cone = Math.max(0, 1 - Math.hypot(lx, lz) / (radius * 0.66));
      h += Math.pow(cone, 1.8) * height * 1.6;
    }

    // rolling ground on the plateau itself
    h += (fbm(lx * 0.14 + seed * 3.1, lz * 0.14, 4) - 0.5) * height * 0.26 * plateau;
    // a beach shelf wherever the mask fades out gently
    return h - 1.3;
  };
}

/* Sea stacks: the painting is full of little rocks standing in the water, and they
   are most of what makes the sea look inhabited rather than empty. */
export function makeSeaStack(seed) {
  const g = new THREE.Group();
  const mat = new THREE.MeshStandardMaterial({ color: PALETTE.rock, flatShading: true, roughness: 1 });
  const dark = new THREE.MeshStandardMaterial({ color: PALETTE.rockDark, flatShading: true, roughness: 1 });
  const n = 1 + Math.floor(hash2(seed, seed * 2.3) * 3);
  for (let i = 0; i < n; i++) {
    const h = 1.6 + hash2(seed + i, i * 3.7) * 4.2;
    const r = 0.7 + hash2(i * 1.9, seed - i) * 1.3;
    const rock = new THREE.Mesh(new THREE.CylinderGeometry(r * 0.55, r, h, 5, 1), i % 2 ? dark : mat);
    rock.position.set(
      (hash2(seed * 1.3, i) - 0.5) * 3.4,
      h / 2 - 0.5,
      (hash2(i, seed * 1.7) - 0.5) * 3.4,
    );
    rock.rotation.y = hash2(i, seed) * Math.PI;
    rock.rotation.z = (hash2(seed, i * 2.1) - 0.5) * 0.3;
    g.add(rock);
  }
  return g;
}

export function buildIsland(spec) {
  const { radius } = spec;
  const heightAt = heightFieldFor(spec);
  // coarse on purpose: the art is chunky, and fine triangles kill the look
  const seg = Math.max(14, Math.round(radius * (spec.detail || 0.72)));
  const geo = new THREE.PlaneGeometry(radius * 2.6, radius * 2.6, seg, seg);
  geo.rotateX(-Math.PI / 2);

  const pos = geo.attributes.position;
  for (let i = 0; i < pos.count; i++) {
    pos.setY(i, heightAt(pos.getX(i), pos.getZ(i)));
  }
  geo.computeVertexNormals();

  // colour per face, by how steep and how high it sits: sand, rock, grass, snow
  const nonIndexed = geo.toNonIndexed();
  const p = nonIndexed.attributes.position;
  const colors = new Float32Array(p.count * 3);
  const sand = new THREE.Color(PALETTE.sand);
  const grass = new THREE.Color(spec.grass ? spec.grass : PALETTE.grass);
  const grassDark = new THREE.Color(PALETTE.grassDark);
  const rock = new THREE.Color(PALETTE.rock);
  const rockDark = new THREE.Color(PALETTE.rockDark);
  const snow = new THREE.Color(PALETTE.snow);
  const lava = new THREE.Color(PALETTE.lava);
  const c = new THREE.Color();
  const a = new THREE.Vector3(), b = new THREE.Vector3(), cc = new THREE.Vector3();
  const ab = new THREE.Vector3(), ac = new THREE.Vector3(), nrm = new THREE.Vector3();

  for (let f = 0; f < p.count; f += 3) {
    a.fromBufferAttribute(p, f); b.fromBufferAttribute(p, f + 1); cc.fromBufferAttribute(p, f + 2);
    ab.subVectors(b, a); ac.subVectors(cc, a);
    nrm.crossVectors(ab, ac).normalize();
    const slope = 1 - Math.abs(nrm.y);                    // 0 flat, 1 vertical
    const hy = (a.y + b.y + cc.y) / 3;
    const cx = (a.x + b.x + cc.x) / 3, cz = (a.z + b.z + cc.z) / 3;
    const grain = fbm(cx * 0.3 + spec.seed, cz * 0.3, 2);

    if (hy < 0.45) c.copy(sand);
    else if (slope > 0.45) c.copy(rock).lerp(rockDark, grain * 0.9);
    else c.copy(grass).lerp(grassDark, grain * 0.75);

    if (spec.snowline && hy > spec.snowline) {
      c.lerp(snow, THREE.MathUtils.clamp((hy - spec.snowline) / 3, 0, 1) * (slope < 0.62 ? 1 : 0.35));
    }
    if (spec.shape === 'volcano') {
      const toCentre = Math.hypot(cx, cz) / radius;
      if (toCentre < 0.2) c.lerp(lava, THREE.MathUtils.clamp(1 - toCentre / 0.2, 0, 1) * 0.85);
      else if (toCentre < 0.5 && grain > 0.62) c.lerp(lava, 0.5);
    }

    for (let k = 0; k < 3; k++) {
      colors[(f + k) * 3] = c.r; colors[(f + k) * 3 + 1] = c.g; colors[(f + k) * 3 + 2] = c.b;
    }
  }
  nonIndexed.setAttribute('color', new THREE.BufferAttribute(colors, 3));
  nonIndexed.computeVertexNormals();

  const mesh = new THREE.Mesh(nonIndexed, new THREE.MeshStandardMaterial({
    vertexColors: true, flatShading: true, roughness: 1, metalness: 0,
  }));
  mesh.position.set(spec.pos[0], 0, spec.pos[1]);
  mesh.userData.heightAt = heightAt;
  return mesh;
}

/* Where the shoreline actually falls, found by walking outward until the ground
   drops under water. Everything that has to hug the coast uses this. */
export function shoreline(spec, rays = 64, offset = 0) {
  const h = heightFieldFor(spec);
  const pts = [];
  for (let k = 0; k < rays; k++) {
    const ang = (k / rays) * Math.PI * 2;
    const cx = Math.cos(ang), cz = Math.sin(ang);
    let lo = 0, hi = spec.radius * 1.5;
    for (let s = 0; s < 18; s++) {
      const mid = (lo + hi) / 2;
      if (h(cx * mid, cz * mid) > 0) lo = mid; else hi = mid;
    }
    const r = lo + offset;
    pts.push(new THREE.Vector2(cx * r, cz * r));
  }
  return pts;
}

/* The bright shallow shelf the island stands on, following the real coastline and
   edged with surf — the strongest graphic element of the painting. */
export function buildLagoon(spec, foamTexture) {
  const g = new THREE.Group();
  const shelf = shoreline(spec, 64, spec.radius * 0.3);

  const disc = new THREE.Mesh(
    new THREE.ShapeGeometry(new THREE.Shape(shelf)),
    new THREE.MeshStandardMaterial({
      color: PALETTE.lagoon, roughness: 0.46, metalness: 0.0,
      transparent: true, opacity: 0.9, flatShading: true,
    }),
  );
  disc.rotation.x = -Math.PI / 2;
  disc.position.y = 0.55;
  disc.renderOrder = 1;
  g.add(disc);

  // surf: a white band laid along the shoreline itself, not a ring texture
  const surf = shoreline(spec, 72, spec.radius * 0.06);
  const verts = [];
  const width = spec.radius * 0.1;
  for (let i = 0; i < surf.length; i++) {
    const a = surf[i], b = surf[(i + 1) % surf.length];
    const na = a.clone().normalize(), nb = b.clone().normalize();
    const a0 = a.clone().addScaledVector(na, -width), a1 = a.clone().addScaledVector(na, width);
    const b0 = b.clone().addScaledVector(nb, -width), b1 = b.clone().addScaledVector(nb, width);
    verts.push(a0.x, 0, a0.y, b0.x, 0, b0.y, a1.x, 0, a1.y);
    verts.push(b0.x, 0, b0.y, b1.x, 0, b1.y, a1.x, 0, a1.y);
  }
  const surfGeo = new THREE.BufferGeometry();
  surfGeo.setAttribute('position', new THREE.Float32BufferAttribute(verts, 3));
  const uvs = [];
  for (let i = 0; i < verts.length / 3; i += 6) uvs.push(0, 0, 0, 1, 1, 0, 0, 1, 1, 1, 1, 0);
  surfGeo.setAttribute('uv', new THREE.Float32BufferAttribute(uvs, 2));
  const surfMesh = new THREE.Mesh(surfGeo, new THREE.MeshBasicMaterial({
    color: 0xffffff, transparent: true, opacity: 0.62, depthWrite: false, fog: true,
  }));
  surfMesh.position.y = 0.66;
  surfMesh.renderOrder = 2;
  g.add(surfMesh);

  g.position.set(spec.pos[0], 0, spec.pos[1]);
  return g;
}
