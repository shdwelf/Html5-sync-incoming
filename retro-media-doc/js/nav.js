(function () {
  "use strict";
  const CHAPTERS = [
    ["index", "Home"],
    ["arcade", "Arcade"],
    ["scene", "Demoscene"],
    ["eggs", "Easter Eggs"],
    ["presskit", "Press Kits"],
    ["gamewizard", "GameWizard"]
  ];
  // figure current page name from location
  const page = (location.pathname.split("/").pop() || "index.html").replace(".html", "");

  const host = document.getElementById("top");
  if (!host) return;
  let brand = document.createElement("span");
  brand.className = "brand";
  brand.innerHTML = "SECRETS OF THE SCREEN<small>an original media-history documentary</small>";
  host.appendChild(brand);

  let nav = document.createElement("nav");
  CHAPTERS.forEach(([name, label]) => {
    const a = document.createElement("a");
    a.href = (name === "index" ? "../index.html" : "../chapters/" + name + ".html");
    // handle being on index (no chapters/ prefix)
    if (page === "index" && name !== "index") a.href = "chapters/" + name + ".html";
    if (name === "index") a.href = page === "index" ? "index.html" : "../index.html";
    a.textContent = label;
    if (name === page || (name === "index" && page === "index")) a.className = "on";
    nav.appendChild(a);
  });
  host.appendChild(nav);

  const right = document.createElement("span");
  right.className = "right";
  const m = document.createElement("button");
  m.className = "mini";
  m.textContent = "♪ music";
  m.addEventListener("click", () => {
    const on = window.chip && window.chip.toggle();
    m.textContent = on ? "♪ on" : "♪ off";
  });
  right.appendChild(m);
  host.appendChild(right);
})();
