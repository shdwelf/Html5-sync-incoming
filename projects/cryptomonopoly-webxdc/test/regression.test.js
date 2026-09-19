/* Regression tests for the defects found in the 2026-09 deep review.
 * Run with:  node --test test/*.test.js      (or)   node test/regression.test.js
 *
 * Unlike the original suite these assert the relationship between the DATA a
 * card/tile describes and the STATE CHANGE it actually produces, which is what
 * let two inverted event cards and a tax that could drive cash negative slip
 * through a fully-green run. See REVIEW.md (CRYPTO-1..CRYPTO-4).
 */
"use strict";
const path = require("path");
const JS = path.join(__dirname, "..", "js");

require(path.join(JS, "board.js"));
require(path.join(JS, "engine.js"));

const Board = global.CryptoBoard;
const E = global.CryptoEngine;

let failures = 0;
function check(name, cond, detail) {
  console.log((cond ? "PASS" : "FAIL") + "  " + name + (cond || !detail ? "" : "   [" + detail + "]"));
  if (!cond) failures++;
}

// Two players, game started, A to act.
function table() {
  let s = E.initialState();
  s = E.reducer(s, { type: "ADD_PLAYER", player: { id: "A", name: "Ann", token: "🪙", color: "#f43f5e" } });
  s = E.reducer(s, { type: "ADD_PLAYER", player: { id: "B", name: "Bob", token: "🚀", color: "#22d3ee" } });
  s = E.reducer(s, { type: "START" });
  return s;
}

// Land A on the EVENT tile at index 15 while drawing event card #d.
function drawEvent(d) {
  let s = table();
  s.eventDraws = d;
  s.pending = null;
  s.turn = 0;
  s.players.A.pos = 13;              // 13 + (1+1) = 15 = Halving/EVENT tile
  return E.reducer(s, { type: "ROLL", player: "A", dice: [1, 1] });
}

// ------------------------------------------------------------------
// CRYPTO-1 — event cards did the opposite of what their text said
// ------------------------------------------------------------------
(function eventCardsMatchTheirText() {
  check("event: target tile really is an EVENT tile", Board.tileByIndex(15).type === Board.type.EVENT);
  check("event: deck is non-empty", Board.EVENT_DECK.length > 0);

  for (let d = 0; d < Board.EVENT_DECK.length; d++) {
    const card = Board.EVENT_DECK[d];
    const before = table();
    const after = drawEvent(d);
    const dCash = after.players.A.cash - before.players.A.cash;
    const dPot = after.pot - before.pot;

    if (card.kind !== "cash") { check(`event ${d}: non-cash card left cash alone`, dCash === 0 || card.kind === "move", `dcash=${dCash}`); continue; }

    const saysPay = /\bpay\b/i.test(card.text);
    const saysGain = /\b(collect|receive)\b/i.test(card.text) || /:\s*\+\d+/.test(card.text);

    if (saysPay) {
      check(`event ${d}: text says PAY and cash decreased`, dCash < 0, `"${card.text}" dcash=${dCash}`);
      if (card.toPot) check(`event ${d}: paid money went INTO the pot`, dPot > 0, `"${card.text}" dpot=${dPot}`);
    }
    if (saysGain) {
      check(`event ${d}: text says COLLECT/RECEIVE and cash increased`, dCash > 0, `"${card.text}" dcash=${dCash}`);
    }
    check(`event ${d}: pot never went negative`, after.pot >= 0, `pot=${after.pot}`);
  }
})();

(function collectFromPotIsCappedAtPot() {
  // "Collect 200 from the network pot" must not mint money the pot does not have.
  let s = table();
  s.eventDraws = 0;                 // Bull run — collect 200 fromPot
  s.pot = 30;                       // only 30 available
  s.pending = null; s.turn = 0; s.players.A.pos = 13;
  const r = E.reducer(s, { type: "ROLL", player: "A", dice: [1, 1] });
  check("event: fromPot payout is capped at the pot balance", r.players.A.cash === 1500 + 30, `cash=${r.players.A.cash}`);
  check("event: fromPot drains the pot exactly", r.pot === 0, `pot=${r.pot}`);
})();

