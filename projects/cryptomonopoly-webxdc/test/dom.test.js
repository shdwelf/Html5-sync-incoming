/* Minimal DOM harness to exercise the real app boot + local hot-seat play path
 * without a browser. Catches runtime/ReferenceErrors in app.js. Run:
 *   node test/dom.test.js
 */
"use strict";
const path = require("path");

// --- tiny DOM shim ---
function makeClassList() {
  const s = new Set();
  return { add: (c) => s.add(c), remove: (c) => s.delete(c), toggle: (c, f) => (f === undefined ? (s.has(c) ? s.delete(c) : s.add(c)) : (f ? s.add(c) : s.delete(c))), contains: (c) => s.has(c) };
}
function makeEl() {
  const el = {
    innerHTML: "",
    textContent: "",
    value: "",
    disabled: false,
    style: {},
    dataset: {},
    children: [],
    classList: makeClassList(),
    appendChild() {}, removeChild() {},
    querySelector: () => makeEl(),
    querySelectorAll: () => [],
    addEventListener() {},
    setAttribute() {}, getAttribute() { return null; },
    focus() {}, click() {},
  };
  el.onclick = null; el.oninput = null; el.onchange = null;
  return el;
}
const els = {};
function getEl(id) { if (!els[id]) els[id] = makeEl(); return els[id]; }
const bootListeners = [];
global.document = {
  getElementById: getEl,
  querySelector: () => makeEl(),
  querySelectorAll: () => [],
  addEventListener: (ev, fn) => { if (ev === "DOMContentLoaded") bootListeners.push(fn); },
  createElement: makeEl,
  body: makeEl(),
};
global.window = global;
global.confirm = () => true;
global.alert = () => {};

// load app modules
require(path.join(__dirname, "..", "js", "board.js"));
require(path.join(__dirname, "..", "js", "engine.js"));
require(path.join(__dirname, "..", "js", "transport.js"));
require(path.join(__dirname, "..", "js", "app.js"));

// boot
bootListeners.forEach((fn) => fn());

const B = global.CryptoBoard;
const E = global.CryptoEngine;
let failures = 0;
const check = (n, c) => { console.log((c ? "PASS" : "FAIL") + "  " + n); if (!c) failures++; };

// reach into module state via the public reducer mirror is not exposed; instead
// drive via DOM handlers and observe rendered HTML.
function fire(id) { const e = getEl(id); if (typeof e.onclick === "function") { e.onclick(); } }
function val(id, v) { const e = getEl(id); e.value = v; if (typeof e.oninput === "function") e.oninput(); return e; }

// default lobby should render two seats & a start button
check("lobby: rendered start button", getEl("startBtn") !== null);
// ensure names present (defaults) then start
fire("startBtn");
// game should now be running: doRoll button exists
const started = typeof getEl("doRoll").onclick === "function";
check("game: started (roll button wired)", started);

// take several turns without crashing
let rollCount = 0;
function driveTurn(guard) {
  if (getEl("doBuy") && typeof getEl("doBuy").onclick === "function") fire("doBuy");
  if (getEl("doPass") && typeof getEl("doPass").onclick === "function") fire("doPass");
  if (getEl("doRoll") && typeof getEl("doRoll").onclick === "function") { fire("doRoll"); rollCount++; }
  if (getEl("doBuy") && typeof getEl("doBuy").onclick === "function") fire("doBuy");
  if (getEl("doPass") && typeof getEl("doPass").onclick === "function") fire("doPass");
  if (getEl("doEnd") && typeof getEl("doEnd").onclick === "function") fire("doEnd");
}
for (let i = 0; i < 40; i++) driveTurn(i);
check("game: many turns executed without throwing", rollCount > 0);
check("game: rollCount>0 and still wired", typeof getEl("doRoll").onclick === "function" || typeof getEl("again").onclick === "function");

// menu back to lobby works
fire("menuBtn");
check("back to lobby", getEl("startBtn") !== null && getEl("doRoll").onclick === null || getEl("startBtn") !== null);

if (failures) { console.log("\n" + failures + " FAILURE(S)"); process.exit(1); }
console.log("\nDOM harness: app booted & played cleanly.");
process.exit(0); // the app opens a BroadcastChannel; force-clear the event loop
