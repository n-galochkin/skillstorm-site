/* The archipelago from above — the same view the game is played in.
   One scene, no cuts: the page scroll sails a camera from island to island. */
import * as THREE from 'three';
import { pass, saturation, screenUV, smoothstep, mix, float, length, vec2, vec3, vec4, abs, luminance, uniform } from 'three/tsl';
import { bloom } from 'three/bloom';
import { gaussianBlur } from 'three/blur';
import { GLTFLoader } from 'three/gltf';
import { ISLANDS, ISLETS } from './archipelago.js';
import { makeSeaStack, shoreline, fbm, PALETTE } from './islands.js';
import { loadTerrain, shoreAt } from './terrain.js';
import { Ocean } from './water.js';
import { Sky } from './sky.js';
import { Clouds } from './atmosphere.js';
import { Gulls } from './gulls.js';
import { CloudBank } from './cloudbank.js';
import {
  loadProps, propsMaterial, PropInstancer,
  scatterForest, layoutPier, mooredBoats, layoutHarbourTown, scatterRuins,
} from './props.js';


export const MODELS = 'assets/models/';

// Phones get a lighter world. A 3D page that stutters is worse than no 3D page.
export const LIGHT = (() => {
  // ?full forces the desktop path, for checking it from a small window
  if (new URLSearchParams(location.search).has('full')) return false;
  const narrow = Math.min(innerWidth, innerHeight) < 760;
  const weak = (navigator.hardwareConcurrency || 8) <= 4
    || /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
  return narrow || weak;
})();

// the scroll track: a short hold at each island, a long flight between them
export const HOLD = 0.2, TRAVEL = 1.45;

/* --------------------------------------------------------------- textures */
function radialTexture(stops, size = 128) {
  const c = document.createElement('canvas');
  c.width = c.height = size;
  const ctx = c.getContext('2d');
  const g = ctx.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
  for (const [at, col] of stops) g.addColorStop(at, col);
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, size, size);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

function skyTexture() {
  const c = document.createElement('canvas');
  c.width = 8; c.height = 256;
  const ctx = c.getContext('2d');
  const g = ctx.createLinearGradient(0, 0, 0, 256);
  g.addColorStop(0.00, '#1d6fae');
  g.addColorStop(0.30, '#4f9fd0');
  g.addColorStop(0.48, '#9ccbe4');
  g.addColorStop(0.53, '#cfe6f1');   // the pale haze band right on the horizon
  g.addColorStop(0.58, '#7fb6d6');
  g.addColorStop(1.00, '#1a5f93');
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, 8, 256);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}


function flatTexture(text, opts = {}) {
  const { font = '700 46px Unbounded, Trebuchet MS, sans-serif', fill = 'rgba(240,182,60,0.95)',
    letter = 7, pad = 24, h = 96, glow = 'rgba(4,10,18,0.85)' } = opts;
  const probe = document.createElement('canvas').getContext('2d');
  probe.font = font;
  const w = Math.ceil(probe.measureText(text).width + text.length * letter) + pad * 2;
  const c = document.createElement('canvas');
  c.width = w; c.height = h;
  const ctx = c.getContext('2d');
  ctx.font = font;
  ctx.textBaseline = 'middle';
  ctx.fillStyle = fill;
  ctx.shadowColor = glow;
  ctx.shadowBlur = 14;
  let x = pad;
  for (const ch of text) {
    ctx.fillText(ch, x, h / 2);
    x += ctx.measureText(ch).width + letter;
  }
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 8;
  t.wrapS = THREE.RepeatWrapping;      // seen from above the plane mirrors U
  t.center.set(0.5, 0.5);
  t.repeat.x = -1;
  return { texture: t, aspect: w / h };
}

/* -------------------------------------------------------------------- sea */
class Sea {
  constructor(size, seg, islands) {
    const cx = size * 0.38;
    const geo = new THREE.PlaneGeometry(size, size, seg, seg);
    geo.rotateX(-Math.PI / 2);
    geo.translate(cx, 0, 0);
    this.geo = geo;
    this.base = Float32Array.from(geo.attributes.position.array);
    this.mat = new THREE.MeshStandardMaterial({
      map: Sea.depthTexture(size, cx, islands), roughness: 0.52, metalness: 0.0,
    });
    this.mesh = new THREE.Mesh(geo, this.mat);
    this.mesh.renderOrder = -1;
  }

  /* The shallows are painted into a texture rather than vertex colours: the sea
     grid is coarse, and a per-vertex gradient shows every quad. */
  static depthTexture(size, cx, islands) {
    const N = 1024;
    const c = document.createElement('canvas');
    c.width = c.height = N;
    const ctx = c.getContext('2d');
    const img = ctx.createImageData(N, N);
    const deep = [26, 96, 158];
    const mid = [48, 146, 196];
    const shoal = [116, 214, 230];
    const per = size / N;
    const x0 = cx - size / 2, z0 = -size / 2;
    for (let py = 0; py < N; py++) {
      const z = z0 + py * per;
      for (let px = 0; px < N; px++) {
        const x = x0 + px * per;
        let near = Infinity;
        for (const is of islands) {
          const d = Math.hypot(x - is.pos[0], z - is.pos[1]) - is.radius;
          if (d < near) near = d;
        }
        const t = THREE.MathUtils.clamp(1 - near / 20, 0, 1);
        const a = THREE.MathUtils.smoothstep(t, 0.0, 0.75);
        const b = THREE.MathUtils.smoothstep(t, 0.72, 1.0);
        const swell = (fbm(x * 0.012, z * 0.012, 3) - 0.5) * 14;
        const i = (py * N + px) * 4;
        for (let k = 0; k < 3; k++) {
          const v = deep[k] + (mid[k] - deep[k]) * a + (shoal[k] - mid[k]) * b;
          img.data[i + k] = THREE.MathUtils.clamp(v + swell, 0, 255);
        }
        img.data[i + 3] = 255;
      }
    }
    ctx.putImageData(img, 0, 0);
    const tex = new THREE.CanvasTexture(c);
    tex.colorSpace = THREE.SRGBColorSpace;
    tex.anisotropy = 8;
    return tex;
  }

