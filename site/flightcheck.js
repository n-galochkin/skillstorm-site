/* Numbers instead of screenshots for the camera's flights (Nikita 2026-10-22: "зачем скриншотами
   смотришь полёт камеры? можно числами проверять").

   Runs every flight (each island to each other one, plus a change of mind mid-flight), steps the
   real camera through it at 60 frames a second and measures what the eye would complain about:
   - backwards: the angle between where the camera looks and where it moves (a bird never flies
     backwards); - flips: the fastest turn of the gaze, degrees per second;
   - clearance: the lowest height over the ground (islands only - trees are not in the map);
   - roll: the strongest bank; - empty: the share of frames with no island in view.
   Usage in the console of the page: await __ss.checkFlights()  */
import * as THREE from 'three';
import { ISLANDS, ISLETS } from './archipelago.js';

export async function checkFlights(world, { fps = 60, width = 1600, height = 900 } = {}) {
  const cam = world.camera;
  // a fixed frame size: a hidden tab has none, and its projection came out as NaN
  const keep = world.size;
  world.size = [width, height];
  world.frameFor(width, height);
  const dirOf = () => cam.getWorldDirection(new THREE.Vector3());
  const ndc = new THREE.Vector3();
  const anyIslandInView = () => {
    cam.updateMatrixWorld();
    for (const s of [...ISLANDS, ...ISLETS]) {
      ndc.set(s.pos[0], 4, s.pos[1]).project(cam);
      if (ndc.z < 1 && Math.abs(ndc.x) < 0.95 && Math.abs(ndc.y) < 0.95) return true;
    }
    return false;
  };
  const flyAndMeasure = (from, to, midTo = null) => {
    world.voyage = { station: from, flight: null, arrivedAt: 0 };
    world.camPos = undefined; world.lastElapsed = undefined;
    let t = 1000;
    world.setCamera(0, t);
    world.flyTo(to, t);
    let prev = null, prevDir = null;
    const m = { backMax: 0, turnMax: 0, clearMin: Infinity, rollMax: 0, frames: 0, empty: 0, seconds: 0 };
    let changed = false;
    for (let i = 0; i < 60 * fps && world.voyage.flight; i++) {
      t += 1 / fps;
      if (midTo !== null && !changed && i === Math.round(1.2 * fps)) { world.flyTo(midTo, t); changed = true; }
      world.setCamera(0, t);
      const pos = cam.position.clone(), dir = dirOf();
      if (prev) {
        const vel = pos.clone().sub(prev);
        const flatV = new THREE.Vector3(vel.x, 0, vel.z), flatD = new THREE.Vector3(dir.x, 0, dir.z);
        if (flatV.length() * fps > 8 && flatD.lengthSq() > 1e-6) {           // only while really moving
          const a = THREE.MathUtils.radToDeg(flatV.angleTo(flatD));
          m.backMax = Math.max(m.backMax, a);
        }
        m.turnMax = Math.max(m.turnMax, THREE.MathUtils.radToDeg(dir.angleTo(prevDir)) * fps);
      }
      m.clearMin = Math.min(m.clearMin, pos.y - world.groundUnder(pos.x, pos.z));
      const right = new THREE.Vector3(1, 0, 0).applyQuaternion(cam.quaternion);
      m.rollMax = Math.max(m.rollMax, Math.abs(THREE.MathUtils.radToDeg(Math.asin(THREE.MathUtils.clamp(right.y, -1, 1)))));
      m.frames++;
      if (!anyIslandInView()) m.empty++;
      prev = pos; prevDir = dir;
    }
    m.seconds = +(m.frames / fps).toFixed(2);
    m.empty = +(m.empty / Math.max(1, m.frames)).toFixed(2);
    for (const k of ['backMax', 'turnMax', 'clearMin', 'rollMax']) m[k] = Math.round(m[k]);
    return m;
  };
  const rows = [];
  const n = ISLANDS.length;
  for (let a = 0; a < n; a++) for (let b = 0; b < n; b++) if (a !== b) rows.push({ flight: `${a}->${b}`, ...flyAndMeasure(a, b) });
  // a change of mind 1.2 s into the flight
  rows.push({ flight: '1->2 then 0', ...flyAndMeasure(1, 2, 0) });
  rows.push({ flight: '0->1 then 2', ...flyAndMeasure(0, 1, 2) });
  rows.push({ flight: '3->4 then 2', ...flyAndMeasure(3, 4, 2) });
  world.size = keep;
  if (keep) world.frameFor(keep[0], keep[1]);
  const worst = (k, dir = 1) => rows.reduce((w, r) => (dir * r[k] > dir * w[k] ? r : w));
  return {
    rows,
    worst: {
      backwards: worst('backMax'), turn: worst('turnMax'), clearance: worst('clearMin', -1),
      roll: worst('rollMax'), empty: worst('empty'),
    },
  };
}
