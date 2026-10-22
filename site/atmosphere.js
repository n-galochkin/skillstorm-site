/* atmosphere.js — what moves in the air over the archipelago.
 *
 * Clouds: clumps of soft billboard puffs, each one shaded per pixel like a little
 * dome (so a clump reads as volume, not as flat stickers), drifting on the wind and
 * handing the sea a matching set of shadow blots. They are deliberately kept high
 * and far: the key art's sky is mostly clean, and a landing page must never fog up.
 *
 * Birds: flocks of gulls on slow circles, wings flapping, banking into the turn.
 * One draw call, no per-frame CPU work — every bird's position, heading and wing
 * angle is computed in the vertex stage from `elapsed`.
 *
 * Both are written from scratch (TSL / WebGPU); the only shared code is the
 * tileable-noise helper in water.js.
 *
 *   const clouds = new Clouds({ sunDirection });
 *   const birds  = new Birds({ sunDirection });
 *   scene.add(clouds.object3D, birds.object3D);
 *   ocean.setCloudShadow(clouds.shadowConfig());
 *   clouds.update(dt, elapsed, camera); birds.update(dt, elapsed, camera);
 */

import {
  Group, Mesh, BufferGeometry, BufferAttribute, DataTexture, NodeMaterial,
  Color, Vector2, Vector3, Sphere, DoubleSide, LinearFilter, ClampToEdgeWrapping,
  NoColorSpace, NormalBlending,
} from 'three';

import {
  Fn, float, vec2, vec3, vec4, uniform, texture, attribute, varying, varyingProperty,
  positionLocal, modelWorldMatrix, cameraProjectionMatrix, cameraViewMatrix,
  normalize, dot, cross, mix, pow, exp, sin, cos, abs,
  smoothstep, fract, length, saturate, oneMinus,
} from 'three';

import { fbmField } from './water.js';

/* ------------------------------------------------------------- textures */

/* One soft puff: a lumpy dome. RGB carries the dome's height (for shading),
   A the silhouette. */
function makePuffTexture(size = 192, seed = 5) {
  const n = fbmField(size, { octaves: 5, base: 3, gain: 0.55, seed });
  const data = new Uint8Array(size * size * 4);
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const u = (x + 0.5) / size * 2 - 1;
      const v = (y + 0.5) / size * 2 - 1;
      const r = Math.hypot(u, v);
      const lump = n[y * size + x] - 0.5;
      const edge = r + lump * 0.62;
      let a = 1 - smooth01(edge, 0.56, 0.96);
      a = Math.max(0, Math.min(1, a));
      a = Math.pow(a, 0.65);          // a fat opaque core, a soft rim
      const dome = Math.sqrt(Math.max(0, 1 - Math.min(1, edge * edge)));
      const i = (y * size + x) * 4;
      data[i] = data[i + 1] = data[i + 2] = Math.round(dome * 255);
      data[i + 3] = Math.round(a * 255);
    }
  }
  const tex = new DataTexture(data, size, size);
  tex.wrapS = tex.wrapT = ClampToEdgeWrapping;
  tex.minFilter = tex.magFilter = LinearFilter;
  tex.colorSpace = NoColorSpace;
  tex.generateMipmaps = false;
  tex.needsUpdate = true;
  return tex;
}

function smooth01(x, a, b) {
  const t = Math.max(0, Math.min(1, (x - a) / (b - a)));
  return t * t * (3 - 2 * t);
}

function mulberry(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6D2B79F5) >>> 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/* ------------------------------------------------------------- clouds */

const CLOUD_DEFAULTS = {
  clusters: 13,
  puffsPerCluster: 16,
  radiusInner: 620,        // metres from the camera: clouds ring the viewer
  radiusOuter: 2050,
  altitude: 300,
  altitudeSpread: 150,
  puffSize: [58, 170],
  clusterSpread: [185, 115],  // horizontal, vertical
  wind: [-9.5, 3.6],       // metres per second
  sunDirection: new Vector3(0.42, 0.52, -0.74).normalize(),
  sunColor: 0xffffad,
  litColor: 0xffffff,
  shadeColor: 0x7fa3d6,   // the blue underside -> about #a6c2de after ACES
  opacity: 0.98,
  shadowStrength: 0.42,
  shadowCoverage: 0.46,
  shadowScaleMeters: 760,
  fogColor: 0x4baaf2,
  fogDensity: 0.0021,
  seed: 7,
};