  update(t) {
    const arr = this.geo.attributes.position.array, base = this.base;
    for (let i = 0; i < arr.length; i += 3) {
      const x = base[i], z = base[i + 2];
      arr[i + 1] =
        Math.sin(x * 0.045 + t * 0.75) * 0.3 +
        Math.sin(z * 0.037 - t * 0.62) * 0.26 +
        Math.sin((x + z) * 0.082 + t * 1.25) * 0.12;
    }
    this.geo.attributes.position.needsUpdate = true;
    this.geo.computeVertexNormals();
  }
}

/* ------------------------------------------------------------------ boats */
function buildBoat() {
  const g = new THREE.Group();
  const shape = new THREE.Shape();
  shape.moveTo(0, 2.3);
  shape.quadraticCurveTo(1.05, 0.6, 0.8, -1.9);
  shape.lineTo(-0.8, -1.9);
  shape.quadraticCurveTo(-1.05, 0.6, 0, 2.3);
  const hull = new THREE.Mesh(
    new THREE.ExtrudeGeometry(shape, { depth: 0.85, bevelEnabled: false }),
    new THREE.MeshStandardMaterial({ color: 0x7a4f2c, roughness: 1, flatShading: true }),
  );
  hull.rotation.x = -Math.PI / 2;
  hull.position.y = 0.85;
  g.add(hull);
  const mast = new THREE.Mesh(
    new THREE.CylinderGeometry(0.1, 0.12, 4.2, 5),
    new THREE.MeshStandardMaterial({ color: 0x6b4526, roughness: 1 }),
  );
  mast.position.set(0, 2.8, 0.2);
  g.add(mast);
  const sail = new THREE.Mesh(
    new THREE.PlaneGeometry(2.4, 3.0),
    new THREE.MeshStandardMaterial({ color: 0xf2e9d6, roughness: 1, side: THREE.DoubleSide, flatShading: true }),
  );
  sail.position.set(0, 3.0, 0.25);
  g.add(sail);
  return g;
}

/* ------------------------------------------------------------------ world */
export class World {
  constructor(canvas) {
    this.canvas = canvas;
    this.scene = new THREE.Scene();
    this.clock = new THREE.Clock();
    this.mixers = [];
    this.islands = new Map();
    this.labels = [];
    this.events = {};
  }

  async init() {
    const renderer = new THREE.WebGPURenderer({ canvas: this.canvas, antialias: !LIGHT });
    await renderer.init();
    renderer.setPixelRatio(Math.min(devicePixelRatio || 1, LIGHT ? 1.3 : 2));
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.22;
    renderer.setClearColor(0x8fc0da, 1);
    this.renderer = renderer;
    this.backend = renderer.backend && renderer.backend.isWebGPUBackend ? 'webgpu' : 'webgl';

    this.camera = new THREE.PerspectiveCamera(42, 1, 1, 9000);   // far enough for the sea disc's rim
    this.setupPost();             // needs the camera

    // Golden hour: a lower, warmer sun and a peach haze on the horizon. Long warm
    // light flatters the generated islands and the haze melts their far edges.
    this.sky = new Sky({
      sunElevation: 21, sunAzimuth: 222,
      sunColor: 0xffd29a, hazeColor: 0xd8c4b0, hazeHeight: 0.11,
    });
    this.scene.add(this.sky.object3D);
    // the painting's air is clear: the far islands keep their colour, only the
    // horizon itself goes pale. Denser fog read as a blue wash over everything.
    // the far islands should melt into a pale warm air, not turn into orange cut-outs
    this.scene.fog = new THREE.FogExp2(0xbfc6c4, 0.00095);

    // the scene light follows the same sun the sky and water are lit by
    const sun = new THREE.DirectionalLight(0xffc98f, 2.9);
    sun.position.copy(this.sky.sunDirection).multiplyScalar(220);
    this.scene.add(sun, sun.target);
    // the island textures carry painted shading already; strong fill on top of it
    // flattened them to pastel
    this.scene.add(new THREE.HemisphereLight(0xcfe0f2, 0x3b6a88, 0.75));
    this.sun = sun;

    const envTex = skyTexture();
    envTex.mapping = THREE.EquirectangularReflectionMapping;
    this.scene.environment = envTex;
    this.scene.environmentIntensity = 0.55;

    const sky = new THREE.Mesh(
      new THREE.SphereGeometry(1700, 32, 20),
      new THREE.MeshBasicMaterial({ map: skyTexture(), side: THREE.BackSide, fog: false, depthWrite: false }),
    );
    sky.renderOrder = -3;
    this.scene.add(sky);
    return this;
  }

