/* Kenney Nature Kit (CC0) prepared for instancing.

   Each model arrives as a few unlit meshes, one per colour. For the scene we need
   one geometry and one material per model, so the material colours are baked into a
   vertex-colour attribute and the pieces merged. After that an island of a thousand
   cliff blocks is a single draw call. Licence: assets/kit/KENNEY-LICENSE.txt */
import * as THREE from 'three';
import { GLTFLoader } from 'three/gltf';
import * as BufferGeometryUtils from 'three/bufferutils';

export const KIT_PATH = 'assets/kit/';
const WHITE = new THREE.Color(0xffffff);

const KEEP = ['position', 'normal'];

/* The kit's glTF export mangled its greens — "grass" arrives cyan — so colour comes
   from the material name instead, in our own palette taken from the start-screen
   painting: limestone cliffs, bright grass, dark conifers, pale sand. */
const PALETTE = {
  grass: 0x74b84a,
  dirt: 0x8d949c,          // cliff sides read as limestone, not soil
  dirtDark: 0x6f767f,
  stone: 0xa7aeb6,
  stoneDark: 0x7d848d,
  leafsGreen: 0x4e9f4a,
  leafsDark: 0x2f6f3c,
  leafsFall: 0xd08a3a,
  woodBark: 0x6d4c2f,
  woodBarkDark: 0x553a24,
  wood: 0x8a5a32,
  woodDark: 0x6b4526,
  woodInner: 0xc9a271,
  colorRed: 0xc5523f,
  colorRedDark: 0x9b3f33,
  colorYellow: 0xe8b445,
  _defaultMat: 0xb9bfc6,
};

function bakeColours(root) {
  const parts = [];
  root.updateWorldMatrix(true, true);
  root.traverse((o) => {
    if (!o.isMesh) return;
    const mats = Array.isArray(o.material) ? o.material : [o.material];
    const geo = o.geometry.index ? o.geometry.toNonIndexed() : o.geometry.clone();
    geo.applyMatrix4(o.matrixWorld);
    for (const name of Object.keys(geo.attributes)) {
      if (!KEEP.includes(name)) geo.deleteAttribute(name);
    }
    if (!geo.attributes.normal) geo.computeVertexNormals();

    const count = geo.attributes.position.count;
    const colours = new Float32Array(count * 3);
    // groups map vertex ranges to materials; without groups the whole mesh is one
    const groups = geo.groups && geo.groups.length ? geo.groups : [{ start: 0, count, materialIndex: 0 }];
    for (const g of groups) {
      const m = mats[g.materialIndex] || mats[0];
      const named = m && PALETTE[m.name] !== undefined ? new THREE.Color(PALETTE[m.name]) : null;
      const col = named || (m && m.color ? m.color : new THREE.Color(0xffffff));
      const end = Math.min(g.start + g.count, count);
      for (let i = g.start; i < end; i++) {
        colours[i * 3] = col.r; colours[i * 3 + 1] = col.g; colours[i * 3 + 2] = col.b;
      }
    }
    geo.clearGroups();
    geo.setAttribute('color', new THREE.BufferAttribute(colours, 3));
    parts.push(geo);
  });
  if (!parts.length) return null;
  return parts.length === 1 ? parts[0] : BufferGeometryUtils.mergeGeometries(parts, false);
}

export async function loadKit(names, onStep) {
  const loader = new GLTFLoader();
  const kit = {};
  await Promise.all(names.map(async (name) => {
    try {
      const gltf = await loader.loadAsync(KIT_PATH + name + '.glb');
      const geo = bakeColours(gltf.scene);
      if (geo) {
        geo.computeBoundingBox();
        kit[name] = geo;
      }
    } catch (e) {
      console.warn('kit piece missing:', name, e.message);
    }
    onStep && onStep();
  }));
  return kit;
}

export function kitMaterial() {
  return new THREE.MeshStandardMaterial({
    vertexColors: true, flatShading: true, roughness: 1, metalness: 0,
  });
}

/* Collects transforms per piece and turns them into one InstancedMesh each. */
export class Instancer {
  constructor(kit) {
    this.kit = kit;
    this.buckets = new Map();
  }

  // tint multiplies the baked colour, which is how the beach row turns sandy
  place(name, matrix, tint) {
    if (!this.kit[name]) return;
    if (!this.buckets.has(name)) this.buckets.set(name, []);
    this.buckets.get(name).push({ matrix: matrix.clone(), tint: tint ? tint.clone() : null });
  }

  commit(scene) {
    const mat = kitMaterial();
    const meshes = [];
    for (const [name, list] of this.buckets) {
      const mesh = new THREE.InstancedMesh(this.kit[name], mat, list.length);
      const tinted = list.some((e) => e.tint);
      list.forEach((e, i) => {
        mesh.setMatrixAt(i, e.matrix);
        if (tinted) mesh.setColorAt(i, e.tint || WHITE);
      });
      mesh.instanceMatrix.needsUpdate = true;
      if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
      mesh.frustumCulled = false;
      scene.add(mesh);
      meshes.push(mesh);
    }
    this.buckets.clear();
    return meshes;
  }
}
