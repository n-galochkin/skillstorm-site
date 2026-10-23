/* The soundscape, made in the browser (Web Audio), so nothing to license or download: the sea and
   a soft wind under everything, now and then gulls far off, and in flight the bird itself - wing
   beats as it lifts off and climbs, the rush of air rising with its speed.

   Browsers start sound only after the visitor does something (a click, a tap, a key - not the
   wheel), so start() is called from the first such event; until then nothing plays. */

export class Soundscape {
  constructor() {
    this.ctx = null;
    this.muted = false;
    this.nextGull = 6;
    this.nextSwell = 0;
    this.flapUntil = 0;
    this.nextFlap = 0;
    this.time = 0;
  }

  start() {
    if (this.ctx) { if (this.ctx.state === 'suspended' && !this.muted) this.ctx.resume(); return; }
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return;
    const ctx = this.ctx = new AC();
    this.master = ctx.createGain();
    this.master.gain.value = this.muted ? 0 : 0.9;
    const comp = ctx.createDynamicsCompressor();
    comp.threshold.value = -16; comp.ratio.value = 3;
    this.master.connect(comp).connect(ctx.destination);

    // noise: white for air and foam, brown (integrated white) for the deep roll of the sea
    const len = ctx.sampleRate * 3;
    const white = ctx.createBuffer(1, len, ctx.sampleRate);
    const brown = ctx.createBuffer(1, len, ctx.sampleRate);
    const w = white.getChannelData(0), b = brown.getChannelData(0);
    let last = 0;
    for (let i = 0; i < len; i++) {
      w[i] = Math.random() * 2 - 1;
      last = (last + 0.02 * w[i]) / 1.02;
      b[i] = last * 3.5;
    }
    this.white = white;
    const loop = (buf) => { const s = ctx.createBufferSource(); s.buffer = buf; s.loop = true; s.loopStart = Math.random(); s.start(); return s; };
    const filter = (type, freq, q = 0.7) => { const f = ctx.createBiquadFilter(); f.type = type; f.frequency.value = freq; f.Q.value = q; return f; };
    const gain = (v) => { const g = ctx.createGain(); g.gain.value = v; return g; };

    // a room of open air for the far sounds: a short decaying noise tail
    this.verb = ctx.createConvolver();
    const ir = ctx.createBuffer(2, ctx.sampleRate * 2.4, ctx.sampleRate);
    for (let c = 0; c < 2; c++) {
      const d = ir.getChannelData(c);
      for (let i = 0; i < d.length; i++) d[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / d.length, 3);
    }
    this.verb.buffer = ir;
    this.verbOut = gain(0.5);
    this.verb.connect(this.verbOut).connect(this.master);

    // the sea: a low roll that swells and ebbs, and the hiss of foam riding on the swell
    this.sea = gain(0);
    loop(brown).connect(filter('lowpass', 420)).connect(this.sea).connect(this.master);
    this.foam = gain(0);
    loop(white).connect(filter('bandpass', 2600, 0.6)).connect(this.foam).connect(this.master);
    // a soft wind over everything
    this.breeze = gain(0.02);
    loop(white).connect(filter('bandpass', 520, 0.9)).connect(this.breeze).connect(this.master);

    // flight: the rush of air past the bird (its pitch and loudness follow the speed) and a low
    // rumble under it
    this.rushFilter = filter('bandpass', 400, 0.8);
    this.rush = gain(0);
    loop(white).connect(this.rushFilter).connect(this.rush).connect(this.master);
    this.rumble = gain(0);
    loop(brown).connect(filter('lowpass', 160)).connect(this.rumble).connect(this.master);
  }

  setMuted(m) {
    this.muted = m;
    if (!this.ctx) return;
    this.master.gain.setTargetAtTime(m ? 0 : 0.9, this.ctx.currentTime, 0.15);
    if (!m && this.ctx.state === 'suspended') this.ctx.resume();
  }

  /* a beat of the wings: a soft thump of air, down-stroke louder than the up-stroke */
  wingBeat(at, strength = 1) {
    const ctx = this.ctx;
    for (const [dt, v, f] of [[0, 0.32, 900], [0.11, 0.14, 1400]]) {
      const s = ctx.createBufferSource();
      s.buffer = this.white;
      const lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = f * (0.85 + Math.random() * 0.3);
      const g = ctx.createGain();
      const t = at + dt;
      g.gain.setValueAtTime(0, t);
      g.gain.linearRampToValueAtTime(v * strength, t + 0.018);
      g.gain.exponentialRampToValueAtTime(0.0008, t + 0.16);
      s.connect(lp).connect(g).connect(this.master);
      s.start(t, Math.random() * 2, 0.2);
    }
  }