  async load(onProgress) {
    const loader = new GLTFLoader();
    const names = ['villager', 'sword', 'stone_01', 'stone_02', 'house_01', 'monument_01'];
    const clips = ['anim_idle', 'anim_walk', 'anim_attack'];
    let done = 0;
    const total = names.length + clips.length + 2;
    const bump = () => { done++; onProgress && onProgress(done / total); };

    const models = {};
    await Promise.all(names.map(async (n) => {
      models[n] = (await loader.loadAsync(MODELS + n + '.glb')).scene;
      bump();
    }));
    const anims = {};
    await Promise.all(clips.map(async (n) => {
      const g = await loader.loadAsync(MODELS + n + '.glb');
      if (g.animations[0]) anims[n.replace('anim_', '')] = g.animations[0];
      bump();
    }));
    const cloudTex = await new THREE.TextureLoader().loadAsync('assets/cloud.webp');
    // the game's own start-screen cumulus, rim cleaned for a blue background
    const bankTex = await new THREE.TextureLoader().loadAsync('assets/cloud_bank.webp');
    bankTex.colorSpace = THREE.SRGBColorSpace;
    const gullTex = await new THREE.TextureLoader().loadAsync('assets/gulls.webp');
    gullTex.colorSpace = THREE.SRGBColorSpace;
    cloudTex.colorSpace = THREE.SRGBColorSpace;
    bump();
    const all = [...ISLANDS, ...ISLETS];
    const [props, terrain] = await Promise.all([loadProps(), loadTerrain(all)]);
    bump();

    this.terrain = terrain;
    this.assets = { models, anims, cloudTex, bankTex, gullTex, props };
    return this.assets;
  }

  shadowMaterial() {
    if (!this._shadowMat) {
      this._shadowMat = new THREE.MeshBasicMaterial({
        map: radialTexture([[0, 'rgba(8,46,74,0.55)'], [0.5, 'rgba(8,46,74,0.28)'], [1, 'rgba(8,46,74,0)']]),
        transparent: true, depthWrite: false, fog: true,
      });
    }
    return this._shadowMat;
  }

  // this build's WebGPU shadow maps come back empty, and for a stylised chart a
  // painted blot is cleaner anyway
  dropShadow(x, y, z, size) {
    const geo = new THREE.PlaneGeometry(size, size);
    geo.rotateX(-Math.PI / 2);
    const m = new THREE.Mesh(geo, this.shadowMaterial());
    m.position.set(x + size * 0.1, y, z + size * 0.08);
    m.renderOrder = 3;
    return m;
  }

  build(lang) {
    const scene = this.scene;
    const all = [...ISLANDS, ...ISLETS];

    // the sea traces its shallows from each island's real outline
    const shores = all.map((spec) => {
      const t = this.terrain.get(spec.id);
      return t ? { pos: spec.pos, radius: spec.radius, heightAt: t.worldHeight } : null;
    }).filter(Boolean);
    this.ocean = new Ocean({
      // a 4 km disc reaches close to the true horizon; more rings than before so the
      // grid under the camera stays fine (a sparse grid smeared the shore damping and
      // let waves climb over flat land)
      size: 2600, segments: LIGHT ? 130 : 220, islands: shores,
      sunDirection: this.sky.sunDirection, quality: LIGHT ? 'low' : 'high',
      sunColor: 0xffd7a6, horizonColor: 0x8fa9bd, fogDensity: 0.0011,
    });
    scene.add(this.ocean.object3D);

    this.dressing = new THREE.Group();
    scene.add(this.dressing);

    const inst = new PropInstancer(this.assets.props, propsMaterial());
    for (const spec of all) {
      const island = this.terrain.get(spec.id);
      if (!island) continue;
      scene.add(island.root);
      this.islands.set(spec.id, { spec, heightAt: island.localHeight, island });
      // the generated islands come with their forests, towns and piers already
      // modelled; scattering props over them would plant a second forest
    }
    this.instanced = inst.commit(scene);

    // The chart drawn on the water (dashed route, depth soundings) is gone from the
    // 3D view: at the islands' new size the dashes read as floating debris and the
    // soundings came out mirrored. The route lives on in the page's chart card.
    this.clouds = new Clouds({ sunDirection: this.sky.sunDirection });
    // the game's own painted gull (main-menu flipbook), wheeling over the islands
    this.birds = new Gulls(this.assets.gullTex, this.planFlocks(all), {});
    scene.add(this.clouds.object3D, this.birds.object3D);
    // the low bank spans the part of the archipelago the page sails through (the
    // chapter islands), not the far band: spread over that, the clouds thinned out
    // to almost none anywhere near the camera
    const xs = ISLANDS.map((sp) => sp.pos[0]), zs = ISLANDS.filter((sp) => !sp.storm).map((sp) => sp.pos[1]);
    this.cloudBank = new CloudBank(this.assets.bankTex, {
      count: LIGHT ? 6 : 9,
      bounds: { minX: Math.min(...xs) - 120, maxX: Math.max(...xs) + 120,
                minZ: Math.min(...zs) - 120, maxZ: Math.max(...zs) + 160 },
    });
    scene.add(this.cloudBank.object3D);
    this.ocean.setCloudShadow(this.clouds.shadowConfig());

    this.buildStorm();
  }

  /* Flocks over the whole archipelago: every island worth a flock gets one, and they
     alternate between low ones that skim its coast and cliffs (lifted clear of the
     highest ground along their circle, read from the island's heightmap) and high
     ones wheeling well above it. Tiny rocks are skipped; the far band gets a few. */
  planFlocks(all) {
    const rnd = (() => { let a = 91; return () => { a = (a * 16807) % 2147483647; return a / 2147483647; }; })();
    const plans = [];
    const budget = LIGHT ? 10 : 20;
    const islands = all.filter((sp) => sp.radius >= 9).sort((a, b) => b.radius - a.radius);
    islands.forEach((sp, i) => {
      if (plans.length >= budget) return;
      const low = i % 2 === 0;
      const r = low ? sp.radius * (0.75 + rnd() * 0.35) : sp.radius * (0.5 + rnd() * 0.6) + 15;
      let top = 0;
      for (let k = 0; k < 24; k++) {
        const a = (k / 24) * Math.PI * 2;
        top = Math.max(top, this.groundAt(sp.id, sp.pos[0] + Math.cos(a) * r, sp.pos[1] + Math.sin(a) * r));
      }
      plans.push({
        cx: sp.pos[0], cz: sp.pos[1], r,
        y: low ? top + 5 + rnd() * 7 : Math.max(top + 18, 38 + rnd() * 34),
        span: low ? [5.5, 7.5] : [8, 11],
        perFlock: low ? [3, 5] : [4, 7],
      });
    });
    return plans;
  }

