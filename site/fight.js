/* The fight, staged on its own island. The rule that makes the game what it is:
   you move, the hero shoots by itself, and only while you stand still. */
import * as THREE from 'three';
import { clone as cloneSkinned } from 'three/skeleton';

const HERO_SPEED = 5.2;
const BOT_SPEED = 3.3;
const SHOT_RANGE = 13;
const HERO_COOLDOWN = 0.46;
const BOT_COOLDOWN = 1.9;
const PROJ_SPEED = 17;
const HERO_HP = 120;
const BOT_HP = 55;
const TINT = [0xcf5b4a, 0x4a8ccf, 0x6fae4f, 0xb574c9, 0xd8a33c];

class Fighter {
  constructor(fight, { isHero, lx, lz, tint }) {
    const { world, assets, spec } = fight;
    this.fight = fight;
    this.isHero = isHero;
    this.maxHp = isHero ? HERO_HP : BOT_HP;
    this.hp = this.maxHp;
    this.cooldown = Math.random() * 0.9;
    this.alive = true;
    this.attackTimer = 0;

    const root = cloneSkinned(assets.models.villager);
    root.position.set(spec.pos[0] + lx, 0, spec.pos[1] + lz);
    root.traverse((o) => {
      if (!o.isMesh && !o.isSkinnedMesh) return;
      o.frustumCulled = false;
      const mats = Array.isArray(o.material) ? o.material : [o.material];
      const next = mats.map((m) => {
        const c = m.clone();
        if (!isHero && tint !== undefined) c.color = new THREE.Color(tint).lerp(c.color, 0.45);
        return c;
      });
      o.material = next.length === 1 ? next[0] : next;
    });
    this.root = root;

    if (assets.models.sword) {
      const sword = assets.models.sword.clone(true);
      let hand = null;
      root.traverse((o) => {
        if (hand) return;
        const n = (o.name || '').toLowerCase();
        if (n.includes('hand_r') || n.includes('righthand') || n.includes('r_hand')) hand = o;
      });
      if (hand) { sword.rotation.set(Math.PI / 2, 0, 0); hand.add(sword); }
      else { sword.position.set(0.3, 0.5, 0.1); root.add(sword); }
    }

    this.mixer = new THREE.AnimationMixer(root);
    this.actions = {};
    for (const [key, clip] of Object.entries(assets.anims)) {
      const a = this.mixer.clipAction(clip);
      if (key === 'attack') { a.setLoop(THREE.LoopOnce); a.clampWhenFinished = true; }
      this.actions[key] = a;
    }
    this.current = null;
    this.play('idle');

    const pipGeo = new THREE.PlaneGeometry(1.2, 0.14);
    this.pipBg = new THREE.Mesh(pipGeo, new THREE.MeshBasicMaterial({
      color: 0x0d1a26, depthTest: false, transparent: true, opacity: 0.85, fog: false,
    }));
    this.pip = new THREE.Mesh(pipGeo, new THREE.MeshBasicMaterial({
      color: isHero ? 0x74d96f : 0xdc6450, depthTest: false, fog: false,
    }));
    this.pipBg.renderOrder = 20; this.pip.renderOrder = 21;
    this.pipGroup = new THREE.Group();
    this.pipGroup.add(this.pipBg, this.pip);

    const shadowGeo = new THREE.PlaneGeometry(2.2, 2.2);
    shadowGeo.rotateX(-Math.PI / 2);
    this.shadow = new THREE.Mesh(shadowGeo, world.shadowMaterial());
    this.shadow.renderOrder = 1;

    world.scene.add(root, this.pipGroup, this.shadow);
  }

  play(name) {
    if (this.attackTimer > 0) return;
    const next = this.actions[name];
    if (!next || this.current === next) return;
    next.reset().fadeIn(0.14).play();
    if (this.current) this.current.fadeOut(0.14);
    this.current = next;
  }

