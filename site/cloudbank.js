/* The low cloud bank: big cumulus between the camera and the sea.

   The game's start screen opens on clouds with the archipelago underneath, and the
   page says the same: a handful of the game's own cumulus (its transition cloud)
   drift over the islands below the camera. They frame the view rather than hide it:
   a cloud that drifts into the middle of the frame, where the island the page is
   talking about sits, thins out, and one the camera is about to pass through fades
   instead of filling the screen with a flat card. */
import * as THREE from 'three';

const DEFAULTS = {
  count: 16,
  bounds: { minX: -320, maxX: 340, minZ: -520, maxZ: 260 },
  // below the page's camera (which flies at 110-190 m) and well above the islands,
  // so they are seen from above, drifting between the eye and the sea
  altitude: [48, 88],
  size: [70, 135],
  wind: [3.2, -1.1],          // metres per second, drifting the bank across the sea
  opacity: 0.86,
  tint: 0xffffff,             // the painted texture carries its own warm/lavender light
  seed: 11,
};

function mulberry(a) {
  return () => {
    a |= 0; a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export class CloudBank {
  constructor(texture, opts = {}) {
    const o = { ...DEFAULTS, ...opts };
    this.options = o;
    this.object3D = new THREE.Group();
    this.object3D.name = 'CloudBank';
    const rnd = mulberry(o.seed);
    const b = o.bounds;
    this.sprites = [];
    // Even cover: the bank's area is cut into a grid with about one cell per cloud,
    // and each cloud sits somewhere inside its own cell. Pure random scatter piled
    // them up over one part of the sea and left the rest bare. They all drift with
    // the same wind, so the spacing holds as they move.
    const w = b.maxX - b.minX, d = b.maxZ - b.minZ;
    const cols = Math.max(1, Math.round(Math.sqrt(o.count * w / d)));
    const rows = Math.max(1, Math.ceil(o.count / cols));
    const cells = [];
    for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) cells.push([c, r]);
    for (let i = cells.length - 1; i > 0; i--) {          // shuffle, then take as many as needed
      const j = Math.floor(rnd() * (i + 1));
      [cells[i], cells[j]] = [cells[j], cells[i]];
    }
    for (let i = 0; i < o.count; i++) {
      const [cx, cz] = cells[i % cells.length];
      const mat = new THREE.SpriteMaterial({
        map: texture, color: o.tint, transparent: true, depthWrite: false, fog: true,
        opacity: o.opacity, rotation: rnd() * Math.PI * 2,
      });
      const s = new THREE.Sprite(mat);
      const size = o.size[0] + (o.size[1] - o.size[0]) * rnd();
      s.scale.set(size, size * (0.78 + rnd() * 0.3), 1);
      s.position.set(
        b.minX + (cx + 0.15 + 0.7 * rnd()) * (w / cols),
        o.altitude[0] + (o.altitude[1] - o.altitude[0]) * rnd(),
        b.minZ + (cz + 0.15 + 0.7 * rnd()) * (d / rows),
      );
      s.renderOrder = 6;
      s.userData.base = o.opacity * (0.75 + rnd() * 0.25);
      this.object3D.add(s);
      this.sprites.push(s);
    }
    this._v = new THREE.Vector3();
    this.visibility = 1;        // the page can thin the whole bank (e.g. during the fight)
    this.focusY = 0;            // where the subject sits on screen, -1..1 (lifted on a tall screen)
    this.focusX = 0;            // and across: slid aside from the chapter's text on a wide screen
    this.textTop = null;        // on a tall screen the text fills the frame below this line
  }

  update(dt, elapsed, camera) {
    const o = this.options, b = o.bounds;
    const w = b.maxX - b.minX, d = b.maxZ - b.minZ;
    for (const s of this.sprites) {
      s.position.x += o.wind[0] * dt;
      s.position.z += o.wind[1] * dt;
      // wrap around the bank's area so the sky never empties
      if (s.position.x > b.maxX) s.position.x -= w;
      if (s.position.x < b.minX) s.position.x += w;
      if (s.position.z > b.maxZ) s.position.z -= d;
      if (s.position.z < b.minZ) s.position.z += d;

      let k = 1;
      if (camera) {
        const dist = s.position.distanceTo(camera.position);
        const near = s.scale.x * 0.55;
        k *= THREE.MathUtils.smoothstep(dist, near, near * 2.2);
        this._v.copy(s.position).project(camera);
        if (this._v.z < 1 && Number.isFinite(this._v.x) && Number.isFinite(this._v.y)) {
          // the subject sits mid-frame: a cloud there thins to a veil
          // measured to the cloud's near edge, not its centre: a big cloud parked beside
          // the island still spreads over it (this is what a tall screen showed)
          const reach = s.scale.x * 0.35 / (dist * Math.tan(THREE.MathUtils.degToRad(camera.fov / 2)));
          const r = Math.max(0, Math.hypot((this._v.x - this.focusX) * Math.min(1, camera.aspect), (this._v.y - this.focusY) * 1.2) - reach);
          k *= THREE.MathUtils.lerp(0.08, 1, THREE.MathUtils.smoothstep(r, 0.25, 0.7));
          // under the text a white cloud fights the lettering: it thins there too
          if (this.textTop !== null) {
            k *= THREE.MathUtils.lerp(0.25, 1, THREE.MathUtils.smoothstep(this._v.y, this.textTop - 0.4, this.textTop));
          }
        }
      }
      const op = s.userData.base * k * this.visibility;
      s.material.opacity = Number.isFinite(op) ? op : s.userData.base;
    }
  }
}