export class Clouds {
  constructor(opts = {}) {
    const o = { ...CLOUD_DEFAULTS, ...opts };
    this.options = o;

    this.object3D = new Group();
    this.object3D.name = 'Clouds';

    const rnd = mulberry(o.seed);
    const total = o.clusters * o.puffsPerCluster;

    const pos = new Float32Array(total * 4 * 3);     // puff centre, repeated per corner
    const corner = new Float32Array(total * 4 * 2);
    const norm = new Float32Array(total * 4 * 3);    // dome-of-the-clump fake normal
    const params = new Float32Array(total * 4 * 3);  // size, seed, height in clump
    const index = new Uint32Array(total * 6);

    let q = 0;
    for (let c = 0; c < o.clusters; c++) {
      const ang = (c / o.clusters) * Math.PI * 2 + rnd() * 0.7;
      const rad = o.radiusInner + (o.radiusOuter - o.radiusInner) * Math.pow(rnd(), 0.6);
      const cx = Math.cos(ang) * rad, cz = Math.sin(ang) * rad;
      const cy = o.altitude + (rnd() - 0.5) * o.altitudeSpread;
      const squash = 0.6 + rnd() * 0.8;
      // every clump its own build: some tall and lumpy, some long and flat
      const bulk = 0.62 + rnd() * 0.8;
      const lift = 0.55 + rnd() * 1.1;
      for (let p = 0; p < o.puffsPerCluster; p++) {
        const t = p / o.puffsPerCluster;
        // puffs cluster towards the middle and flatten at the bottom, like a cumulus
        const a = rnd() * Math.PI * 2;
        const rr = Math.pow(rnd(), 0.55);
        const hx = Math.cos(a) * rr * o.clusterSpread[0] * squash * bulk;
        const hz = Math.sin(a) * rr * o.clusterSpread[0] * (1.6 - squash) * 0.9 * bulk;
        // cumulus: a flat base with the mass piled towards the middle and top
        const hy = Math.pow(1 - rr, 1.4) * o.clusterSpread[1] * (0.5 + rnd() * 0.85) * lift
          - o.clusterSpread[1] * 0.22;
        const size = (o.puffSize[0] + (o.puffSize[1] - o.puffSize[0]) * (0.45 + 0.55 * (1 - rr)))
          * (0.7 + rnd() * 0.6) * (0.75 + bulk * 0.4);
        const nx = hx, ny = hy + o.clusterSpread[1] * 0.5, nz = hz;
        const nl = Math.hypot(nx, ny, nz) || 1;
        const heightT = Math.max(0, Math.min(1, 0.5 + hy / (o.clusterSpread[1] * 1.6)));
        const corners = [[-1, -1], [1, -1], [1, 1], [-1, 1]];
        const v0 = q * 4;
        for (let k = 0; k < 4; k++) {
          const vi = v0 + k;
          pos[vi * 3] = cx + hx; pos[vi * 3 + 1] = cy + hy; pos[vi * 3 + 2] = cz + hz;
          corner[vi * 2] = corners[k][0]; corner[vi * 2 + 1] = corners[k][1];
          norm[vi * 3] = nx / nl; norm[vi * 3 + 1] = ny / nl; norm[vi * 3 + 2] = nz / nl;
          params[vi * 3] = size; params[vi * 3 + 1] = rnd() * 6.28; params[vi * 3 + 2] = heightT;
        }
        const i6 = q * 6;
        index[i6] = v0; index[i6 + 1] = v0 + 1; index[i6 + 2] = v0 + 2;
        index[i6 + 3] = v0; index[i6 + 4] = v0 + 2; index[i6 + 5] = v0 + 3;
        q++;
        void t;
      }
    }

    const geo = new BufferGeometry();
    geo.setAttribute('position', new BufferAttribute(pos, 3));
    geo.setAttribute('aCorner', new BufferAttribute(corner, 2));
    geo.setAttribute('aNorm', new BufferAttribute(norm, 3));
    geo.setAttribute('aParams', new BufferAttribute(params, 3));
    geo.setIndex(new BufferAttribute(index, 1));
    geo.boundingSphere = new Sphere(new Vector3(0, o.altitude, 0), o.radiusOuter * 2);
    this.geometry = geo;

    this.puffTex = makePuffTexture(192, o.seed + 3);

    const U = this.u = {
      time: uniform(0),
      wind: uniform(new Vector2(o.wind[0], o.wind[1])),
      domain: uniform(o.radiusOuter * 2.2),
      sunDir: uniform(new Vector3().copy(o.sunDirection).normalize()),
      lit: uniform(new Color(o.litColor)),
      shade: uniform(new Color(o.shadeColor)),
      sunColor: uniform(new Color(o.sunColor)),
      opacity: uniform(o.opacity),
      fogColor: uniform(new Color(o.fogColor)),
      fogDensity: uniform(o.fogDensity),
    };

    const aCorner = attribute('aCorner', 'vec2');
    const aNorm = attribute('aNorm', 'vec3');
    const aParams = attribute('aParams', 'vec3');

    const vertexNode = Fn(() => {
      // drift, wrapped inside a square domain so the field never runs out
      const half = U.domain.mul(0.5);
      const drift = positionLocal.xz.add(U.wind.mul(U.time)).toVar();
      const wrapped = fract(drift.add(half).div(U.domain)).mul(U.domain).sub(half);
      const local = vec3(wrapped.x, positionLocal.y, wrapped.y);
      const world = modelWorldMatrix.mul(vec4(local, 1.0)).xyz.toVar();

      // billboard in view space: no matrix gymnastics, always square to the lens
      const v = cameraViewMatrix.mul(vec4(world, 1.0)).toVar();
      const off = aCorner.mul(aParams.x);
      const view = vec4(v.x.add(off.x), v.y.add(off.y), v.z, v.w).toVar();

      varyingProperty('vec2', 'vCorner').assign(aCorner);
      varyingProperty('vec3', 'vNorm').assign(aNorm);
      varyingProperty('float', 'vHeight').assign(aParams.z);
      varyingProperty('float', 'vDist').assign(length(view.xyz));
      return cameraProjectionMatrix.mul(view);
    })();

    const fragmentNode = Fn(() => {
      const corner2 = varying(vec2(), 'vCorner');
      const fakeN = varying(vec3(), 'vNorm');
      const height = varying(float(), 'vHeight');
      const dist = varying(float(), 'vDist');

      const uv = corner2.mul(0.5).add(0.5);
      const tex = texture(this.puffTex).uv(uv).toVar();
      const alpha = tex.w.toVar();

      // per-pixel dome normal, in view space, so each puff turns in the light
      const dome = tex.x.toVar();
      const nView = normalize(vec3(corner2.x, corner2.y, dome.mul(1.25).add(0.12))).toVar();
      const sunView = normalize(cameraViewMatrix.mul(vec4(U.sunDir, 0.0)).xyz).toVar();
      const lambert = saturate(dot(nView, sunView)).toVar();

      // the clump's own shading: lit on top and on the sun's side, blue underneath
      const clumpLight = saturate(dot(fakeN, U.sunDir).mul(0.5).add(0.5));
      const shadeT = saturate(pow(height, 0.75).mul(0.65).add(clumpLight.mul(0.35)));

      // clouds are white first and shaded second: only the undersides go blue
      const tone = saturate(float(0.42).add(shadeT.mul(0.52)).add(lambert.sub(0.40).mul(0.50)));
      const col = mix(U.shade, U.lit, tone).toVar();
      // the sun's own edge on the lit side, the one thing that sells the volume
      col.addAssign(U.sunColor.mul(pow(lambert, 4.0).mul(0.30)));

      // haze, but far gentler than the sea's: a white cloud keeps its brightness
      // much longer than a dark object at the same distance
      const hz = U.fogDensity.mul(dist).mul(0.5);
      const fog = oneMinus(exp(hz.mul(hz).negate()));
      col.assign(mix(col, U.fogColor, saturate(fog).mul(0.28)));

      // never a hard edge against the camera, never a hard edge in the distance
      const nearFade = smoothstep(float(60.0), float(260.0), dist);
      return vec4(col, alpha.mul(U.opacity).mul(nearFade));
    })();

    const material = new NodeMaterial();
    material.vertexNode = vertexNode;
    material.fragmentNode = fragmentNode;
    material.transparent = true;
    material.depthWrite = false;
    material.blending = NormalBlending;
    material.side = DoubleSide;
    material.fog = false;
    this.material = material;

    this.mesh = new Mesh(geo, material);
    this.mesh.frustumCulled = false;
    this.mesh.renderOrder = 10;
    this.mesh.name = 'CloudPuffs';
    this.object3D.add(this.mesh);

    this._tmp = new Vector3();
  }