  strike() {
    const a = this.actions.attack;
    if (!a) return;
    const rate = 1.7;
    if (this.current) this.current.fadeOut(0.08);
    a.reset(); a.setEffectiveTimeScale(rate); a.setEffectiveWeight(1);
    a.fadeIn(0.06).play();
    this.current = a;
    this.attackTimer = a.getClip().duration / rate;
  }

  tickAnim(dt) {
    if (this.attackTimer <= 0) return;
    this.attackTimer -= dt;
    if (this.attackTimer <= 0) {
      this.attackTimer = 0;
      this.actions.attack.fadeOut(0.12);
      this.current = null;
    }
  }

  damage(n) {
    if (!this.alive) return;
    this.hp -= n;
    if (this.hp <= 0) { this.hp = 0; this.alive = false; }
  }

  dispose(world) { world.scene.remove(this.root, this.pipGroup, this.shadow); }
}

export class Fight {
  constructor(world, assets, spec) {
    this.world = world;
    this.assets = assets;
    this.spec = spec;
    this.radius = spec.radius * 0.66;
    this.fighters = [];
    this.projectiles = [];
    this.pool = [];
    this.input = { x: 0, y: 0 };
    this.playerControlled = false;
    this.kills = 0;
    this.projGeo = new THREE.SphereGeometry(0.3, 10, 8);
    this.matHero = new THREE.MeshBasicMaterial({ color: 0xffd36b, fog: false });
    this.matBot = new THREE.MeshBasicMaterial({ color: 0xff8a6b, fog: false });
  }

  ground(x, z) { return this.world.groundAt(this.spec.id, x, z); }

  spawn(botCount = 5) {
    this.clear();
    this.kills = 0;
    this.over = false;
    this.hero = new Fighter(this, { isHero: true, lx: 0, lz: 6 });
    this.fighters = [this.hero];
    for (let i = 0; i < botCount; i++) {
      const a = (i / botCount) * Math.PI * 2 + 0.5;
      const r = this.radius * (0.5 + Math.random() * 0.3);
      this.fighters.push(new Fighter(this, {
        isHero: false, lx: Math.cos(a) * r, lz: Math.sin(a) * r, tint: TINT[i % TINT.length],
      }));
    }
    this.world.mixers = this.fighters.map((f) => f.mixer);
    this.emit();
  }

  clear() {
    this.fighters.forEach((f) => f.dispose(this.world));
    this.fighters = [];
    this.projectiles.forEach((p) => this.world.scene.remove(p.mesh));
    this.projectiles = [];
    this.world.mixers = [];
  }

  emit() {
    if (!this.onChange || !this.hero) return;
    this.onChange({
      hp: this.hero.hp, maxHp: this.hero.maxHp, kills: this.kills,
      enemies: this.fighters.filter((f) => !f.isHero && f.alive).length,
    });
  }

  setInput(x, y) { this.input.x = x; this.input.y = y; }

  fire(from, to, isHero) {
    const mesh = this.pool.pop() || new THREE.Mesh(this.projGeo, isHero ? this.matHero : this.matBot);
    mesh.material = isHero ? this.matHero : this.matBot;
    mesh.position.copy(from);
    this.world.scene.add(mesh);
    this.projectiles.push({
      mesh, dir: to.clone().sub(from).setY(0).normalize(),
      isHero, life: 1.7, dmg: isHero ? 12 : 6,
    });
  }

  nearest(f) {
    let best = null, bestD = Infinity;
    for (const o of this.fighters) {
      if (!o.alive || o.isHero === f.isHero) continue;
      const d = o.root.position.distanceTo(f.root.position);
      if (d < bestD) { bestD = d; best = o; }
    }
    return { target: best, dist: bestD };
  }

