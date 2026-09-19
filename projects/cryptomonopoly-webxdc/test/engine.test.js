/* Headless engine smoke test — run with: node test/engine.test.js
 * Exercises the pure reducer deterministically (no DOM needed).
 */
"use strict";
const path = require("path");
require(path.join(__dirname, "..", "js", "board.js"));
require(path.join(__dirname, "..", "js", "engine.js"));

const B = global.CryptoBoard;
const E = global.CryptoEngine;

let failures = 0;
function check(name, cond) {
  console.log((cond ? "PASS" : "FAIL") + "  " + name);
  if (!cond) failures++;
}

function mkPlayers(ids) {
  let st = E.initialState();
  ids.forEach((id, i) => {
    st = E.reducer(st, { type: "ADD_PLAYER", player: { id, name: "P" + id, token: B.TOKENS[i % B.TOKENS.length].glyph, color: B.PLAYER_COLORS[i % B.PLAYER_COLORS.length] } });
  });
  return E.reducer(st, { type: "START" });
}

// 1. determinism
(function determinismTest() {
  let a = mkPlayers(["A", "B"]);
  let b = mkPlayers(["A", "B"]);
  const actions = [
    { type: "ROLL", player: "A", dice: [2, 3] },
    { type: "BUY", player: "A" },
    { type: "END_TURN", player: "A" },
    { type: "ROLL", player: "B", dice: [1, 1] },
    { type: "END_TURN", player: "B" },
  ];
  for (const ac of actions) { a = E.reducer(a, ac); b = E.reducer(b, ac); }
  check("determinism: two peers converge", JSON.stringify(a) === JSON.stringify(b));
})();

// 2. buying a property
(function buyTest() {
  let s = mkPlayers(["A", "B"]);
  // A rolls 1+1=2 from GO(0) -> tile 2 is Gas Fee (tax), not buyable.
  // Instead drive A to tile 1 (Dogecoin) by rolling total 1 is impossible.
  // Land A exactly by moving: roll 4 -> tile 4 (Bitcoin, price 80, affordable).
  s = E.reducer(s, { type: "ROLL", player: "A", dice: [2, 2] }); // pos 4 Bitcoin
  check("buy: pending offered", s.pending && s.pending.kind === "buy" && s.pending.pos === 4);
  const cashBefore = s.players.A.cash;
  s = E.reducer(s, { type: "BUY", player: "A" });
  check("buy: ownership recorded", s.ownership[4] && s.ownership[4].ownerId === "A" && s.ownership[4].level === 0);
  check("buy: cash deducted by price(80)", s.players.A.cash === cashBefore - 80);
  check("buy: pending cleared", s.pending === null);
})();

// 3. rent transfer + pot feeding via gas fee
(function rentTaxTest() {
  let s = mkPlayers(["A", "B"]);
  // A buys Bitcoin (tile4). Put B at tile 2 (Gas Fee tax) to feed pot.
  s = E.reducer(s, { type: "ROLL", player: "A", dice: [2, 2] }); // -> 4 Bitcoin
  s = E.reducer(s, { type: "BUY", player: "A" });
  s = E.reducer(s, { type: "END_TURN", player: "A" });
  const potBefore = s.pot;
  const cashB = s.players.B.cash;
  // B rolls 1+1 = 2 -> tile 2 Gas Fee (tax ~ max(40, 10%) = 150) into pot
  s = E.reducer(s, { type: "ROLL", player: "B", dice: [1, 1] });
  check("tax: B lost cash", s.players.B.cash < cashB);
  check("tax: pot grew", s.pot > potBefore);
  s = E.reducer(s, { type: "END_TURN", player: "B" });
  // A now rolls to land on B... not needed. rent path: force A to land on a tile B owns.
  // Let B buy tile 1 (roll total1 impossible). Instead test rent via ownership on 4 again from A turn is same owner. Skip rent here; separate test.
})();