  /* What to hand Ocean.setCloudShadow(): blots that drift with the same wind. */
  shadowConfig() {
    const o = this.options;
    return {
      strength: o.shadowStrength,
      coverage: o.shadowCoverage,
      scaleMeters: o.shadowScaleMeters,
      driftX: o.wind[0] * 0.55,
      driftZ: o.wind[1] * 0.55,
    };
  }

  setSun(dir) { this.u.sunDir.value.copy(dir).normalize(); return this; }

  update(dt, elapsed, camera) {
    this.u.time.value = elapsed;
    if (camera) {
      this._tmp.copy(camera.position);
      this.object3D.position.set(this._tmp.x, 0, this._tmp.z);
    }
  }

  dispose() { this.geometry.dispose(); this.material.dispose(); this.puffTex.dispose(); }
}

/* -------------------------------------------------------------- birds */

const BIRD_DEFAULTS = {
  flocks: 8,
  perFlock: 7,
  radius: [34, 190],       // how wide a flock circles
  altitude: [24, 125],
  spread: 650,             // how far the furthest flock sits from the camera
  near: 130,               // how close the nearest one comes
  scale: [1.5, 2.6],       // wingspan in metres (bigger than life: they must read)
  speed: [0.055, 0.12],    // radians per second
  flapRate: [3.4, 6.2],
  color: 0x262b32,
  lightColor: 0x5e6d80,
  sunDirection: new Vector3(0.42, 0.52, -0.74).normalize(),
  fogColor: 0x4baaf2,
  fogDensity: 0.0021,
  seed: 3,
};

