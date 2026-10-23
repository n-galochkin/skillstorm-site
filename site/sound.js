/* The soundscape, from recorded clips (assets/sfx, cut into seamless loops): a soft wind and,
   far below, the sea under everything; now and then gulls off to one side; in flight the rush of
   air, louder and brighter the faster it goes (Nikita 2026-10-23: "звук полёта - это не взмах
   крыльев, а просто ветер"; the sea "едва слышно, до воды далеко").

   Browsers start sound only after the visitor does something (a click, a tap, a key - not the
   wheel), so start() is called from the first such event; until then nothing plays.
   Under it all, quietly, the game's own music (its piano, strings and percussion loops mixed into
   one; Nikita 2026-10-23: "музыку из нашей игры на фон, только тихо"). */

const FILES = { music: 'assets/sfx/music.mp3', sea: 'assets/sfx/sea.mp3', bed: 'assets/sfx/wind-bed.mp3', flight: 'assets/sfx/wind-flight.mp3', gulls: 'assets/sfx/gulls.mp3' };

export class Soundscape {
  constructor() {
    this.ctx = null;
    this.muted = false;
    this.time = 0;
    this.nextGull = 7;
    this.buffers = {};
  }

  start() {
    if (this.ctx) { if (this.ctx.state === 'suspended' && !this.muted) this.ctx.resume(); return; }
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return;
    const ctx = this.ctx = new AC();
    this.master = ctx.createGain();
    this.master.gain.value = this.muted ? 0 : 1;
    this.master.connect(ctx.destination);
    const gain = (v) => { const g = ctx.createGain(); g.gain.value = v; return g; };
    this.sea = gain(0);
    this.bed = gain(0);
    this.flight = gain(0);
    this.music = gain(0);
    this.music.connect(this.master);
    this.flightTone = ctx.createBiquadFilter();
    this.flightTone.type = 'lowpass';
    this.flightTone.frequency.value = 900;
    this.sea.connect(this.master);
    this.bed.connect(this.master);
    this.flightTone.connect(this.flight).connect(this.master);
    // the clips load once sound is allowed; each loop starts as soon as its clip is in
    const load = async (key) => {
      const res = await fetch(FILES[key]);
      return ctx.decodeAudioData(await res.arrayBuffer());
    };
    const loop = (buf, dest, from = Math.random() * (buf.duration - 0.1)) => {
      const s = ctx.createBufferSource();
      s.buffer = buf; s.loop = true;
      // (an mp3 may carry a few ms of encoder padding at either end; the loop skips it)
      s.loopStart = 0.03; s.loopEnd = buf.duration - 0.03;
      s.connect(dest);
      s.start(0, from);
      return s;
    };
    for (const key of Object.keys(FILES)) {
      load(key).then((buf) => {
        this.buffers[key] = buf;
        if (key === 'music') loop(buf, this.music, 0.03);
        if (key === 'sea') loop(buf, this.sea);
        if (key === 'bed') loop(buf, this.bed);
        if (key === 'flight') this.flightSrc = loop(buf, this.flightTone);
      }).catch(() => { /* a missing clip leaves that layer silent */ });
    }
  }

  setMuted(m) {
    this.muted = m;
    if (!this.ctx) return;
    this.master.gain.setTargetAtTime(m ? 0 : 1, this.ctx.currentTime, 0.15);
    if (!m && this.ctx.state === 'suspended') this.ctx.resume();
  }

  /* kept for the page's call on take-off: the flight's sound is only the wind now */
  takeOff() {}

  /* a few seconds of the gulls' clip, faded in and out, off to one side */
  gulls(at) {
    const ctx = this.ctx, buf = this.buffers.gulls;
    if (!buf) return;
    const len = 3.5 + Math.random() * 3;
    const from = Math.random() * Math.max(0, buf.duration - len);
    const s = ctx.createBufferSource();
    s.buffer = buf;
    const g = ctx.createGain();
    const v = 0.1 + Math.random() * 0.08;
    g.gain.setValueAtTime(0, at);
    g.gain.linearRampToValueAtTime(v, at + 0.8);
    g.gain.setValueAtTime(v, at + len - 1);
    g.gain.linearRampToValueAtTime(0, at + len);
    let out = g;
    if (ctx.createStereoPanner) {
      const p = ctx.createStereoPanner();
      p.pan.value = (Math.random() < 0.5 ? -1 : 1) * (0.3 + Math.random() * 0.5);
      g.connect(p); out = p;
    }
    s.connect(g); out.connect(this.master);
    s.start(at, from, len);
  }

  /* every frame: speed in m/s, height over the sea in m, whether it is flying or in the fight */
  update(dt, { speed = 0, height = 130, flying = false, playing = false } = {}) {
    this.time += dt;
    if (!this.ctx || this.ctx.state !== 'running') return;
    const now = this.ctx.currentTime;
    const k = Math.min(1, speed / 320);
    // flight: the rush of air, louder and brighter with the speed
    this.flight.gain.setTargetAtTime(0.85 * Math.pow(k, 1.2), now, 0.15);
    this.flightTone.frequency.setTargetAtTime(700 + 6000 * k * k, now, 0.15);
    if (this.flightSrc) this.flightSrc.playbackRate.setTargetAtTime(0.85 + 0.3 * k, now, 0.2);
    // the bed: a soft wind, stepping back while the air rushes and in the fight
    const bed = playing ? 0.5 : 1 - 0.7 * k;
    this.bed.gain.setTargetAtTime((0.16 + 0.04 * Math.sin(this.time * 0.29)) * bed, now, 0.8);
    // the sea is far below: barely there over an island, nearer only as it dives to the water
    const t = Math.min(1, Math.max(0, (150 - height) / 105));
    const near = t * t * (3 - 2 * t);
    this.sea.gain.setTargetAtTime((0.05 + 0.25 * near) * bed, now, 0.9);
    // the music: quiet, a touch quieter still while the air rushes
    this.music.gain.setTargetAtTime(0.13 * (1 - 0.3 * k), now, 1.2);
    // gulls now and then, while it holds over an island
    if (this.time >= this.nextGull) {
      this.nextGull = this.time + 14 + Math.random() * 16;
      if (!flying && !playing) this.gulls(now + 0.05);
    }
  }
}