  /* Trees first, then whatever this island is known for. All of it is placed on
     the real surface through the island's heightmap. */
  dressIsland(spec, island, inst) {
    const sample = island.worldHeight;
    const r = spec.radius;
    const count = Math.round((spec.kindCount || (spec.id && spec.id.startsWith('islet') ? 40 : 190)) * (LIGHT ? 0.5 : 1));

    const mask = spec.arena
      ? (x, z) => Math.hypot(x - spec.pos[0], z - spec.pos[1]) > r * 0.62
      : undefined;
    const passes = LIGHT ? 3 : 7;
    for (let k = 0; k < passes; k++) {
      inst.placeAll(scatterForest({
        sampleHeight: sample,
        bounds: { cx: spec.pos[0], cz: spec.pos[1], radius: r * 0.96 },
        count, seed: (spec.seed || 1) * 31 + k * 977, mask,
      }));
    }

    if (spec.feature === 'pier' || spec.boats) {
      const angle = spec.pierAngle !== undefined ? spec.pierAngle : Math.PI * 0.28;
      const shore = shoreAt(island, angle);
      const pier = layoutPier({
        from: [shore.x, shore.z], angle, length: r * 0.55, deckY: 1.4, seed: spec.seed || 3,
      });
      inst.placeAll(pier.placements);
      inst.placeAll(mooredBoats(pier, { seaY: 0, seed: spec.seed || 5 }));
      this.piers = this.piers || [];
      this.piers.push(pier);
    }

    if (spec.feature === 'village') {
      inst.placeAll(layoutHarbourTown({
        shoreAt: (tt) => {
          const s = shoreAt(island, tt * Math.PI * 2);
          return [s.x, s.z];
        },
        sampleHeight: sample, count: 7, setback: 5, lighthouse: true, seed: spec.seed || 7,
      }));
    }

    if (spec.feature === 'ruins') {
      inst.placeAll(scatterRuins({
        sampleHeight: sample, x: spec.pos[0], z: spec.pos[1],
        radius: r * 0.45, count: 7, seed: spec.seed || 11,
      }));
    }
  }

  groundAt(id, x, z) {
    const entry = this.islands.get(id);
    if (!entry) return 0;
    return entry.island.worldHeight(x, z);
  }

  /* Rocks standing in the water: most of what keeps the open sea from reading empty. */
  buildSeaStacks(all) {
    const g = new THREE.Group();
    const count = LIGHT ? 26 : 56;
    let made = 0, tries = 0;
    while (made < count && tries < count * 14) {
      tries++;
      const x = -60 + Math.random() * 580;
      const z = -140 + Math.random() * 300;
      let nearest = Infinity;
      for (const is of all) nearest = Math.min(nearest, Math.hypot(x - is.pos[0], z - is.pos[1]) - is.radius);
      if (nearest < 2 || nearest > 22) continue;          // they belong just off the shore
      const stack = makeSeaStack(made * 3.7 + 1.3);
      stack.position.set(x, 0, z);
      stack.scale.setScalar(0.28 + Math.random() * 0.34);
      g.add(stack);
      g.add(this.dropShadow(x, 0.7, z, 3));
      made++;
    }
    this.scene.add(g);
    this.seaStacks = g;
  }