/* A gull from above: slender body, long wings that sweep back and narrow to a
   point. `aWing` is (side * span fraction, panel) and the vertex stage folds the
   wing about the body for the flap. */
function birdShape() {
  const v = [];
  const P = (x, y, z, w) => [x, y, z, w, 0];
  const tri = (a, b, c) => { v.push(a, b, c); };

  // body and tail fan
  const nose = P(0, 0.015, 0.62, 0);
  const hipL = P(-0.085, 0, 0.05, 0);
  const hipR = P(0.085, 0, 0.05, 0);
  const tail = P(0, 0, -0.55, 0);
  const tailL = P(-0.15, 0, -0.80, 0);
  const tailR = P(0.15, 0, -0.80, 0);
  tri(nose, hipL, hipR);
  tri(hipL, tail, hipR);
  tri(tail, tailL, tailR);

  // long swept wings, narrowing to a point
  for (const s of [-1, 1]) {
    const sF = P(0.08 * s, 0, 0.26, 0.08 * s);
    const sB = P(0.08 * s, 0, -0.16, 0.08 * s);
    const eF = P(0.45 * s, 0, 0.14, 0.45 * s);
    const eB = P(0.42 * s, 0, -0.24, 0.42 * s);
    const tip = P(1.0 * s, 0, -0.54, 1.0 * s);
    tri(sF, sB, eB);
    tri(sF, eB, eF);
    tri(eF, eB, tip);
  }
  return v;
}

