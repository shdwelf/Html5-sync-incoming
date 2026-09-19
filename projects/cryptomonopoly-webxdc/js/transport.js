/* Cryptomonopoly — transport layer.
 * A tiny adapter so the SAME game code runs in two ways:
 *   1. WebXDC peer-to-peer  — real Delta Chat (window.webxdc present):
 *        each device is one player; actions are broadcast and every peer runs
 *        the deterministic reducer so states stay in sync.
 *   2. Local "hot-seat"     — a plain browser tab (no webxdc): one screen, many
 *        human seats in a row. Actions run through the reducer in-process.
 * The reducer never changes — only who generates/forwards the action.
 *
 * Two webxdc facts drive the design of the adapter below:
 *   • The spec says setUpdateListener's callback "is called for updates sent by
 *     you or other peers", i.e. our own sendUpdate() is echoed back to us. If we
 *     also applied the action optimistically at send time, every local action
 *     would be reduced TWICE (double-spent cash, double movement). So we apply
 *     optimistically and then DEDUPE our own echo by (player, seq).
 *   • The same spec notes the echo is not guaranteed in every state (e.g. after
 *     leaving a group), so optimistic-apply + dedupe is correct in both cases,
 *     whereas "wait for the echo" would silently freeze the UI.
 *   • Calling setUpdateListener() more than once is undefined behaviour ("only
 *     the last invocation works"), so we register exactly one listener for the
 *     lifetime of the adapter, no matter how many onAction() subscribers exist.
 */
(function (global) {
  "use strict";

  const Engine = global.CryptoEngine;

  function detectWebxdc() {
    return typeof window !== "undefined" && !!window.webxdc && typeof window.webxdc.sendUpdate === "function";
  }

  // Stable identity for a device that has no webxdc selfAddr (dev shims, plain
  // browser). Persisted so a reload does not orphan the seat it already joined.
  function stableLocalId() {
    const KEY = "cryptomonopoly.deviceId";
    try {
      let id = global.localStorage && global.localStorage.getItem(KEY);
      if (!id) {
        id = "dev-" + Math.random().toString(36).slice(2, 10);
        global.localStorage.setItem(KEY, id);
      }
      return id;
    } catch (e) {
      return "local"; // storage blocked (sandboxed iframe) — single-tab play
    }
  }

  // An action is uniquely identified by the device that produced it plus that
  // device's own monotonically increasing sequence number.
  function actionKey(action) {
    return (action && (action.player || action.from || "?")) + "#" + (action && action.seq != null ? action.seq : "?");
  }

  // ------------------------------------------------------------------
  // Local hot-seat adapter: in-process dispatch, with a BroadcastChannel
  // mirror so a second tab can watch (and reset) the same game.
  // ------------------------------------------------------------------
  function createLocalAdapter() {
    const listeners = [];
    const bc = typeof BroadcastChannel !== "undefined" ? new BroadcastChannel("cryptomonopoly-local") : null;
    const seen = new Set();

    function fire(action) {
      // Cross-tab echo: a tab must not re-apply an action it originated.
      const k = actionKey(action);
      if (k !== "?#?") {
        if (seen.has(k)) return;
        seen.add(k);
        if (seen.size > 4096) seen.clear();
      }
      for (const cb of listeners) cb(action);
    }

    if (bc) {
      bc.onmessage = (e) => {
        const d = e.data;
        if (!d) return;
        if (d.kind === "action") fire(d.action);
        // A reset from another tab is delivered as a normal RESET action so it
        // runs through the reducer exactly like a local reset would.
        else if (d.kind === "reset") fire({ type: "RESET" });
      };
    }

    return {
      mode: "local",
      selfId: stableLocalId(),
      selfName: "Device",
      broadcast(action) {
        fire(action);
        if (bc) bc.postMessage({ kind: "action", action });
      },
      onAction(cb) { listeners.push(cb); },
      resetLocal() {
        if (bc) bc.postMessage({ kind: "reset" });
      },
    };
  }

  // ------------------------------------------------------------------
  // Real WebXDC adapter: this device is one player in a Delta Chat group.
  // ------------------------------------------------------------------
  function createWebxdcAdapter() {
    const listeners = [];
    const xdc = window.webxdc;
    const sent = new Set();   // keys of actions WE produced (already applied)
    let registered = false;
    let lastSerial = 0;

    function fire(action) { for (const cb of listeners) cb(action); }

    function markSent(action) {
      const k = actionKey(action);
      sent.add(k);
      if (sent.size > 4096) sent.clear(); // bounded; a game never gets near this
    }

    // Register once. serial 0 => the host replays full history first, which is
    // exactly what a device that joins an already-running game needs.
    function register() {
      if (registered || typeof xdc.setUpdateListener !== "function") return;
      registered = true;
      xdc.setUpdateListener((update) => {
        if (!update || !update.payload) return;
        if (typeof update.serial === "number") lastSerial = Math.max(lastSerial, update.serial);
        if (sent.has(actionKey(update.payload))) return; // our own echo
        fire(update.payload);
      }, 0);
    }

    return {
      mode: "webxdc",
      selfId: xdc.selfAddr || stableLocalId(),
      selfName: xdc.selfName || "Player",
      broadcast(action) {
        markSent(action);
        fire(action); // optimistic local apply
        try { xdc.sendUpdate({ payload: action }, action.type + " #" + (action.seq || "")); } catch (e) { /* ignore */ }
      },
      onAction(cb) {
        listeners.push(cb);
        register(); // idempotent — the spec allows only one listener
      },
      // A shared game cannot be unilaterally reset from one device: RESET is a
      // normal action that has to be agreed by the table, so this stays a no-op.
      resetLocal() {},
      get serial() { return lastSerial; },
    };
  }

  function createTransport() {
    return detectWebxdc() ? createWebxdcAdapter() : createLocalAdapter();
  }

  global.CryptoTransport = { createTransport, detectWebxdc, actionKey };
})(typeof window !== "undefined" ? window : globalThis);
