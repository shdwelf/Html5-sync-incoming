/* Cryptomonopoly — UI controller.
 * Owns the DOM, feeds actions into the deterministic reducer, and re-renders.
 * Two play modes share this one controller:
 *   • local  (hot-seat) — one screen, the operator plays every seat in turn.
 *   • webxdc (sync)     — each device is one player in a Delta Chat group;
 *                         actions are broadcast and every peer runs the same
 *                         reducer, so everyone stays in sync.
 */
(function (global) {
  "use strict";
  const B = global.CryptoBoard;
  const Engine = global.CryptoEngine;
  const Transport = global.CryptoTransport;

  let state = Engine.initialState();
  let transport = null;
  let seq = 0;
  let selfId = "local";      // device identity (webxdc selfAddr)
  let webxdcMode = false;

  // lobby seat editor (local mode only)
  let lobbySeats = [];

  const $ = (id) => document.getElementById(id);

  // ---------------- boot ----------------
  function boot() {
    transport = Transport.createTransport();
    webxdcMode = transport.mode === "webxdc";
    selfId = webxdcMode ? transport.selfId : "local";
    transport.onAction((action) => apply(action));
    render();
  }

  function apply(action) {
    state = Engine.reducer(state, action);
    render();
  }

  function send(action) {
    action.seq = ++seq;
    transport.broadcast(action);
  }

  function myId() {
    return webxdcMode ? selfId : (Engine.currentPlayer(state) || {}).id || "local";
  }

  // my device controls the current player's hand only in webxdc mode;
  // in local hot-seat the operator controls whoever's turn it is.
  function canOperate() {
    if (state.over) return false;
    if (state.phase === "lobby") return true;
    const cur = Engine.currentPlayer(state);
    if (!cur) return false;
    if (webxdcMode) return cur.id === selfId;
    return true;
  }
  function isMyTurn() {
    const cur = Engine.currentPlayer(state);
    if (state.phase !== "play" || !cur) return false;
    if (webxdcMode) return cur.id === selfId;
    return true;
  }
  function iAmInLobby() {
    return state.phase === "lobby" && (!webxdcMode || !!state.players[selfId]);
  }

  // ---------------- render dispatcher ----------------
  function render() {
    if (state.phase === "lobby") renderLobby();
    else if (state.over) renderOver();
    else renderGame();
  }

  // ==================================================================
  // LOBBY
  // ==================================================================
  function renderLobby() {
    const root = $("root");
    const joined = state.order.map((id) => state.players[id]);
    const mySeat = state.players[selfId];

    let playersPanel = "";
    if (webxdcMode) {
      playersPanel = `
        <div class="card block">
          <h2>This device</h2>
          <div class="row">
            <input id="myName" class="seat-name" maxlength="18" placeholder="Your name" value="${escAttr(transport.selfName || "")}">
            <button class="ghost" id="pickToken">🎲 piece</button>
          </div>
          <div class="tokens" id="xdcTokens"></div>
        </div>
        <div class="card block">
          <h2>At the table (${joined.length})</h2>
          <div class="joins">${joined.length ? joined.map((p) => joinChip(p, p.id === selfId)).join("") : '<div class="hint">Waiting for others to open the app…</div>'}</div>
        </div>`;
    } else {
      playersPanel = `
        <div class="card block">
          <h2>Seats <button class="ghost small" id="addSeat">+ seat</button></h2>
          <div id="seats" class="seats"></div>
        </div>
        <div class="card block">
          <h2>Pick a piece</h2>
          <div id="tokenPicker" class="tokens"></div>
        </div>`;
    }

    root.innerHTML = `
      <div class="shell lobby">
        <div class="logo">
          <div class="logo-coin">🪙</div>
          <div>
            <h1>Cryptomonopoly</h1>
            <p class="sub">A crypto-flavoured original trading-board game — WebXDC + browser.</p>
          </div>
        </div>

        <div class="mode-row">
          <span class="pill ${webxdcMode ? "pill-xdc" : "pill-local"}">
            ${webxdcMode ? "📡 WebXDC · Delta Chat table" : "💻 Local hot-seat"}
          </span>
          <button class="ghost" id="newGame">↺ New game</button>
        </div>

        <div class="two-col">${playersPanel}</div>

        <details class="rules card">
          <summary><b>How to play</b></summary>
          <ul>
            <li>Roll two dice and move. Pass GO to collect <b>200</b>.</li>
            <li>Land on an unowned <b>coin / exchange</b> to buy it; others pay you rent.</li>
            <li>Own several <b>exchanges</b> to raise their fee (25→50→100→200).</li>
            <li>On your turn, stake a <b>node</b> on a coin you own (raises rent, max lvl 4).</li>
            <li><b>Gas fees &amp; bonds</b> feed the <b>Free-Mint pot</b> — land on it to claim it all.</li>
            <li>Doubles = roll again; <b>3 doubles</b> or a <b>Rug Pull</b> sends you to jail.</li>
            <li>Bankrupt and you're out. Last chain standing wins.</li>
          </ul>
        </details>

        <button class="primary big" id="startBtn" disabled>${webxdcMode ? "Join &amp; start" : "Start game"}</button>
        ${mySeat ? `<p class="you-chip">You are <b>${escAttr(mySeat.name)}</b> ${mySeat.token}</p>` : ""}
        <p class="legal">Original game inspired by classic trading-board themes. No copyrighted game assets are reproduced.</p>
      </div>
    `;

    $("newGame").onclick = resetAll;
    const sb = $("startBtn");

    if (webxdcMode) {
      const tokensHost = $("xdcTokens");
      tokensHost.innerHTML = B.TOKENS.map((t) =>
        `<button class="token" data-tok="${t.glyph}" title="${escAttr(t.label)}">${t.glyph}</button>`).join("");
      let tok = B.TOKENS[0].glyph;
      tokensHost.querySelectorAll(".token").forEach((b) => b.onclick = () => {
        tok = b.dataset.tok;
        tokensHost.querySelectorAll(".token").forEach((x) => x.classList.toggle("sel", x === b));
      });
      const nameInput = $("myName");
      const refreshBtn = () => {
        const haveMe = joined.some((p) => p.id === selfId);
        const ready = nameInput.value.trim() && (haveMe || joined.length < 6);
        sb.disabled = !ready;
        sb.textContent = haveMe
          ? (joined.length >= 2 ? "Start game" : "Waiting for opponents…")
          : "Join the table";
        sb.disabled = haveMe ? joined.length < 2 : !nameInput.value.trim();
      };
      nameInput.oninput = refreshBtn;
      refreshBtn();
      sb.onclick = () => {
        if (!state.players[selfId]) {
          // pick a colour that's free
          const used = joined.map((p) => p.color);
          const color = B.PLAYER_COLORS.find((c) => !used.includes(c)) || B.PLAYER_COLORS[joined.length % B.PLAYER_COLORS.length];
          send({ type: "ADD_PLAYER", player: { id: selfId, name: nameInput.value.trim(), token: tok, color } });
        } else if (joined.length >= 2) {
          send({ type: "START" });
        }
      };
    } else {
      if (lobbySeats.length === 0) lobbySeats = defaultSeats(2);
      bindLocalLobby();
      refreshStart();
      sb.onclick = startLocal;
    }
  }

  function bindLocalLobby() {
    $("addSeat").onclick = () => { if (lobbySeats.length < 6) { lobbySeats.push(freshSeat(lobbySeats.length)); bindLocalLobby(); refreshStart(); } };
    renderLocalSeats();
  }

  function renderLocalSeats() {
    const host = $("seats");
    const tokensHost = $("tokenPicker");
    host.innerHTML = lobbySeats.map((s, i) => `
      <div class="seat">
        <span class="seat-token">${s.token}</span>
        <input data-idx="${i}" class="seat-name" value="${escAttr(s.name)}" maxlength="18">
        <button data-idx="${i}" class="remove" title="remove">✕</button>
      </div>`).join("");
    tokensHost.innerHTML = B.TOKENS.map((t) =>
      `<button class="token" data-tok="${t.glyph}" title="${escAttr(t.label)}">${t.glyph}</button>`).join("");

    let activeSeat = 0;
    function showActiveTokens() {
      tokensHost.querySelectorAll(".token").forEach((x) =>
        x.classList.toggle("sel", x.dataset.tok === lobbySeats[activeSeat].token));
    }
    function activePicker(idx) {
      activeSeat = idx;
      tokensHost.querySelectorAll(".token").forEach((x) => {
        x.dataset.idx = idx;
        x.onclick = () => { lobbySeats[idx].token = x.dataset.tok; renderLocalSeats(); };
      });
      showActiveTokens();
    }
    host.querySelectorAll("input").forEach((inp) => {
      inp.oninput = () => { lobbySeats[+inp.dataset.idx].name = inp.value; refreshStart(); };
      inp.onclick = () => activePicker(+inp.dataset.idx);
    });
    host.querySelectorAll(".remove").forEach((btn) => {
      btn.onclick = () => {
        if (lobbySeats.length <= 2) return;
        lobbySeats.splice(+btn.dataset.idx, 1);
        bindLocalLobby();
        refreshStart();
      };
    });
    activePicker(0);
    showActiveTokens();
  }

  function refreshStart() {
    const b = $("startBtn");
    if (b) b.disabled = lobbySeats.length < 2 || lobbySeats.some((s) => !s.name.trim());
  }

  function startLocal() {
    state = Engine.initialState();
    seq = 0;
    lobbySeats.forEach((s, i) => send({ type: "ADD_PLAYER", player: {
      id: "P" + i, name: s.name.trim(), token: s.token,
      color: B.PLAYER_COLORS[i % B.PLAYER_COLORS.length],
    }}));
    // don't START here; render() shows game when phase transitions. ADD_PLAYER
    // keeps phase lobby, so we need a START to lock.
    if (lobbySeats.length >= 2) send({ type: "START" });
  }

  function freshSeat(i) {
    return { name: "Player " + (i + 1), token: B.TOKENS[i % B.TOKENS.length].glyph };
  }
  function defaultSeats(n) {
    const arr = [];
    for (let i = 0; i < n; i++) arr.push(freshSeat(i));
    return arr;
  }

  function joinChip(p, me) {
    return `<div class="join" style="--pc:${p.color}">
      <span class="join-tok">${p.token}</span><span>${escAttr(p.name)}</span>${me ? " <em>(you)</em>" : ""}
    </div>`;
  }

  // ==================================================================
  // GAME
  // ==================================================================
  function renderGame() {
    const root = $("root");
    const cur = Engine.currentPlayer(state);
    const operate = canOperate();

    const header = `
      <div class="topbar">
        <div class="brand">🪙 Cryptomonopoly</div>
        <div class="mode">${webxdcMode ? "📡 sync" : "💻 hot-seat"}</div>
        <button class="ghost" id="menuBtn">☰</button>
      </div>
      <div class="player-strip">${playersStrip()}</div>
    `;

    const board = boardHtml();
    const center = centerHtml(cur, operate);

    root.innerHTML = `${header}<div class="game">${board}${center}</div><div id="toast" class="toast"></div>`;
    wireCenter(cur, operate);
    $("menuBtn").onclick = () => { if (confirm("Return to lobby?")) resetAll(); };
    if (state.pending) showToast(cur.name + ": buy or pass on " + B.tileByIndex(state.pending.pos).name);
  }

  function playersStrip() {
    return state.order.map((id, i) => {
      const p = state.players[id];
      return `<div class="pbadge ${state.turn === i ? "active" : ""} ${p.alive ? "" : "dead"}" style="--pc:${p.color}">
        <span class="pb-tok">${p.token}</span>
        <span class="pb-name">${escAttr(p.name)}</span>
        <span class="pb-cash">🪙 ${p.cash}</span>
      </div>`;
    }).join("");
  }

  function boardHtml() {
    let cells = "";
    for (let r = 0; r < 7; r++) for (let c = 0; c < 7; c++) {
      const idx = B.POSITIONS.findIndex(([rr, cc]) => rr === r && cc === c);
      if (idx < 0) continue;
      cells += tileHtml(idx, r, c);
    }
    return `<div class="board-grid">${cells}<div class="board-center"></div></div>`;
  }

  function tileHtml(idx, r, c) {
    const t = B.tileByIndex(idx);
    const own = state.ownership[idx];
    const owner = own ? state.players[own.ownerId] : null;
    const markers = state.order.filter((id) => {
      const p = state.players[id];
      return p.alive && p.pos === idx && !(p.inJail && idx !== B.JAIL_INDEX);
    }).map((id) => `<span class="marker" style="--mc:${state.players[id].color}">${state.players[id].token}</span>`).join("");

    const ownable = t.type === B.type.PROP || t.type === B.type.EXCH;
    let body;
    if (ownable) {
      const lvl = own ? own.level : 0;
      const dots = own ? "●".repeat(lvl) + "○".repeat(4 - lvl) : "";
      body = `<div class="tt-sym">${t.sym}</div><div class="tt-name">${t.name}</div><div class="tt-lvl">${dots}</div>`;
      if (owner) body += `<div class="tt-owner" style="background:${owner.color}">${owner.token}</div>`;
    } else {
      body = `<div class="tt-sym big">${t.sym}</div><div class="tt-name">${t.name}</div>`;
    }
    const colorTop = ownable && t.color ? ` style="--ct:${t.color}"` : "";
    return `<div class="tile ${ownable ? "ownable" : ""} ${owner ? "owned" : ""}" data-idx="${idx}" style="grid-row:${r + 1};grid-column:${c + 1}" ${colorTop}>
      ${body}<div class="markers">${markers}</div></div>`;
  }

  function centerHtml(cur, operate) {
    if (!cur) return `<div class="side"><div class="panel"><div class="hint">Waiting for players…</div></div></div>`;

    const d = state.lastDice;
    const diceHtml = d
      ? `<div class="dice"><span class="die">${dieFace(d[0])}</span><span class="die">${dieFace(d[1])}</span></div>`
      : `<div class="dice idle">🎲</div>`;

    const pend = state.pending && state.pending.player === cur.id ? state.pending : null;
    let actions = "";
    const turnLabel = webxdcMode ? (cur.id === selfId ? "Your turn" : "Waiting for " + cur.name) : cur.name + "’s turn";

    if (operate) {
      if (pend) {
        const t = B.tileByIndex(pend.pos);
        actions = `<div class="card prompt">
            <b>${escAttr(cur.name)}</b>: buy <b>${t.name}</b>?
            <div class="btn-row">
              <button class="primary" id="doBuy">Buy · ${t.price} 🪙</button>
              <button class="ghost" id="doPass">Pass</button>
            </div></div>`;
      } else {
        actions = `
          <button class="primary big" id="doRoll">${state.canRollAgain ? "🎲 Roll again (doubles!)" : "🎲 Roll dice"}</button>
          <div class="btn-row"><button class="ghost" id="doEnd">End turn</button></div>`;
      }
    } else {
      actions = `<div class="card waiting"><div class="turnlabel">${turnLabel}</div><div class="spinner"></div></div>`;
    }

    const upgrade = upgradePanel(cur);
    return `<div class="side">
      <div class="panel who">
        <span class="who-tok" style="--mc:${cur.color}">${cur.token}</span>
        <div>
          <div class="who-name">${escAttr(cur.name)}${cur.inJail ? " ⛓" : ""}</div>
          <div class="who-cash">🪙 ${cur.cash} <span class="dim">· Pot:</span> <b>🫙 ${state.pot}</b></div>
        </div>
      </div>
      <div class="panel dicepanel"><div class="turnlabel">${state.canRollAgain ? "DOUBLES — roll again" : turnLabel}</div>${diceHtml}</div>
      <div class="panel actions">${actions}</div>
      ${upgrade}
      <div class="panel logcard"><div class="log">${logHtml()}</div></div>
    </div>`;
  }

  function upgradePanel(cur) {
    const mine = Object.entries(state.ownership).filter(([, o]) => o.ownerId === cur.id);
    if (!mine.length) return "";
    let opts = "";
    for (const [k, o] of mine) {
      const tile = B.tileByIndex(+k);
      if (tile.type !== B.type.PROP || o.level >= 4) continue;
      opts += `<button class="up-item" data-tile="${k}">${tile.name} · lvl ${o.level}→${o.level + 1} · ${tile.up}🪙</button>`;
    }
    if (!opts) return "";
    return `<div class="panel"><h3>🏗 Stake a node</h3><div class="up-list">${opts}</div></div>`;
  }

  function logHtml() {
    return state.log.map((m) => `<div class="log-line">${esc(m)}</div>`).join("");
  }

  function dieFace(n) { return ["", "⚀", "⚁", "⚂", "⚃", "⚄", "⚅"][n] || n; }

  function renderOver() {
    const w = state.winner ? state.players[state.winner] : null;
    $("root").innerHTML = `<div class="overlay card">
      <div class="logo-coin big">🏆</div>
      <h1>${w ? esc(w.name) + " rules the chain!" : "Game over"}</h1>
      <p class="sub">${w ? w.token + " " + esc(w.name) + " was the last chain standing." : ""}</p>
      <button class="primary big" id="again">Play again</button>
    </div>`;
    $("again").onclick = resetAll;
  }

  // ---------------- wiring ----------------
  function wireCenter(cur, operate) {
    if (!operate || !cur) return;
    const roll = $("doRoll");
    if (roll) roll.onclick = () => sendDice(cur.id);
    const end = $("doEnd");
    if (end) end.onclick = () => send({ type: "END_TURN", player: cur.id });
    const buy = $("doBuy");
    if (buy) buy.onclick = () => send({ type: "BUY", player: cur.id });
    const pass = $("doPass");
    if (pass) pass.onclick = () => send({ type: "PASS_BUY", player: cur.id });
    const ups = document.querySelectorAll(".up-item");
    ups.forEach((b) => b.onclick = () => send({ type: "UPGRADE", player: cur.id, tile: +b.dataset.tile }));
  }

  function sendDice(playerId) {
    send({ type: "ROLL", player: playerId, dice: [1 + Math.floor(Math.random() * 6), 1 + Math.floor(Math.random() * 6)] });
  }

  // ---------------- misc ----------------
  function showToast(msg) {
    const t = $("toast");
    if (!t) return;
    t.textContent = msg; t.classList.add("show");
    clearTimeout(t._t); t._t = setTimeout(() => t.classList.remove("show"), 2400);
  }

  function resetAll() {
    seq = 0;
    state = Engine.initialState();
    render();
  }

  function esc(s) {
    return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }
  function escAttr(s) { return esc(s); }

  document.addEventListener("DOMContentLoaded", boot);
})(typeof window !== "undefined" ? window : globalThis);
