/* The island meshes and the ground they stand on.

   Each island ships as a .glb plus a heightmap raycast from that same mesh, so
   anything placed on an island — a fighter, a boat at its pier — sits on the real
   surface rather than on a formula that approximates it. Models are generated from
   the start-screen painting and turned to face the painting's camera; a small rock
   model is shared by many places at different sizes. */
import * as THREE from 'three';
import { GLTFLoader } from 'three/gltf';
import { DRACOLoader } from 'three/draco';

export const ISLAND_PATH = 'assets/isles/';

function sampler(entry, data, size) {
  const { size: metres, minHeight, maxHeight } = entry;
  const span = maxHeight - minHeight;
  const half = metres / 2;
  // local metres -> texel, bilinear, so slopes read smooth under a character
  return (lx, lz) => {
    const u = (lx + half) / metres * (size - 1);
    const v = (lz + half) / metres * (size - 1);
    if (u < 0 || v < 0 || u > size - 1 || v > size - 1) return minHeight;
    const x0 = Math.floor(u), z0 = Math.floor(v);
    const x1 = Math.min(x0 + 1, size - 1), z1 = Math.min(z0 + 1, size - 1);
    const fx = u - x0, fz = v - z0;
    const at = (x, z) => data[(z * size + x) * 4] / 255;
    const h = (at(x0, z0) * (1 - fx) + at(x1, z0) * fx) * (1 - fz)
            + (at(x0, z1) * (1 - fx) + at(x1, z1) * fx) * fz;
    return minHeight + h * span;
  };
}

async function readHeight(url) {
  // createImageBitmap handles the 16-bit greyscale PNGs that Image.decode() stalls on
  const res = await fetch(url);
  if (!res.ok) throw new Error('heightmap ' + res.status + ' ' + url);
  const bitmap = await createImageBitmap(await res.blob());
  const c = document.createElement('canvas');
  c.width = bitmap.width; c.height = bitmap.height;
  const ctx = c.getContext('2d', { willReadFrequently: true });
  ctx.drawImage(bitmap, 0, 0);
  bitmap.close && bitmap.close();
  return { data: ctx.getImageData(0, 0, c.width, c.height).data, size: c.width };
}

function prepareMaterials(root) {
  root.traverse((o) => {
    if (!o.isMesh) return;
    o.frustumCulled = true;
    const mats = Array.isArray(o.material) ? o.material : [o.material];
    for (const m of mats) {
      // the painted texture carries the light already; a glossy response on top of
      // it reads as plastic
      m.roughness = 1;
      m.metalness = 0;
      if (m.map) m.map.anisotropy = 4;
    }
  });
}

export async function loadTerrain(specs, onStep) {
  const manifest = await (await fetch(ISLAND_PATH + 'manifest.json')).json();
  const byId = new Map((manifest.islands || manifest).map((e) => [e.id, e]));

  const draco = new DRACOLoader();
  draco.setDecoderPath('assets/vendor/draco/');
  draco.setDecoderConfig({ type: 'wasm' });
  const loader = new GLTFLoader();
  loader.setDRACOLoader(draco);

  // each model once, however many places share it
  const wanted = [...new Set(specs.map((s) => s.model || s.id))];
  const models = new Map();
  await Promise.all(wanted.map(async (id) => {
    const entry = byId.get(id);
    if (!entry) { console.warn('no island mesh for', id); return; }
    try {
      const [gltf, height] = await Promise.all([
        loader.loadAsync(ISLAND_PATH + entry.mesh),
        readHeight(ISLAND_PATH + entry.height),
      ]);
      prepareMaterials(gltf.scene);
      models.set(id, { entry, scene: gltf.scene, local: sampler(entry, height.data, height.size) });
    } catch (err) {
      console.warn('island failed:', id, err.message);
    }
    onStep && onStep();
  }));
  draco.dispose();

  const out = new Map();
  for (const spec of specs) {
    const model = models.get(spec.model || spec.id);
    if (!model) continue;
    const yaw = spec.yaw || 0;
    const s = spec.scale || 1;
    const root = model.scene.clone();
    root.position.set(spec.pos[0], 0, spec.pos[1]);
    root.rotation.y = yaw;
    root.scale.setScalar(s);

    const cos = Math.cos(yaw), sin = Math.sin(yaw);
    // world -> the model's own frame: undo the turn, then the size
    const toLocal = (x, z) => {
      const dx = x - spec.pos[0], dz = z - spec.pos[1];
      return [(dx * cos - dz * sin) / s, (dx * sin + dz * cos) / s];
    };
    out.set(spec.id, {
      spec, entry: model.entry, root,
      localHeight: (lx, lz) => model.local(lx / s, lz / s) * s,
      worldHeight: (x, z) => {
        const [lx, lz] = toLocal(x, z);
        return model.local(lx, lz) * s;
      },
    });
  }
  return out;
}

/* Walks outward from the island centre until the ground drops under the water,
   so piers and boats can be put where the shore actually is. */
export function shoreAt(island, angle, from = 0.2) {
  const { spec, worldHeight } = island;
  const cx = Math.cos(angle), cz = Math.sin(angle);
  let lo = spec.radius * from, hi = spec.radius * 1.6;
  for (let i = 0; i < 20; i++) {
    const mid = (lo + hi) / 2;
    if (worldHeight(spec.pos[0] + cx * mid, spec.pos[1] + cz * mid) > 0.25) lo = mid; else hi = mid;
  }
  return { r: lo, x: spec.pos[0] + cx * lo, z: spec.pos[1] + cz * lo };
}