  /* a few beats as it lifts off */
  takeOff() {
    if (!this.ctx) return;
    this.flapUntil = this.time + 1.1;
  }

  /* a gull far off: a falling, slightly rough cry, two or three times, somewhere left or right */
  gull(at) {
    const ctx = this.ctx;
    const pan = ctx.createStereoPanner ? ctx.createStereoPanner() : null;
    if (pan) pan.pan.value = Math.random() * 1.6 - 0.8;
    const out = ctx.createGain();
    out.gain.value = 0.03 + Math.random() * 0.025;
    const dest = pan ? (out.connect(pan), pan) : out;
    dest.connect(this.master);
    dest.connect(this.verb);
    const calls = 2 + Math.floor(Math.random() * 3);
    const base = 1500 + Math.random() * 500;
    for (let k = 0; k < calls; k++) {
      const t = at + k * (0.26 + Math.random() * 0.08);
      const o = ctx.createOscillator();
      o.type = 'sawtooth';
      o.frequency.setValueAtTime(base * 1.15, t);
      o.frequency.exponentialRampToValueAtTime(base * 0.62, t + 0.2);
      const vib = ctx.createOscillator(); vib.frequency.value = 38;
      const vibG = ctx.createGain(); vibG.gain.value = 40;
      vib.connect(vibG).connect(o.frequency);
      const bp = ctx.createBiquadFilter(); bp.type = 'bandpass'; bp.frequency.value = base; bp.Q.value = 2.2;
      const g = ctx.createGain();
      g.gain.setValueAtTime(0, t);
      g.gain.linearRampToValueAtTime(1, t + 0.03);
      g.gain.exponentialRampToValueAtTime(0.001, t + 0.22);
      o.connect(bp).connect(g).connect(out);
      o.start(t); o.stop(t + 0.25); vib.start(t); vib.stop(t + 0.25);
    }
  }

  /* every frame: speed in m/s, climb in m/s (up +), height over the sea in m, whether it is flying */
  update(dt, { speed = 0, climb = 0, height = 130, flying = false, playing = false } = {}) {
    this.time += dt;
    if (!this.ctx || this.ctx.state !== 'running') return;
    const now = this.ctx.currentTime;
    const k = Math.min(1, speed / 320);
    this.rush.gain.setTargetAtTime(0.42 * Math.pow(k, 1.3), now, 0.12);
    this.rushFilter.frequency.setTargetAtTime(320 + 1300 * k, now, 0.12);
    this.rumble.gain.setTargetAtTime(0.5 * k, now, 0.15);
    // the sea and the breeze step back while the air rushes, and in the fight
    const bed = playing ? 0.45 : 1 - 0.55 * k;
    // the sea is far below: barely there over an island, near only when it dives to the water
    // (Nikita 2026-10-23: "должен быть слышен очень тихо, потому что до воды далеко")
    const t = Math.min(1, Math.max(0, (160 - height) / 115));
    const near = 0.08 + 0.92 * t * t * (3 - 2 * t);
    this.sea.gain.setTargetAtTime((this.seaLevel || 0.18) * bed * near, now, 0.9);
    this.foam.gain.setTargetAtTime((this.foamLevel || 0.012) * bed * near, now, 0.8);
    if (this.time >= this.nextSwell) {
      this.nextSwell = this.time + 3.5 + Math.random() * 4;
      this.seaLevel = 0.12 + Math.random() * 0.14;
      this.foamLevel = 0.006 + Math.random() * 0.014;
    }
    this.breeze.gain.setTargetAtTime((0.018 + 0.01 * Math.sin(this.time * 0.37)) * bed, now, 0.8);
    // wing beats: lifting off, and whenever it climbs hard
    if ((this.time < this.flapUntil || (flying && climb > 25)) && this.time >= this.nextFlap) {
      this.nextFlap = this.time + 0.21 + Math.random() * 0.05;
      this.wingBeat(now + 0.01, this.time < this.flapUntil ? 1 : Math.min(1, climb / 60));
    }
    // gulls now and then, while it holds over an island
    if (this.time >= this.nextGull) {
      this.nextGull = this.time + 9 + Math.random() * 14;
      if (!flying && !playing) this.gull(now + 0.05);
    }
  }
}