export class Birds {
  constructor(opts = {}) {
    const o = { ...BIRD_DEFAULTS, ...opts };
    this.options = o;

    this.object3D = new Group();
    this.object3D.name = 'Birds';

    const shape = birdShape();
    const perBird = shape.length;
    const total = o.flocks * o.perFlock;
    const rnd = mulberry(o.seed);

    const pos = new Float32Array(total * perBird * 3);
    const wing = new Float32Array(total * perBird * 2);
    const orbit = new Float32Array(total * perBird * 4);   // cx, cz, radius, altitude
    const motion = new Float32Array(total * perBird * 4);  // angSpeed, phase, flapRate, scale

    let w = 0;
    for (let f = 0; f < o.flocks; f++) {
      const a = (f / o.flocks) * Math.PI * 2 + rnd() * 0.8;
      // spread the flocks deterministically in depth: some always close, some far
      const d = o.near + Math.pow(f / Math.max(1, o.flocks - 1), 1.35) * o.spread;
      const cx = Math.cos(a) * d, cz = Math.sin(a) * d;
      const rad = o.radius[0] + rnd() * (o.radius[1] - o.radius[0]);
      const alt = o.altitude[0] + rnd() * (o.altitude[1] - o.altitude[0]);
      const spd = (o.speed[0] + rnd() * (o.speed[1] - o.speed[0])) * (rnd() < 0.5 ? -1 : 1);
      for (let b = 0; b < o.perFlock; b++) {
        // strung out around the circle, at mixed radii and heights: a tight clump
        // of birds reads as one ragged blob instead of a flock
        const phase = (b / o.perFlock) * 4.4 + rnd() * 0.9;
        const rr = rad * (0.62 + rnd() * 0.85);
        const ay = alt + (rnd() - 0.5) * 34;
        const sc = o.scale[0] + rnd() * (o.scale[1] - o.scale[0]);
        const flap = o.flapRate[0] + rnd() * (o.flapRate[1] - o.flapRate[0]);
        for (let k = 0; k < perBird; k++) {
          const p = shape[k];
          const vi = w * perBird + k;
          pos[vi * 3] = p[0]; pos[vi * 3 + 1] = p[1]; pos[vi * 3 + 2] = p[2];
          wing[vi * 2] = p[3]; wing[vi * 2 + 1] = p[4];
          orbit[vi * 4] = cx; orbit[vi * 4 + 1] = cz; orbit[vi * 4 + 2] = rr; orbit[vi * 4 + 3] = ay;
          motion[vi * 4] = spd; motion[vi * 4 + 1] = phase + rnd() * 0.08;
          motion[vi * 4 + 2] = flap; motion[vi * 4 + 3] = sc;
        }
        w++;
      }
    }

    const geo = new BufferGeometry();
    geo.setAttribute('position', new BufferAttribute(pos, 3));
    geo.setAttribute('aWing', new BufferAttribute(wing, 2));
    geo.setAttribute('aOrbit', new BufferAttribute(orbit, 4));
    geo.setAttribute('aMotion', new BufferAttribute(motion, 4));
    geo.boundingSphere = new Sphere(new Vector3(0, o.altitude[1], 0), o.spread * 2);
    this.geometry = geo;

    const U = this.u = {
      time: uniform(0),
      sunDir: uniform(new Vector3().copy(o.sunDirection).normalize()),
      color: uniform(new Color(o.color)),
      light: uniform(new Color(o.lightColor)),
      fogColor: uniform(new Color(o.fogColor)),
      fogDensity: uniform(o.fogDensity),
    };

    const aWing = attribute('aWing', 'vec2');
    const aOrbit = attribute('aOrbit', 'vec4');
    const aMotion = attribute('aMotion', 'vec4');

    const vertexNode = Fn(() => {
      const t = U.time.mul(aMotion.x).add(aMotion.y).toVar();
      const centre = vec3(aOrbit.x, aOrbit.w, aOrbit.y).toVar();
      const r = aOrbit.z;
      const bob = sin(t.mul(3.1).add(aMotion.y.mul(2.0))).mul(1.4);
      const world = centre.add(vec3(cos(t).mul(r), bob, sin(t).mul(r))).toVar();

      // heading is the tangent of the circle; bank into the turn
      const heading = normalize(vec3(sin(t).negate(), float(0.0), cos(t))).toVar();
      const right = normalize(cross(vec3(0.0, 1.0, 0.0), heading)).toVar();
      const bank = float(0.33).mul(aMotion.x.div(abs(aMotion.x).add(0.0001)));
      const up = normalize(cross(heading, right).sub(right.mul(bank))).toVar();

      // flap: the wing lifts along its span, the elbow lagging behind the tip
      const flap = sin(U.time.mul(aMotion.z).add(aMotion.y.mul(5.0))).toVar();
      const span = abs(aWing.x);
      const lift = flap.mul(pow(span, 1.5)).mul(0.62);
      const lag = sin(U.time.mul(aMotion.z).add(aMotion.y.mul(5.0)).sub(span.mul(0.9))).mul(pow(span, 1.6)).mul(0.22);
      // a shallow resting dihedral keeps a gull readable even when it is level
      // with the camera, where a flat wing would vanish edge-on
      const dihedral = pow(span, 1.25).mul(0.17);
      const local = vec3(
        positionLocal.x.mul(oneMinus(abs(lift).mul(0.16))),
        positionLocal.y.add(dihedral).add(lift.mul(0.55)).add(lag.mul(0.45)),
        positionLocal.z.sub(abs(lift).mul(0.08)),
      ).mul(aMotion.w).toVar();

      const p = world.add(right.mul(local.x)).add(up.mul(local.y)).add(heading.mul(local.z));
      const pw = modelWorldMatrix.mul(vec4(p, 1.0)).xyz;
      const view = cameraViewMatrix.mul(vec4(pw, 1.0)).toVar();
      varyingProperty('float', 'vLit').assign(saturate(up.dot(U.sunDir).mul(0.5).add(0.5)));
      varyingProperty('float', 'vDist').assign(length(view.xyz));
      return cameraProjectionMatrix.mul(view);
    })();

    const fragmentNode = Fn(() => {
      const lit = varying(float(), 'vLit');
      const dist = varying(float(), 'vDist');
      const col = mix(U.color, U.light, lit.mul(0.55)).toVar();
      // birds keep more of their own darkness than the haze would really allow:
      // a grey smudge on the water reads as debris, a silhouette reads as a gull
      const fog = oneMinus(exp(U.fogDensity.mul(dist).mul(U.fogDensity.mul(dist)).negate()));
      col.assign(mix(col, U.fogColor, saturate(fog).mul(0.55)));
      // far birds thin out instead of flickering as single pixels
      const a = oneMinus(smoothstep(float(320.0), float(780.0), dist)).mul(0.75).add(0.25);
      return vec4(col, a);
    })();

    const material = new NodeMaterial();
    material.vertexNode = vertexNode;
    material.fragmentNode = fragmentNode;
    material.side = DoubleSide;
    material.transparent = true;
    material.depthWrite = true;
    material.fog = false;
    this.material = material;

    this.mesh = new Mesh(geo, material);
    this.mesh.frustumCulled = false;
    this.mesh.name = 'Birds';
    this.object3D.add(this.mesh);
    this._tmp = new Vector3();
  }

  setSun(dir) { this.u.sunDir.value.copy(dir).normalize(); return this; }

  update(dt, elapsed, camera) {
    this.u.time.value = elapsed;
    if (camera) {
      // the flocks keep the viewer company instead of being left behind
      this._tmp.copy(camera.position);
      this.object3D.position.set(this._tmp.x, 0, this._tmp.z);
    }
  }

  dispose() { this.geometry.dispose(); this.material.dispose(); }
}

export default { Clouds, Birds };
