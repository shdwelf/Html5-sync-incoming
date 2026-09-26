(function () {
  "use strict";
  const CHAPTERS = [
    ["index", "Home"],
    ["arcade", "Arcade"],
    ["scene", "Demoscene"],
    ["eggs", "Easter Eggs"],
    ["presskit", "Press Kits"],
    ["gamewizard", "GameWizard"],
    ["ctf", "CTF"]
  ];
  // Strip a trailing extension only. `.replace(".html", "")` replaced the FIRST
  // ".html" anywhere in the segment, so a page named `foo.html.bak.html` or a
  // directory named `.html` mapped to the wrong chapter.
  const page = (location.pathname.split("/").pop() || "index.html").replace(/\.html?$/i, "");
  const host = document.getElementById("top");
  if (!host) return;

  let brand = document.createElement("span");
  brand.className = "brand";
  brand.innerHTML = "SECRETS OF THE SCREEN<small>an original media-history documentary</small>";
  host.appendChild(brand);

  let nav = document.createElement("nav");
  CHAPTERS.forEach(([name, label]) => {
    const a = document.createElement("a");
    if (name === "index") a.href = (page === "index" ? "index.html" : "../index.html");
    else a.href = (page === "index" ? "chapters/" + name + ".html" : "../chapters/" + name + ".html");
    a.textContent = label;
    if (name === page || (name === "index" && page === "index")) a.className = "on";
    nav.appendChild(a);
  });
  host.appendChild(nav);

  // ---- music control: song select + play/stop ----
  // The song list is chip.js's, not a copy of it. This used to fall back to a
  // hardcoded ["title","arcade","ballad"] when window.chip was absent, which
  // (a) duplicated chip.js's SONGS keys so the two could drift silently, and
  // (b) rendered a play button that did nothing at all. No engine -> no control.
  const songs = (window.chip && window.chip.songs) || [];
  if (songs.length) {
    const right = document.createElement("span");
    right.className = "right";
    right.style.cssText = "display:flex;gap:6px;align-items:center";

    const sel = document.createElement("select");
    sel.className = "mini";
    sel.style.cssText = "border:1px solid var(--line);background:#0a0e18;color:var(--ink);padding:6px 8px;font:inherit;font-size:11px";
    songs.forEach(s => {
      const o = document.createElement("option");
      o.value = s; o.textContent = "♪ " + s;
      sel.appendChild(o);
    });

    const m = document.createElement("button");
    m.className = "mini"; m.textContent = "▶ play";
    function refresh() { m.textContent = window.chip && window.chip.playing ? "■ stop" : "▶ play"; }
    sel.addEventListener("change", () => { if (window.chip) window.chip.playSong(sel.value); });
    m.addEventListener("click", () => {
      if (!window.chip) return;
      const on = window.chip.toggle();
      if (on) window.chip.playSong(sel.value);
      refresh();
    });
    // periodic refresh so state label stays honest
    setInterval(refresh, 500);
    right.appendChild(sel);
    right.appendChild(m);
    host.appendChild(right);
  }
})();