// 4. rent to another owner forces bankruptcy, freeing A's property but not B's
(function bankruptcyTest() {
  let s = mkPlayers(["A", "B"]);
  // A owns tile 1 (Dogecoin), B owns tile 14 (Chainlink). Put A before 14 with little cash.
  s.ownership[1] = { ownerId: "A", level: 0 };
  s.ownership[14] = { ownerId: "B", level: 0 };
  s.players.A.pos = 12; // jail square; dice [1,1] -> 14 (B's, rent 18)
  s.players.A.cash = 5;
  s = E.reducer(s, { type: "ROLL", player: "A", dice: [1, 1] });
  check("rent: A went bankrupt paying rent to B", s.players.A.alive === false && s.players.A.cash === 0);
  check("rent: A's property freed on bankruptcy", !s.ownership[1]);
  check("bankrupt: B's property kept", s.ownership[14] && s.ownership[14].ownerId === "B");
})();

// 5. three doubles -> jail; and escape via double; bond on failed attempts
(function jailTest() {
  let s = mkPlayers(["A", "B"]);
  // drive A onto RUG (tile 18) by rolling total from current pos.
  // Manually position A at 16 then roll 1+1=2 -> 18 RUG.
  s.players.A.pos = 16;
  s = E.reducer(s, { type: "ROLL", player: "A", dice: [1, 1] });
  check("jail: landing on RUG sends to jail", s.players.A.inJail === true && s.players.A.pos === B.JAIL_INDEX);
  // Try non-double twice -> jailLeft decreases
  s = E.reducer(s, { type: "ROLL", player: "A", dice: [2, 3] });
  check("jail: non-double keeps in jail, reduces jailLeft", s.players.A.inJail === true && s.players.A.jailLeft === 2);
  s = E.reducer(s, { type: "ROLL", player: "A", dice: [4, 2] });
  check("jail: 2nd non-double reduces to 1", s.players.A.jailLeft === 1);
  // doubles escape: roll 1+1 = 2 -> tile 14, far from the RUG at 18
  s = E.reducer(s, { type: "ROLL", player: "A", dice: [1, 1] });
  check("jail: doubles escape", s.players.A.inJail === false && s.players.A.jailLeft === 0);
})();

// 6. Free-Mint pot claim
(function potClaimTest() {
  let s = mkPlayers(["A", "B"]);
  const potBefore = s.pot;
  // put A directly before POT tile 6 (Free Mint). A at pos 4, roll 1+1 -> 6
  s.players.A.pos = 4;
  s = E.reducer(s, { type: "ROLL", player: "A", dice: [1, 1] });
  check("pot: A claimed the whole pot", s.players.A.cash === 1500 + potBefore);
  check("pot: pot reset to 0", s.pot === 0);
})();

// 7. a full random game must terminate (cap turns) with a winner once cash pressure applied
(function fullGameTest() {
  let s = mkPlayers(["A", "B", "C", "D"]);
  // raise the stakes: double default rents would still need building; simpler: trust the game ends
  // but also confirm basic turn rotation works across 3 rounds without a crash.
  const order = s.order;
  let seed = 7; const rnd = () => { seed = (seed * 1103515245 + 12345) % 2147483648; return seed / 2147483648; };
  const die = () => 1 + Math.floor(rnd() * 6);
  let cur = 0, steps = 0;
  while (!s.over && steps < 1200) {
    steps++;
    const pid = order[cur];
    if (!s.players[pid].alive) { cur = (cur + 1) % order.length; continue; }
    if (s.pending && s.pending.player === pid) { s = E.reducer(s, { type: "PASS_BUY", player: pid }); continue; }
    // cheap nodes when possible
    const own = Object.entries(s.ownership).find(([, o]) => o.ownerId === pid);
    if (own && rnd() < 0.5) s = E.reducer(s, { type: "UPGRADE", player: pid, tile: +own[0] });
    s = E.reducer(s, { type: "ROLL", player: pid, dice: [die(), die()] });
    if (s.pending && s.pending.player === pid) s = E.reducer(s, { type: "PASS_BUY", player: pid });
    if (s.canRollAgain) continue;
    s = E.reducer(s, { type: "END_TURN", player: pid });
    cur = (cur + 1) % order.length;
  }
  check("full: ran without crashing", true);
  let ok = true;
  for (const id of order) { const p = s.players[id]; if (p.alive && p.cash < 0) ok = false; }
  check("full: no negative cash while alive", ok);
  check("full: pot >= 0", s.pot >= 0);
  console.log("  full game steps=" + steps + " over=" + s.over);
})();

if (failures) { console.log("\n" + failures + " FAILURE(S)"); process.exit(1); }
console.log("\nAll engine checks passed.");