  /* The chart drawn on the water: the sailed route as a dashed line, and depth
     soundings over the open sea. This is what makes the page a chart. */
  buildChartLayer() {
    const g = new THREE.Group();
    const curve = new THREE.CatmullRomCurve3(
      ISLANDS.map((s) => new THREE.Vector3(s.pos[0], 0.7, s.pos[1])), false, 'catmullrom', 0.4);
    const dashMat = new THREE.MeshBasicMaterial({
      color: 0xffd98a, transparent: true, opacity: 0.34, depthWrite: false, fog: true,
    });
    const steps = 150;
    const pts = curve.getSpacedPoints(steps);
    for (let i = 0; i < steps; i += 2) {
      const a = pts[i], b = pts[Math.min(i + 1, steps)];
      const len = a.distanceTo(b);
      if (len < 0.01) continue;
      const dash = new THREE.Mesh(new THREE.PlaneGeometry(len * 0.72, 0.5), dashMat);
      dash.rotation.x = -Math.PI / 2;
      dash.position.copy(a).lerp(b, 0.5);
      dash.rotation.z = -Math.atan2(b.z - a.z, b.x - a.x);
      dash.renderOrder = 2;
      g.add(dash);
    }

    const spots = [[30, -46], [112, -58], [64, 70], [150, 52], [196, -72], [226, 2],
      [272, 66], [310, -52], [356, 36], [396, -58], [432, 10], [-24, 24], [86, -14], [268, -30]];
    for (const [x, z] of spots) {
      const depth = 6 + Math.round(fbm(x * 0.04, z * 0.04, 2) * 40);
      const { texture, aspect } = flatTexture(String(depth), {
        font: '700 30px JetBrains Mono, monospace', fill: 'rgba(214,240,250,0.8)',
        letter: 1, pad: 8, h: 44, glow: 'rgba(8,40,66,0.7)',
      });
      const hgt = 3.4;
      const geo = new THREE.PlaneGeometry(hgt * aspect, hgt);
      geo.rotateX(-Math.PI / 2);
      const m = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({
        map: texture, transparent: true, depthWrite: false, opacity: 0.55, fog: true,
      }));
      m.position.set(x, 0.7, z);
      m.renderOrder = 2;
      g.add(m);
    }
    this.scene.add(g);
  }

  buildClouds() {
    const tex = this.assets.cloudTex;
    const shadowTex = radialTexture([[0, 'rgba(10,52,80,0.8)'], [0.55, 'rgba(10,52,80,0.35)'], [1, 'rgba(10,52,80,0)']]);
    this.clouds = new THREE.Group();
    this.shadows = new THREE.Group();
    const n = LIGHT ? 6 : 11;
    for (let i = 0; i < n; i++) {
      const s = 30 + Math.random() * 40;
      const x = -120 + Math.random() * 760;
      const z = -190 + Math.random() * 380;
      const y = 40 + Math.random() * 16;
      const cloud = new THREE.Mesh(new THREE.PlaneGeometry(s, s),
        new THREE.MeshBasicMaterial({
          map: tex, transparent: true, depthWrite: false, opacity: 0.24,
          color: 0xf0f6fc, fog: false, side: THREE.DoubleSide,
        }));
      cloud.position.set(x, y, z);
      cloud.rotation.x = -Math.PI / 2;
      cloud.userData.drift = 1.1 + Math.random() * 1.4;
      this.clouds.add(cloud);

      const shadow = new THREE.Mesh(new THREE.PlaneGeometry(s * 1.1, s * 1.1),
        new THREE.MeshBasicMaterial({ map: shadowTex, transparent: true, depthWrite: false, opacity: 0.12, fog: false }));
      shadow.rotation.x = -Math.PI / 2;
      shadow.position.set(x + 26, 0.62, z + 16);
      shadow.renderOrder = 2;
      shadow.userData.drift = cloud.userData.drift;
      this.shadows.add(shadow);
    }
    this.scene.add(this.clouds, this.shadows);
  }

  buildStorm() {
    const spec = ISLANDS.find((i) => i.storm);
    if (!spec) return;
    const tex = this.assets.cloudTex;
    const group = new THREE.Group();
    const n = LIGHT ? 14 : 22;
    for (let i = 0; i < n; i++) {
      const m = new THREE.Mesh(new THREE.PlaneGeometry(30, 30),
        new THREE.MeshBasicMaterial({
          map: tex, transparent: true, depthWrite: false, opacity: 0,
          color: 0x9f86ff, fog: false, side: THREE.DoubleSide,
        }));
      m.rotation.x = -Math.PI / 2;
      m.userData.angle = (i / n) * Math.PI * 2;
      m.userData.phase = Math.random() * Math.PI * 2;
      group.add(m);
    }
    group.position.set(spec.pos[0], 3, spec.pos[1]);
    // the cloud banks grow with the island they ring, the ring itself is set per frame
    group.children.forEach((m) => m.scale.setScalar(Math.max(1, spec.radius / 40)));
    this.scene.add(group);
    this.stormRing = { group, spec };
  }

  /* ------------------------------------------------------------- camera */
  stationFor(spec, zoom = 1) {
    // about 30 degrees above the water, the way the start-screen painting sits:
    // the island fills the near third and the archipelago runs off to the horizon
    // a tall island (the volcano) needs the camera further out than its footprint says
    const view = (spec.view || 1) * zoom * (this.backOff || 1);
    // looking down at about 43 degrees: high enough to read the archipelago as a map
    // and an island as a whole, the way the game itself is seen
    const h = (100 + spec.radius * 0.6) * view;
    const back = (100 + spec.radius * 0.8) * view;
    return new THREE.Vector3(spec.pos[0] - spec.radius * 0.25, h, spec.pos[1] + back);
  }

  buildRoute() {
    const points = ISLANDS.map((s) => this.stationFor(s));
    const looks = ISLANDS.map((s) => new THREE.Vector3(s.pos[0], 0, s.pos[1]));
    this.routeCurve = new THREE.CatmullRomCurve3(points, false, 'catmullrom', 0.4);
    this.lookCurve = new THREE.CatmullRomCurve3(looks, false, 'catmullrom', 0.4);
    this.legs = ISLANDS.slice(0, -1).map((_, i) => this.birdPath(i));
  }

  /* The highest island ground under a point (0 over open water). */
  groundUnder(x, z) {
    let top = 0;
    for (const t of this.terrain.values()) top = Math.max(top, t.worldHeight(x, z) || 0);
    return top;
  }

  /* One leg as a bird would fly it: off the hold with a gliding drop, low over the water off
     to one side, in at the next island from its flank, round it, and down onto the hold. */
  birdPath(i) {
    const A = this.stationFor(ISLANDS[i]), B = this.stationFor(ISLANDS[i + 1]);
    const LA = new THREE.Vector3(ISLANDS[i].pos[0], 0, ISLANDS[i].pos[1]);
    const LB = new THREE.Vector3(ISLANDS[i + 1].pos[0], 0, ISLANDS[i + 1].pos[1]);
    const RB = ISLANDS[i + 1].radius;
    // measured from hold to hold, not island to island: a hold sits well off its island's
    // centre, and a path laid from the centres doubled back on itself (storm -> forge)
    const span = new THREE.Vector3(B.x - A.x, 0, B.z - A.z);
    const D = span.length();
    const dir = span.clone().normalize();
    const side = new THREE.Vector3(dir.z, 0, -dir.x).multiplyScalar(i % 2 ? 1 : -1);
    const at = (along, aside, y) => A.clone().addScaledVector(dir, along).addScaledVector(side, aside).setY(y);
    const pts = [A.clone()];
    pts.push(at(D * 0.16, D * 0.06, A.y * 0.62));                           // off the hold, gliding down
    if (D > 500) {                                                          // the long way to the storm:
      pts.push(at(D * 0.34, -D * 0.08, 230));                               // up over the clouds
      pts.push(at(D * 0.6, D * 0.1, 80));                                   // and back down
    } else {
      pts.push(at(D * 0.48, D * 0.24, 26));                                 // low over the water, off to one side
    }
    // in at the next island from its flank, then a sweep round it onto the hold
    const fromA = Math.atan2(A.z - LB.z, A.x - LB.x);
    const toHold = Math.atan2(B.z - LB.z, B.x - LB.x);
    const turn = (i % 2 ? 1 : -1) * 1.25;
    let sweep = toHold - (fromA + turn);
    while (sweep > Math.PI) sweep -= 2 * Math.PI;
    while (sweep < -Math.PI) sweep += 2 * Math.PI;
    const hold = Math.hypot(B.x - LB.x, B.z - LB.z);
    const ring = (a, r, y) => new THREE.Vector3(LB.x + Math.cos(a) * r, y, LB.z + Math.sin(a) * r);
    pts.push(ring(fromA + turn, Math.max(RB * 1.9, hold * 0.8), B.y * 0.45));
    pts.push(ring(fromA + turn + sweep * 0.55, hold * 0.95, B.y * 0.72));
    pts.push(B.clone());
    // never through a hillside: lift any waypoint that sits too close to the ground
    for (const p of pts) p.y = Math.max(p.y, this.groundUnder(p.x, p.z) + 22);
    return new THREE.CatmullRomCurve3(pts, false, 'centripetal');
  }

  routeAt(p) {
    const n = ISLANDS.length;
    const hold = HOLD, travel = TRAVEL;
    const segs = [];
    for (let i = 0; i < n; i++) {
      segs.push({ kind: 'hold', i, w: hold });
      if (i < n - 1) segs.push({ kind: 'travel', i, w: travel });
    }
    const total = segs.reduce((s, x) => s + x.w, 0);
    const target = THREE.MathUtils.clamp(p, 0, 1) * total;
    let acc = 0;
    for (let k = 0; k < segs.length; k++) {
      const seg = segs[k];
      if (target <= acc + seg.w || k === segs.length - 1) {
        const local = THREE.MathUtils.clamp((target - acc) / seg.w, 0, 1);
        if (seg.kind === 'hold') return { u: seg.i / (n - 1), station: seg.i, local, moving: false };
        const eased = local;   // the page glide already starts and ends slowly
        return { u: (seg.i + eased) / (n - 1), station: eased < 0.5 ? seg.i : seg.i + 1, local, moving: true, leg: seg.i, e: eased };
      }
      acc += seg.w;
    }
    return { u: 1, station: n - 1, local: 1, moving: false };
  }

  /* One leg of the voyage, flown along its bird path. The camera looks ahead and down along
     its course in mid-flight and turns to the island at both ends; it banks with the turn. */
  flight(leg, e) {
    const path = this.legs[leg];
    const s = THREE.MathUtils.clamp(e, 0, 1);
    const pos = path.getPointAt(s);
    const ahead = path.getPointAt(Math.min(1, s + 0.03));
    const behind = path.getPointAt(Math.max(0, s - 0.03));
    const course = ahead.clone().sub(behind);
    const flat = new THREE.Vector3(course.x, 0, course.z);
    if (flat.lengthSq() < 1e-6) flat.set(0, 0, -1);
    flat.normalize();
    // where a bird would look: well ahead along its course, and down at the sea
    const gaze = pos.clone().addScaledVector(flat, 140);
    gaze.y = Math.max(0, pos.y - 70);
    const LA = new THREE.Vector3(ISLANDS[leg].pos[0], 0, ISLANDS[leg].pos[1]);
    const LB = new THREE.Vector3(ISLANDS[leg + 1].pos[0], 0, ISLANDS[leg + 1].pos[1]);
    // a bird keeps its goal in sight: half the gaze is on the next island all the way, all of
    // it from the approach on (looking only along the course filled the frame with empty sea)
    const look = gaze.clone()
      .lerp(LB, 0.6 + 0.4 * THREE.MathUtils.smoothstep(s, 0.4, 0.8))
      .lerp(LA, 1 - THREE.MathUtils.smoothstep(s, 0, 0.2));
    // bank with the turn: how far the course swings between just behind and just ahead
    const a0 = Math.atan2(pos.z - behind.z, pos.x - behind.x);
    const a1 = Math.atan2(ahead.z - pos.z, ahead.x - pos.x);
    let swing = a1 - a0;
    while (swing > Math.PI) swing -= 2 * Math.PI;
    while (swing < -Math.PI) swing += 2 * Math.PI;
    const ends = THREE.MathUtils.smoothstep(s, 0, 0.12) * (1 - THREE.MathUtils.smoothstep(s, 0.88, 1));
    const roll = THREE.MathUtils.clamp(-swing * 220, -16, 16) * ends;
    // low over the water the lens opens a touch: the sea rushes past
    const fov = 6 * (1 - THREE.MathUtils.smoothstep(pos.y, 30, 110)) * ends;
    return { pos, look, roll, fov };
  }

  setCamera(p, elapsed) {
    const r = this.routeAt(p);
    let pos, look, roll = 0, fovKick = 0;
    if (r.moving) ({ pos, look, roll, fov: fovKick } = this.flight(r.leg, r.e));
    else {
      pos = this.stationFor(ISLANDS[r.station]);
      look = new THREE.Vector3(ISLANDS[r.station].pos[0], 0, ISLANDS[r.station].pos[1]);
    }
    // the bank is smoothed frame to frame, so a turn never snaps the horizon
    this.rollSm = THREE.MathUtils.damp(this.rollSm || 0, roll, 3, 1 / 60);
    roll = this.rollSm;
    // the frame leans a little toward the mouse, the way IVRESS's does (set by the page)
    this.lean = this.lean || new THREE.Vector2();
    this.lean.x = THREE.MathUtils.damp(this.lean.x, (this.leanTarget && this.leanTarget.x) || 0, 2.2, 1 / 60);
    this.lean.y = THREE.MathUtils.damp(this.lean.y, (this.leanTarget && this.leanTarget.y) || 0, 2.2, 1 / 60);
    // holding over an island the camera hangs in the wind like a drone: a slow drift, a
    // gentle roll, and now and then a gust that leans it a little further. Several unrelated
    // sines, so the motion never repeats and never reads as a loop.
    this.holdSway = THREE.MathUtils.damp(this.holdSway || 0, r.moving ? 0 : 1, 1.6, 1 / 60);
    const sway = this.holdSway;
    const gust = Math.max(0, Math.sin(elapsed * 0.31) * Math.sin(elapsed * 0.113 + 1.3)) ** 2;
    pos.x += (Math.sin(elapsed * 0.17) * 3.2 + Math.sin(elapsed * 0.53 + 2) * 0.9 + gust * 4.5) * sway;
    pos.z += (Math.cos(elapsed * 0.13) * 2.4 + Math.sin(elapsed * 0.41) * 0.7) * sway;
    pos.y += Math.sin(elapsed * 0.21) * 1.4 + Math.sin(elapsed * 0.67 + 1) * 0.5 * sway;
    look.x += (Math.sin(elapsed * 0.11 + 0.7) * 1.6 + gust * 1.5) * sway;
    look.z += Math.cos(elapsed * 0.09 + 0.3) * 1.2 * sway;
    this.camera.position.copy(pos);
    this.camera.lookAt(look);
    // the mouse lean: slide along the camera's own right and up, a few metres at most
    const right = new THREE.Vector3().setFromMatrixColumn(this.camera.matrixWorld, 0);
    const up = new THREE.Vector3().setFromMatrixColumn(this.camera.matrixWorld, 1);
    this.camera.position.addScaledVector(right, this.lean.x * 7).addScaledVector(up, -this.lean.y * 4);
    this.camera.rotateZ(((Math.sin(elapsed * 0.23) * 0.55 + Math.sin(elapsed * 0.61 + 0.4) * 0.2 + gust * 0.6) * sway + roll) * Math.PI / 180);
    // a manoeuvre may widen or narrow the lens for a moment
    const fov = (this.baseFov || this.camera.fov) + fovKick;
    if (Math.abs(this.camera.fov - fov) > 0.01) { this.camera.fov = fov; this.camera.updateProjectionMatrix(); }
    return r;
  }

  focusIsland(spec, zoom) {
    this.camera.position.copy(this.stationFor(spec, zoom));
    this.camera.lookAt(spec.pos[0], 0, spec.pos[1]);
  }

  /* Where an island's name should sit on screen, in pixels, or null when it is
     behind the camera. The page draws the label itself, in real type. */
  projectLabel(spec, width, height) {
    const v = new THREE.Vector3(spec.pos[0], 1.2, spec.pos[1] + spec.radius * 1.5);
    v.project(this.camera);
    if (v.z > 1) return null;
    return { x: (v.x * 0.5 + 0.5) * width, y: (-v.y * 0.5 + 0.5) * height };
  }

  resize(w, h) {
    this.renderer.setSize(w, h, false);
    this.size = [w, h];
    this.frameFor(w, h);
  }

  /* On a tall screen the chapter text fills the lower two thirds, so the frame is
     lifted: the island the camera looks at sits in the free upper third instead of
     under the text (and the far haze and cloud tops leave the top edge). The fight
     has no text over it and keeps the plain frame. */
  frameFor(w, h) {
    this.camera.aspect = w / h;
    // a tall screen is narrow across: a wider lens and a step back keep the whole
    // island in, where the desktop lens would show a slice of it
    const tall = w / h < 0.8;
    this.camera.fov = this.baseFov = tall ? 50 : 42;
    const backOff = tall ? 1.45 : 1;
    if (backOff !== (this.backOff || 1)) {
      this.backOff = backOff;
      if (this.routeCurve) this.buildRoute();
    }
    const lift = this.liftFrame !== false && w / h < 0.8 ? 0.22 : 0;
    // on a wide screen the chapter's text takes one side: the frame slides so the island
    // stands on the other (side +1 = text on the left, island to the right)
    const across = tall ? 0 : (this.side || 0) * 0.2;
    if (lift || Math.abs(across) > 1e-4) this.camera.setViewOffset(w, h, -across * w, h * lift, w, h);
    else this.camera.clearViewOffset();
    this.camera.updateProjectionMatrix();
    if (this.focusY) this.focusY.value = 0.53 - lift;
    if (this.cloudBank) {
      this.cloudBank.focusY = lift * 2;
      this.cloudBank.focusX = across * 2;
      this.cloudBank.textTop = lift ? 0.2 : null;
    }
  }

  /* where the chapter's text is: +1 left, -1 right, 0 none (the fight). The frame
     glides there in tick(), so a chapter change never jumps the picture. */
  setTextSide(side) { this.sideTarget = side; }

  setLift(on) {
    this.liftFrame = on;
    if (this.size) this.frameFor(this.size[0], this.size[1]);
  }

  tick(dt, elapsed, state) {
    if (this.size && this.sideTarget !== undefined && Math.abs((this.side || 0) - this.sideTarget) > 1e-3) {
      this.side = THREE.MathUtils.damp(this.side || 0, this.sideTarget, 2.6, dt);
      this.frameFor(this.size[0], this.size[1]);
    }
    this.ocean.update(dt, elapsed, this.camera);
    this.sky.update(dt, elapsed, this.camera);
    this.clouds.update(dt, elapsed, this.camera);
    this.cloudBank.update(dt, elapsed, this.camera);
    this.birds.update(dt, elapsed, this.camera);


    if (this.stormRing) {
      const close = state && state.storm !== undefined ? state.storm : 0;
      const { group, spec } = this.stormRing;
      // the storm closes in over the sea but never cuts into the land: a flat cloud
      // crossing a mountain read as purple paint on its slopes
      const radius = THREE.MathUtils.lerp(spec.radius * 2.2, spec.radius * 1.2, close);
      group.children.forEach((m) => {
        const a = m.userData.angle + elapsed * 0.08;
        m.position.set(Math.cos(a) * radius, Math.sin(elapsed * 0.7 + m.userData.phase) * 1.6, Math.sin(a) * radius);
        m.material.opacity = 0.5 * close;
      });
    }

    for (const list of [this.smoke, this.ash]) {
      if (!list) continue;
      for (const p of list) {
        p.position.y += dt * (list === this.ash ? 2.4 : 1.4);
        const rise = p.position.y - p.userData.floor;
        if (rise > 26) p.position.y = p.userData.floor;
        p.material.opacity = 0.32 * THREE.MathUtils.clamp(1 - rise / 26, 0, 1);
      }
    }

    for (const m of this.mixers) m.update(dt);
  }

  /* The finish on the frame, after the scene and before tone mapping:
     - a soft bloom on what is already bright (foam, sunlit sand, the crater, cloud tops);
     - tilt-shift: the top and bottom of the frame go soft, the band where the subject
       sits stays sharp. It reads as a miniature, the way a diorama is photographed,
       and it keeps the eye off the rough edges of generated geometry at the margins;
     - golden-hour grading: warm highlights, cool teal shadows, a little more colour;
     - a gentle vignette that settles the eye on the middle of the frame. */
  setupPost() {
    if (LIGHT) return;           // phones keep the plain render
    const post = new THREE.PostProcessing(this.renderer);
    const scenePass = pass(this.scene, this.camera);
    const color = scenePass.getTextureNode('output');

    const soft = gaussianBlur(color, null, 4);
    this.focusY = uniform(0.53);   // the sharp band follows the lifted frame
    const band = abs(screenUV.y.sub(this.focusY));
    const focus = smoothstep(float(0.14), float(0.46), band);
    const shifted = mix(color, soft, focus);

    const glow = bloom(shifted, 0.24, 0.6, 0.74);
    const lit = shifted.add(glow);

    const lum = luminance(lit.rgb);
    const warm = smoothstep(float(0.25), float(0.9), lum);
    const tone = mix(vec3(0.93, 1.0, 1.06), vec3(1.07, 1.0, 0.9), warm);
    const graded = saturation(lit.rgb.mul(tone), float(1.12));

    const r = length(screenUV.sub(vec2(0.5, 0.5)).mul(vec2(1.15, 1.0)));
    const vignette = mix(float(1.0), float(0.78), smoothstep(float(0.4), float(0.85), r));
    post.outputNode = vec4(graded.mul(vignette), 1.0);
    this.post = post;
  }

  /* The scene pass inside post-processing re-renders once per node frame, and the
     node frame only advances inside three's own animation loop. The page drives its
     own requestAnimationFrame, so the frame is advanced here by hand; without it
     the pass would keep showing its first frame. */
  nextFrame() {
    const nodes = this.renderer._nodes;
    if (nodes && nodes.nodeFrame && !(this.renderer._animation && this.renderer._animation.isAnimating)) {
      nodes.nodeFrame.update();
    }
  }

  render() {
    if (this.post) { this.nextFrame(); this.post.render(); }
    else this.renderer.render(this.scene, this.camera);
  }

  /* Render one frame into an offscreen target and hand back a JPEG data URL, so
     frames can be inspected without the page itself being painted. */
  async grab(width = 1280, height = 720) {
    const rt = new THREE.RenderTarget(width, height);
    this.frameFor(width, height);
    // with post-processing on, the frame is graded and tone-mapped inside the
    // final pass and comes out already sRGB-encoded; the scene pass sizes itself to
    // the canvas, so the canvas takes the capture size for the moment
    const encoded = !!this.post;
    const size = this.renderer.getSize(new THREE.Vector2());
    const ratio = this.renderer.getPixelRatio();
    if (encoded) { this.renderer.setPixelRatio(1); this.renderer.setSize(width, height, false); }
    this.renderer.setRenderTarget(rt);
    if (encoded) { this.nextFrame(); this.post.render(); } else this.renderer.render(this.scene, this.camera);
    this.renderer.setRenderTarget(null);
    const buf = await this.renderer.readRenderTargetPixelsAsync(rt, 0, 0, width, height);
    if (encoded) { this.renderer.setPixelRatio(ratio); this.renderer.setSize(size.x, size.y, false); }
    if (this.size) this.frameFor(this.size[0], this.size[1]);

    const c = document.createElement('canvas');
    c.width = width; c.height = height;
    const ctx = c.getContext('2d');
    const img = ctx.createImageData(width, height);
    const row = width * 4;
    // A render target carries no colour space, so the backend writes linear values
    // while the canvas on screen is sRGB-encoded. Encoding here is what makes a
    // captured frame match what the page actually shows.
    for (let y = 0; y < height; y++) {
      // the backend hands back rows top-down already; flipping them here was
      // what turned every review frame upside down
      const src = y * row;
      const dst = y * row;
      for (let x = 0; x < row; x += 4) {
        for (let k = 0; k < 3; k++) {
          const v = buf[src + x + k] / 255;
          img.data[dst + x + k] = encoded ? buf[src + x + k] : Math.round(255 * (v <= 0.0031308
            ? v * 12.92 : 1.055 * Math.pow(v, 1 / 2.4) - 0.055));
        }
        img.data[dst + x + 3] = 255;
      }
    }
    ctx.putImageData(img, 0, 0);
    rt.dispose();
    return c.toDataURL('image/jpeg', 0.86);
  }
}