  update(dt, elapsed) {
    if (!this.fighters.length) return;
    const tmp = new THREE.Vector3();
    const cx = this.spec.pos[0], cz = this.spec.pos[1];

    for (const f of this.fighters) {
      if (!f.alive) { f.root.visible = false; f.pipGroup.visible = false; f.shadow.visible = false; continue; }
      f.tickAnim(dt);
      const prevX = f.root.position.x, prevZ = f.root.position.z;
      let moving = false;

      if (f.isHero) {
        // left to itself the hero circles, so the island always looks alive
        const ix = this.playerControlled ? this.input.x : Math.sin(elapsed * 0.7) * 0.8;
        const iy = this.playerControlled ? this.input.y : Math.cos(elapsed * 0.47) * 0.8;
        const len = Math.hypot(ix, iy);
        if (len > 0.1) {
          moving = true;
          const s = HERO_SPEED * dt * Math.min(len, 1) / len;
          f.root.position.x += ix * s;
          f.root.position.z += iy * s;
          f.root.rotation.y = Math.atan2(ix, iy);
        }
      } else {
        const { target, dist } = this.nearest(f);
        if (target) {
          if (dist > SHOT_RANGE * 0.72) {
            tmp.copy(target.root.position).sub(f.root.position).setY(0).normalize();
            f.root.position.addScaledVector(tmp, BOT_SPEED * dt);
            moving = true;
          }
          f.root.rotation.y = Math.atan2(
            target.root.position.x - f.root.position.x,
            target.root.position.z - f.root.position.z,
          );
        }
      }

      const d = Math.hypot(f.root.position.x - cx, f.root.position.z - cz);
      if (d > this.radius) {
        f.root.position.x = cx + (f.root.position.x - cx) * this.radius / d;
        f.root.position.z = cz + (f.root.position.z - cz) * this.radius / d;
      }
      if (this.ground(f.root.position.x, f.root.position.z) < 0.8) {
        f.root.position.x = prevX; f.root.position.z = prevZ;
      }
      f.root.position.y = this.ground(f.root.position.x, f.root.position.z);

      f.cooldown -= dt;
      const { target, dist } = this.nearest(f);
      if (!moving && target && dist < SHOT_RANGE && f.cooldown <= 0) {
        f.cooldown = f.isHero ? HERO_COOLDOWN : BOT_COOLDOWN;
        f.root.rotation.y = Math.atan2(
          target.root.position.x - f.root.position.x,
          target.root.position.z - f.root.position.z,
        );
        tmp.copy(f.root.position).add(new THREE.Vector3(0, 1.1, 0));
        this.fire(tmp, target.root.position.clone().setY(f.root.position.y + 1.1), f.isHero);
        f.strike();
      }
      f.play(moving ? 'walk' : 'idle');

      f.shadow.position.set(f.root.position.x + 0.3, f.root.position.y + 0.08, f.root.position.z + 0.22);
      f.pipGroup.position.copy(f.root.position).add(new THREE.Vector3(0, 2.0, 0));
      f.pipGroup.quaternion.copy(this.world.camera.quaternion);
      const ratio = Math.max(f.hp / f.maxHp, 0);
      f.pip.scale.x = ratio;
      f.pip.position.x = -(1 - ratio) * 0.6;
      f.pip.position.z = 0.001;
    }

    for (let i = this.projectiles.length - 1; i >= 0; i--) {
      const p = this.projectiles[i];
      p.mesh.position.addScaledVector(p.dir, PROJ_SPEED * dt);
      p.life -= dt;
      let hit = false;
      for (const f of this.fighters) {
        if (!f.alive || f.isHero === p.isHero) continue;
        tmp.copy(f.root.position).setY(p.mesh.position.y);
        if (tmp.distanceTo(p.mesh.position) < 0.95) {
          f.damage(p.dmg);
          if (!f.alive && !f.isHero) this.kills++;
          hit = true;
          this.emit();
          break;
        }
      }
      if (hit || p.life <= 0) {
        this.world.scene.remove(p.mesh);
        this.pool.push(p.mesh);
        this.projectiles.splice(i, 1);
      }
    }

    if (!this.over && this.hero) {
      if (!this.hero.alive) { this.over = true; this.onEnd && this.onEnd(false, this.kills); }
      else if (this.fighters.every((f) => f.isHero || !f.alive)) {
        this.over = true; this.onEnd && this.onEnd(true, this.kills);
      }
    }
  }

  restart() { this.spawn(); }
}
