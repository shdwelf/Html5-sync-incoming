/* chip.js — an original SID/chiptune-style WebAudio engine for the documentary.
   Two-oscillator + triangle + noise voices with a simple pattern/loop song model.
   Every note is synthesized live; nothing is sampled from anywhere. */
(function () {
  "use strict";
  const n = (m) => 440 * Math.pow(2, (m - 69) / 12);
  let AC = null, master = null, playing = false, timer = null;
  let stepIdx = 0, nextT = 0;

  // SONG = { bpm, len (steps), lead:[..], bass:[..], arpStep }
  // note values: midi int, -1=rest, 0=hold previous
  const SONG = {
    bpm: 136,
    len: 32,
    lead: [57, 57, 60, 57, 64, -1, 62, 60, 57, 57, 60, 57, 65, 64, 62, -1,
           57, 57, 60, 57, 64, -1, 67, 65, 64, 62, 60, 59, 60, -1, -1, -1],
    bass: [45, 0, 45, 0, 45, 0, 43, 0, 45, 0, 45, 0, 48, 0, 47, 0,
           45, 0, 45, 0, 45, 0, 43, 0, 41, 0, 43, 0, 45, 0, 0, 0],
    arp: [69, 72, 76, 81, 69, 72, 76, 81, 67, 71, 74, 79, 67, 71, 74, 79]
  };

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
    const s = AC.createBufferSource(), g = AC.createGain(); s.buffer = b; s.connect(g); g.connect(master);
    g.gain.setValueAtTime(vol, when);
    g.gain.exponentialRampToValueAtTime(0.0004, when + dur);
    s.start(when);
  }
  function schedule() {
    while (nextT < AC.currentTime + 0.16) {
      const i = stepIdx % SONG.len;
      const stepDur = 60 / SONG.bpm / 4; // 16th
      const L = SONG.lead[i], B = SONG.bass[i];
      if (L > 0) osc("square", n(L), nextT, stepDur * 0.92, 0.07);
      if (B > 0) osc("triangle", n(B), nextT, stepDur * 3.2, 0.13);
      // quick arpeggio on the lead chord every other step
      if (i % 2 === 0 && L > 0) {
        const a = SONG.arp[(i / 2) % SONG.arp.length];
        osc("square", n(a), nextT + stepDur * 0.5, stepDur * 0.45, 0.025);
      }
      if (i % 8 === 6) noise(nextT, stepDur * 0.7, 0.09); // snare accent
      if (i % 8 === 0) osc("triangle", n(B + 0), nextT, stepDur * 2, 0.05);
      nextT += stepDur; stepIdx++;
    }
  }
  function start() {
    init();
    if (playing) return;
    playing = true; stepIdx = 0; nextT = AC.currentTime + 0.06;
    master.gain.linearRampToValueAtTime(0.6, AC.currentTime + 0.15);
    timer = setInterval(schedule, 28);
  }
  function stop() {
    playing = false; clearInterval(timer); timer = null;
    if (master && AC) master.gain.linearRampToValueAtTime(0.0001, AC.currentTime + 0.1);
  }
  function toggle() {
    if (playing) stop(); else start();
    return playing;
  }
  // tiny blip for buttons (attract)
  function blip(freq) {
    if (!AC) return;
    osc("square", freq, AC.currentTime, 0.08, 0.06);
  }
  window.chip = { start, stop, toggle, blip, get playing() { return playing; } };
})();