// ------------------------------------------------------------------
// CRYPTO-2 — Gas Fee could push cash below zero with no bankruptcy
// ------------------------------------------------------------------
(function taxNeverGoesNegative() {
  const gasIdx = Board.TILES.findIndex((t) => t.type === Board.type.TAX);
  check("tax: board has a TAX tile", gasIdx >= 0);

  for (const startCash of [0, 5, 10, 39, 40, 41, 500, 1500]) {
    let s = table();
    s.players.A.cash = startCash;
    s.pending = null; s.turn = 0;
    // place A so that a 1+1 roll lands exactly on the TAX tile
    s.players.A.pos = (gasIdx - 2 + Board.BOARD_SIZE) % Board.BOARD_SIZE;
    const r = E.reducer(s, { type: "ROLL", player: "A", dice: [1, 1] });
    const a = r.players.A;
    check(`tax: cash ${startCash} -> never negative`, a.cash >= 0, `cash=${a.cash}`);
    check(`tax: cash ${startCash} -> wiped out means bankrupt`, a.cash > 0 || a.alive === false, `cash=${a.cash} alive=${a.alive}`);
    check(`tax: cash ${startCash} -> pot never negative`, r.pot >= 0, `pot=${r.pot}`);
  }
})();

(function taxRateAndFloorComeFromBoard() {
  check("tax: rate/floor are board data, not magic numbers in the reducer",
    typeof Board.TAX_RATE === "number" && typeof Board.TAX_FLOOR === "number",
    `rate=${Board.TAX_RATE} floor=${Board.TAX_FLOOR}`);
})();

// ------------------------------------------------------------------
// CRYPTO-3 — exchange rent table carried an unreachable 4th tier
// ------------------------------------------------------------------
(function exchRentTableMatchesBoard() {
  const exchTiles = Board.TILES.filter((t) => t.type === Board.type.EXCH);
  // Guarded so a missing table reports as a failure instead of throwing and
  // aborting the rest of the run.
  const tiers = Array.isArray(Board.EXCH_RENT) ? Board.EXCH_RENT : null;
  check("exch: rent table is exported as board data", tiers !== null, "Board.EXCH_RENT is not an array");
  if (tiers) {
    check("exch: rent table has exactly one tier per EXCH tile",
      tiers.length === exchTiles.length, `tiers=${tiers.length} tiles=${exchTiles.length}`);
    check("exch: rent tiers are strictly increasing",
      tiers.every((v, i) => i === 0 || v > tiers[i - 1]), JSON.stringify(tiers));
  }
})();

// ------------------------------------------------------------------
// CRYPTO-4 — remote peers supply player identity, so validate it
// ------------------------------------------------------------------
(function addPlayerRejectsPrototypeKeys() {
  for (const bad of ["__proto__", "constructor", "prototype"]) {
    const s = E.reducer(E.initialState(), { type: "ADD_PLAYER", player: { id: bad, name: "x", token: "🪙", color: "#fff" } });
    check(`ADD_PLAYER: rejects id ${JSON.stringify(bad)}`, s.order.length === 0 && Object.keys(s.players).length === 0,
      `order=${JSON.stringify(s.order)}`);
    check(`ADD_PLAYER: id ${JSON.stringify(bad)} did not pollute Object.prototype`, ({}).alive === undefined);
  }
})();

