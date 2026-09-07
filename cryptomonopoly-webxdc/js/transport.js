/* Cryptomonopoly — transport layer.
 * A tiny adapter so the SAME game code runs in two ways:
 *   1. WebXDC peer-to-peer  — real Delta Chat (window.webxdc present):
 *        each device is one player; actions are broadcast and every peer runs
 *        the deterministic reducer so states stay in sync.
 *   2. Local "hot-seat"     — a plain browser tab (no webxdc): one screen, many
 *        human seats in a row. Actions run through the reducer in-process.
 * The reducer never changes — only who generates/forwards the actions.
 */
(function (global) {
  "use strict";

  const Engine = global.CryptoEngine;

  function detectWebxdc() {
    return typeof window !== "undefined" && !!window.webxdc && typeof window.webxdc.sendUpdate === "function";
  }

  // Local hot-seat adapter: in-process dispatch, optional cross-tab echo via
  // BroadcastChannel so two tabs can watch (still fully usable in one tab).
  function createLocalAdapter() {
    const listeners = [];
    const bc = typeof BroadcastChannel !== "undefined" ? new BroadcastChannel("cryptomonopoly-local") : null;
    if (bc) bc.onmessage = (e) => { if (e.data && e.data.kind === "action") fire(e.data.action); };
    return {
      mode: "local",
      selfId: "local",
      selfName: "Device",
      broadcast(action) {
        fire(action);
        if (bc) bc.postMessage({ kind: "action", action });
      },
      onAction(cb) { listeners.push(cb); },
      resetLocal() {
        // notify other local tabs to reset too
        if (bc) bc.postMessage({ kind: "reset" });
      },
      _reset() {},
    };
    function fire(action) { for (const cb of listeners) cb(action); }
  }

  // Real WebXDC adapter: this device is one player in a Delta Chat group.
  function createWebxdcAdapter() {
    const listeners = [];
    let lastSerial = 0;
    const xdc = window.webxdc;
    return {
      mode: "webxdc",
      selfId: xdc.selfAddr || ("p" + Math.random().toString(36).slice(2, 7)),
      selfName: xdc.selfName || "Player",
      broadcast(action) {
        // feed our own copy immediately AND broadcast
        fire(action);
        try { xdc.sendUpdate({ payload: action }, action.type + " #" + (action.seq || "")); } catch (e) { /* ignore */ }
      },
      onAction(cb) {
        listeners.push(cb);
        // Replay any history we may have missed (new joiners).
        if (typeof xdc.setUpdateListener === "function") {
          xdc.setUpdateListener((update) => {
            if (update && update.payload && typeof update.serial === "number") {
              lastSerial = Math.max(lastSerial, update.serial);
              for (const cb of listeners) cb(update.payload);
            }
          });
        }
      },
      resetLocal() {},
    };
    function fire(action) { for (const cb of listeners) cb(action); }
  }

  function createTransport() {
    return detectWebxdc() ? createWebxdcAdapter() : createLocalAdapter();
  }

  global.CryptoTransport = { createTransport, detectWebxdc };
})(typeof window !== "undefined" ? window : globalThis);
