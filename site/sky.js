/* sky.js — the dome over the archipelago.
 *
 * A painted gradient rather than a physical model: the key art's sky is a flat
 * bright blue that pales into a haze band on the horizon, and Preetham scattering
 * fights that look instead of helping. Three stops (zenith / mid / horizon haze),
 * a sun disc with two glow falloffs, and a little dithering so the gradient does
 * not band on an 8-bit display.
 *
 * The clip-space trick (push z to w so the dome always sits on the far plane) is
 * the one three.js' own Sky/SkyMesh uses; everything else is written for this site.
 *
 *   const sky = new Sky({ sunElevation: 32, sunAzimuth: 118 });
 *   scene.add(sky.object3D);
 *   scene.fog = new THREE.FogExp2(sky.fogColor.getHex(), 0.0021);
 *   sky.update(dt, elapsed, camera);
 */

import {
  Mesh, BoxGeometry, NodeMaterial, Color, Vector3, BackSide,
} from 'three';

import {
  Fn, float, vec2, vec3, vec4, uniform, modelViewProjection, positionWorld, cameraPosition,
  normalize, dot, abs, max, mix, pow, exp, sin, fract, smoothstep, saturate, oneMinus, screenUV,
} from 'three';

const DEFAULTS = {
  sunElevation: 33,        // degrees above the horizon
  sunAzimuth: 118,         // degrees, 0 = +z, turning towards +x
  /* Pre-compensated for ACES at exposure 1.22, like the sea's palette: these
     land on #2b94dd / #53b5e9 / #80c4e4, straight off the key art. */
  zenithColor: 0x167adc,
  midColor: 0x0497ff,
  hazeColor: 0x4baaf2,     // the pale band that sea, land and sky all die into
  seaColor: 0x2c89ce,      // below the horizon the dome stands in for far water
  sunColor: 0xffffec,
  hazeHeight: 0.085,       // how far up the haze band reaches (sin of the angle)
  sunDiscSize: 0.9,        // 1 = about the real sun
  exposure: 1.0,
};

export class Sky {
  constructor(opts = {}) {
    const o = { ...DEFAULTS, ...opts };
    this.options = o;

    this.sunDirection = new Vector3();
    this.fogColor = new Color(o.hazeColor);
    this.sunColor = new Color(o.sunColor);
    this.horizonColor = new Color(o.hazeColor);

    const U = this.u = {
      sunDir: uniform(new Vector3(0, 1, 0)),
      zenith: uniform(new Color(o.zenithColor)),
      mid: uniform(new Color(o.midColor)),
      haze: uniform(new Color(o.hazeColor)),
      sea: uniform(new Color(o.seaColor)),
      sunColor: uniform(new Color(o.sunColor)),
      hazeHeight: uniform(o.hazeHeight),
      discSize: uniform(o.sunDiscSize),
      exposure: uniform(o.exposure),
    };

    const vertexNode = Fn(() => {
      const p = modelViewProjection().toVar();
      p.z.assign(p.w);          // always on the far plane, never clipped
      return p;
    })();

    const fragmentNode = Fn(() => {
      const dir = normalize(positionWorld.sub(cameraPosition)).toVar();
      const up = dir.y.toVar();

      // vertical gradient, flattened near the top the way a painted sky reads
      const col = mix(U.mid, U.zenith, pow(saturate(up), 0.62)).toVar();

      // haze band: a soft pale collar sitting on the horizon, both sides of it
      const band = exp(abs(up).div(U.hazeHeight).negate()).toVar();
      col.assign(mix(col, U.haze, band.mul(0.92)));
      // Below the horizon the dome stands in for water too far away to be meshed,
      // so the line where sea meets sky stays crisp instead of mushing out.
      col.assign(mix(col, U.sea, oneMinus(smoothstep(float(-0.006), float(0.002), up))));

      // sun: a small disc, a tight glow and a wide bloom across the sky
      const s = saturate(dot(dir, U.sunDir)).toVar();
      const disc = smoothstep(float(0.99972), float(0.99993), s);
      const tight = pow(s, 420.0).mul(0.55);
      const wide = pow(s, 14.0).mul(0.10);
      const bloom = pow(s, 3.0).mul(0.035);
      col.addAssign(U.sunColor.mul(disc.mul(2.4).add(tight).add(wide).add(bloom)));

      // 8-bit dither: breaks the banding a smooth gradient shows on cheap panels
      const n = fract(sin(dot(screenUV, vec2(12.9898, 78.233))).mul(43758.5453)).sub(0.5);
      col.addAssign(vec3(n).mul(0.0045));

      return vec4(max(col.mul(U.exposure), vec3(0.0)), 1.0);
    })();

    const material = new NodeMaterial();
    material.vertexNode = vertexNode;
    material.fragmentNode = fragmentNode;
    material.side = BackSide;
    material.depthWrite = false;
    material.fog = false;
    this.material = material;

    this.geometry = new BoxGeometry(1, 1, 1);
    this.mesh = new Mesh(this.geometry, material);
    this.mesh.scale.setScalar(20000);
    this.mesh.frustumCulled = false;
    this.mesh.renderOrder = -1000;
    this.mesh.name = 'Sky';
    this.object3D = this.mesh;

    this.setSun(o.sunElevation, o.sunAzimuth);
  }

  /* Elevation and azimuth in degrees; keeps `sunDirection` in step for the ocean,
     the clouds and any directional light. */
  setSun(elevationDeg, azimuthDeg) {
    const e = (elevationDeg * Math.PI) / 180;
    const a = (azimuthDeg * Math.PI) / 180;
    this.sunDirection.set(Math.sin(a) * Math.cos(e), Math.sin(e), Math.cos(a) * Math.cos(e)).normalize();
    this.u.sunDir.value.copy(this.sunDirection);
    this.options.sunElevation = elevationDeg;
    this.options.sunAzimuth = azimuthDeg;
    return this;
  }

  /* Suggested scene fog: the horizon haze, so water, land and sky all die into
     the same colour. Pair it with a density around 0.002. */
  get fogDensitySuggestion() { return 0.0021; }

  setColors({ zenith, mid, haze, sun, sea } = {}) {
    if (zenith !== undefined) this.u.zenith.value.set(zenith);
    if (mid !== undefined) this.u.mid.value.set(mid);
    if (haze !== undefined) {
      this.u.haze.value.set(haze);
      this.fogColor.set(haze);
      this.horizonColor.set(haze);
    }
    if (sun !== undefined) { this.u.sunColor.value.set(sun); this.sunColor.set(sun); }
    // `sea` is what the dome shows below the horizon: keep it equal to the
    // ocean's own haze colour and the horizon line stays seamless.
    if (sea !== undefined) this.u.sea.value.set(sea);
    return this;
  }

  update(dt, elapsed, camera) {
    if (camera) this.mesh.position.copy(camera.position);
  }

  dispose() {
    this.geometry.dispose();
    this.material.dispose();
  }
}

export default Sky;