(function addPlayerSanitisesRemoteFields() {
  const hostileColor = 'red" onload="alert(1)';
  const hostileToken = '<img src=x onerror=alert(1)>';
  const s = E.reducer(E.initialState(), {
    type: "ADD_PLAYER",
    player: { id: "evil", name: "a".repeat(500), token: hostileToken, color: hostileColor },
  });
  const p = s.players.evil;
  check("ADD_PLAYER: hostile colour is replaced, not passed through", p.color !== hostileColor && /^[#a-zA-Z]/.test(p.color), `color=${p.color}`);
  check("ADD_PLAYER: hostile colour contains no quote/angle bracket", !/["'<>]/.test(p.color), `color=${p.color}`);
  check("ADD_PLAYER: markup is stripped from the token", !/[<>]/.test(p.token), `token=${p.token}`);
  check("ADD_PLAYER: name is clipped to 18 chars", p.name.length <= 18, `len=${p.name.length}`);
})();

(function tileByIndexHandlesNegatives() {
  check("tileByIndex(-1) wraps to the last tile instead of undefined",
    Board.tileByIndex(-1) === Board.TILES[Board.BOARD_SIZE - 1]);
  check("tileByIndex(BOARD_SIZE) wraps to GO", Board.tileByIndex(Board.BOARD_SIZE).type === Board.type.GO);
})();

// ------------------------------------------------------------------
// CRYPTO-5 — transport applied our own webxdc echo a second time
// ------------------------------------------------------------------
(function transportDedupesSelfEcho() {
  // Build a fake messenger that behaves per spec: sendUpdate() is echoed back
  // through the setUpdateListener callback.
  delete require.cache[path.join(JS, "transport.js")];
  const delivered = [];
  let listener = null;
  let listenerRegistrations = 0;
  global.window = {
    webxdc: {
      selfAddr: "me@example.org",
      selfName: "Me",
      sendUpdate(payload, info) { delivered.push(payload.payload); },
      setUpdateListener(cb, serial) { listenerRegistrations++; listener = cb; return Promise.resolve(); },
      getAllUpdates() { return Promise.resolve([]); },
    },
    localStorage: undefined,
  };
  require(path.join(JS, "transport.js"));
  // transport.js binds its exports to `window` when one exists, so read them
  // back from the same object the module chose -- not from Node's globalThis.
  const T = global.window.CryptoTransport;
  check("transport: exports landed on the host global", !!T);
  check("transport: detects the webxdc host", T.detectWebxdc() === true);

  const t = T.createTransport();
  const applied = [];
  t.onAction((a) => applied.push(a));
  t.onAction(() => {});   // a second subscriber must not re-register the listener
  check("transport: setUpdateListener registered exactly once", listenerRegistrations === 1, `n=${listenerRegistrations}`);

  // Flush the echo, as a real messenger would.
  let serial = 0;
  for (const payload of delivered.splice(0)) {
    listener({ payload, serial: ++serial, max_serial: serial });
  }

  t.broadcast({ type: "ROLL", player: "me@example.org", seq: 1, dice: [3, 4] });
  check("transport: action applied optimistically on send", applied.length === 1, `n=${applied.length}`);
  for (const payload of delivered.splice(0)) {
    listener({ payload, serial: ++serial, max_serial: serial });
  }
  check("transport: our own echo was NOT applied a second time", applied.length === 1, `n=${applied.length}`);

  // A peer's action must still come through.
  listener({ payload: { type: "ROLL", player: "peer@example.org", seq: 1, dice: [2, 2] }, serial: ++serial, max_serial: serial });
  check("transport: a peer action is applied", applied.length === 2 && applied[1].player === "peer@example.org", `n=${applied.length}`);

  // And it must be applied for BOTH subscribers.
  check("transport: every subscriber saw the peer action", applied.length === 2);

  delete global.window;
})();

(function localTransportPropagatesReset() {
  delete require.cache[path.join(JS, "transport.js")];
  // Minimal BroadcastChannel double that loops messages back to other instances.
  const channels = [];
  global.BroadcastChannel = class {
    constructor(name) { this.name = name; this.onmessage = null; channels.push(this); }
    postMessage(data) { for (const c of channels) if (c !== this && c.onmessage) c.onmessage({ data }); }
  };
  delete global.window;
  require(path.join(JS, "transport.js"));
  const T = global.CryptoTransport;
  check("transport: falls back to local mode without a host", T.createTransport().mode === "local");

  const a = T.createTransport();   // tab 1
  const b = T.createTransport();   // tab 2
  const seenB = [];
  b.onAction((x) => seenB.push(x));

  a.resetLocal();
  check("transport: resetLocal() reaches the mirror tab as a RESET action",
    seenB.length === 1 && seenB[0].type === "RESET", JSON.stringify(seenB));

  // A RESET through the reducer really does return to the lobby.
  const finished = (() => { let s = table(); s.over = true; return s; })();
  check("transport: RESET returns a finished game to the lobby",
    E.reducer(finished, { type: "RESET" }).phase === "lobby");

  // The originating tab must not re-apply its own cross-tab echo.
  const seenA = [];
  a.onAction((x) => seenA.push(x));
  a.broadcast({ type: "ROLL", player: "A", seq: 7, dice: [1, 2] });
  check("transport: local broadcast applied once in the origin tab", seenA.length === 1, `n=${seenA.length}`);

  delete global.BroadcastChannel;
})();

if (failures) { console.log("\n" + failures + " FAILURE(S)"); process.exit(1); }
console.log("\nAll regression checks passed.");
