/* stage.js — shared animated "attract screen" backdrop for documentary heroes.
   Pure Canvas: raster bars + starfield + a small bouncing mark. Original. */
(function () {
  "use strict";
  const PAL = ["#000", "#fff", "#883932", "#67b6bd", "#8b3e94", "#55a049", "#40318d",
               "#bfce72", "#8b6f47", "#c0722f", "#78c0fb", "#9f79d3", "#4d8707", "#6ffb77", "#c46b8e", "#c2c2c2"];
  const ROWS = ["#40318d", "#12071f", "#1f0f3a", "#12071f"]; // bar cycle (indexes fine)
  const stars = [];
  for (let i = 0; i < 90; i++) stars.push({ x: Math.random(), y: Math.random(), s: Math.random() });

  function run(canvas, { title = "", sub = "", color = 10 } = {}) {
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    let raf = null, t = 0, W = 0, H = 0;
    function resize() {
      W = canvas.width = canvas.clientWidth * devicePixelRatio;
      H = canvas.height = canvas.clientHeight * devicePixelRatio;
    }
    window.addEventListener("resize", resize); resize();

    const barStep = 8;
    function frame() {
      t += 1 / 60;
      ctx.fillStyle = "#000"; ctx.fillRect(0, 0, W, H);
      // vertical raster bars sweeping
      const off = Math.floor(t * 30);
      for (let y = -barStep; y < H + barStep; y += barStep) {
        const row = Math.floor(y / barStep);
        const shifted = row - off;
        ctx.fillStyle = PAL[6 + (Math.abs(shifted) % 2)] ;
        ctx.fillRect(0, y, W * 0.5, barStep + 1);
        ctx.fillStyle = PAL[4 + (Math.abs(shifted + 1) % 2)];
        ctx.fillRect(W * 0.5, y, W * 0.5, barStep + 1);
      }
      // centre content band stays readable
      ctx.fillStyle = "rgba(0,0,0,0.55)";
      ctx.fillRect(0, H * 0.30, W, H * 0.4);
      // starfield
      ctx.fillStyle = "#fff";
      for (const s of stars) {
        const sx = (s.x * W) % W;
        const sy = (s.y * H + t * (1 + s.s * 3)) % H;
        const a = 0.3 + 0.7 * s.s;
        ctx.globalAlpha = a; ctx.fillRect(sx, sy, 1.6, 1.6);
      }
      ctx.globalAlpha = 1;
      // title
      ctx.textAlign = "center";
      ctx.font = (Math.min(W, 700) * 0.05) + 'px "Courier New", monospace';
      ctx.fillStyle = PAL[color]; ctx.shadowColor = PAL[color]; ctx.shadowBlur = 14;
      ctx.fillText(title, W / 2, H * 0.42);
      ctx.shadowBlur = 0;
      ctx.font = (Math.min(W, 700) * 0.018) + 'px monospace';
      ctx.fillStyle = PAL[15];
      ctx.fillText(sub || "", W / 2, H * 0.52);
      raf = requestAnimationFrame(frame);
    }
    frame();
    return () => { cancelAnimationFrame(raf); };
  }
  window.stageRun = run;
  window.PAL16 = PAL;
})();
