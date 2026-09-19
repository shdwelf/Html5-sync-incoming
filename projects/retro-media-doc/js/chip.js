/* chip.js — an original SID/chiptune-style WebAudio engine for the documentary.
   Pattern/step sequencer with several selectable songs (title / arcade / ballad).
   Every note is synthesized live; nothing is sampled from anywhere. */
(function () {
  "use strict";
  const n = (m) => 440 * Math.pow(2, (m - 69) / 12);
  let AC = null, master = null, playing = false, timer = null;
  let stepIdx = 0, nextT = 0;
  let curSong = null;

  /* ---------------- songs ---------------- */
  const S = (bpm, len, lead, bass, arpIdx, opts) => ({ bpm, len, lead, bass, arpIdx, opts: opts || {} });

  // Title — bright, driving square lead, quick arpeggios.
  const TITLE_LEAD = [57,57,60,57, 64,-1,62,60, 57,57,60,57, 65,64,62,-1,
                      57,57,60,57, 64,-1,67,65, 64,62,60,59, 60,-1,-1,-1];
  const TITLE_BASS = [45,0,45,0, 45,0,43,0, 45,0,45,0, 48,0,47,0,
                      45,0,45,0, 45,0,43,0, 41,0,43,0, 45,0,0,0];
  const TITLE_ARP = [69,72,76,81, 69,72,76,81, 67,71,74,79, 67,71,74,79];

  // Arcade — minor, pulse-y, denser arpeggio, hats accent.
  const ARC_LEAD = [57,-1,56,-1, 55,-1,53,-1, 55,-1,56,-1, 57,-1,60,-1,
                    57,-1,56,-1, 55,-1,53,-1, 52,-1,55,-1, 53,-1,55,-1];
  const ARC_BASS = [33,0,33,0, 31,0,31,0, 29,0,29,0, 28,0,28,0,
                    33,0,33,0, 31,0,31,0, 29,0,29,0, 27,0,31,0];
  const ARC_ARP = [45,48,52,57, 45,48,52,57, 43,47,50,55, 43,47,50,55];

  // Ballad — slower, major, airy: triangle melody + soft pulse pad.
  const BAL_LEAD = [64,-1,69,-1, 71,-1,69,-1, 67,-1,64,-1, 62,-1,60,-1,
                    64,-1,69,-1, 71,-1,72,71, 69,-1,67,-1, 64,-1,-1,-1];
  const BAL_BASS = [48,0,48,0, 45,0,45,0, 43,0,43,0, 40,0,40,0,
                    48,0,48,0, 45,0,45,0, 43,0,43,0, 48,0,48,0];
  const BAL_ARP = [64,67,71,74, 64,67,71,74, 62,65,69,72, 60,64,67,71];

  const SONGS = {
    title: S(138, 32, TITLE_LEAD, TITLE_BASS, TITLE_ARP, { vol: 0.6 }),
    arcade: S(150, 32, ARC_LEAD, ARC_BASS, ARC_ARP, { vol: 0.62, noise: true }),
    ballad: S(96, 32, BAL_LEAD, BAL_BASS, BAL_ARP, { vol: 0.55, soft: true })
  };
  // tag each song with its own key
  for (const k in SONGS) SONGS[k].name = k;

  function init() {
    if (!AC) {
      AC = new (window.AudioContext || window.webkitAudioContext)();
      master = AC.createGain(); master.gain.value = 0.0; master.connect(AC.destination);
    }
    if (AC.state === "suspended") AC.resume();
  }
  function osc(type, freq, when, dur, vol, dest) {
    const o = AC.createOscillator(), g = AC.createGain();
    o.type = type; o.frequency.value = freq; o.connect(g); g.connect(dest || master);
    g.gain.setValueAtTime(0, when);
    g.gain.linearRampToValueAtTime(vol, when + 0.012);
    g.gain.exponentialRampToValueAtTime(0.0004, when + dur);
    o.start(when); o.stop(when + dur + 0.05);
    return o;
  }
  function noise(when, dur, vol) {
    const len = Math.max(1, Math.floor(AC.sampleRate * dur));
    const b = AC.createBuffer(1, len, AC.sampleRate), d = b.getChannelData(0);
    for (let i = 0; i < len; i++) d[i] = Math.random() * 2 - 1;
    const s = AC.createBufferSource(), g = AC.createGain();
    s.buffer = b; s.connect(g); g.connect(master);
    g.gain.setValueAtTime(vol, when);
    g.gain.exponentialRampToValueAtTime(0.0004, when + dur);
    s.start(when);
  }
  function schedule() {
    const s = curSong; if (!s) return;
    const len = s.len, stepDur = 60 / s.bpm / 4;
    while (nextT < AC.currentTime + 0.16) {
      const i = stepIdx % len;
      const L = s.lead[i], B = s.bass[i];
      const soft = s.opts.soft;
      if (L > 0) osc(soft ? "triangle" : "square", n(L), nextT, stepDur * 0.94, soft ? 0.13 : 0.07);
      if (B > 0) osc("triangle", n(B), nextT, stepDur * 3.4, soft ? 0.14 : 0.11);
      // arpeggio shimmer every other step
      if (!soft && i % 2 === 0 && L > 0) {
        const a = s.arpIdx[Math.floor((i / 2) % s.arpIdx.length)];
        osc("square", n(a), nextT + stepDur * 0.5, stepDur * 0.45, 0.022);
      } else if (soft && i % 4 === 0) {
        const a = s.arpIdx[Math.floor((i / 4) % s.arpIdx.length)];
        osc("sine", n(a), nextT, stepDur * 1.5, 0.03);
      }
      if (s.opts.noise && i % 8 === 6) noise(nextT, stepDur * 0.6, 0.07); // hat/perc
      if (i % 16 === 0) osc("triangle", n(B), nextT, stepDur * 2.2, 0.05);
      nextT += stepDur; stepIdx++;
    }
  }
  function start() {
    init(); if (!curSong) curSong = SONGS.title;
    if (playing) return;
    playing = true; stepIdx = 0; nextT = AC.currentTime + 0.06;
    master.gain.linearRampToValueAtTime(curSong.opts.vol || 0.6, AC.currentTime + 0.15);
    timer = setInterval(schedule, 28);
  }
  function stop() {
    playing = false; clearInterval(timer); timer = null;
    if (master && AC) master.gain.linearRampToValueAtTime(0.0001, AC.currentTime + 0.1);
  }
  function playSong(name) {
    const s = SONGS[name]; if (!s) return;
    curSong = s;
    if (playing) { // restart with new song
      stop(); start();
    }
    return true;
  }
  function toggle() {
    if (playing) stop(); else start();
    return playing;
  }
  function blip(freq) {
    if (!AC) return;
    osc("square", freq || 700, AC.currentTime, 0.08, 0.06);
  }
  window.chip = {
    songs: Object.keys(SONGS),
    current() { return curSong ? curSong.name : null; },
    start, stop, toggle, playSong, blip,
    get playing() { return playing; }
  };
})();
