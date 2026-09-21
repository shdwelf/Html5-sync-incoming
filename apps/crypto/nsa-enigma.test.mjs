/*
 * node:test harness for apps/crypto/nsa-enigma.html
 *
 * Extracts the `<script id="enigma-core">` block from the single-file app and
 * runs its built-in SELF_TESTS suite in a fresh VM sandbox — the exact same
 * assertions the app's Self-test tab runs in-browser, so the committed HTML
 * and the CI gate can never drift apart.
 *
 *   node --test apps/crypto/nsa-enigma.test.mjs
 *
 * Provenance: core is a JS conversion of NationalSecurityAgency/
 * enigma-simulator@f234ee6 (MIT + US-Gov public domain portions).
 * See docs/nsa-github-deep-dive.md for the full investigation.
 */
import { test } from 'node:test';
import fs from 'node:fs';
import vm from 'node:vm';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const html = fs.readFileSync(path.join(here, 'nsa-enigma.html'), 'utf8');
const m = html.match(/<script id="enigma-core">([\s\S]*?)<\/script>/);
if (!m) throw new Error('enigma-core script block not found in nsa-enigma.html — the app file is malformed');

const sandbox = { console, Date, Math, JSON, String, Number, Array, Object, Error, RegExp };
vm.createContext(sandbox);
vm.runInContext(m[1], sandbox, { timeout: 300_000 });
const C = sandbox.EnigmaCore;
if (!C) throw new Error('EnigmaCore did not export from the core block');

test('app file is fully offline (no external URLs, no network calls)', () => {
  const dangerous = /(?:src|href)\s*=\s*["']https?:|fetch\(|XMLHttpRequest|WebSocket|import\s*\(/gi;
  const hits = html.match(dangerous) || [];
  if (hits.length) throw new Error(`found network-referencing constructs: ${hits.join(', ')}`);
});

test('core identifies its provenance', () => {
  if (!/NationalSecurityAgency\/enigma-simulator@f234ee6/.test(C.VERSION)) {
    throw new Error('unexpected VERSION: ' + C.VERSION);
  }
});

for (const [i, t] of C.SELF_TESTS.entries()) {
  test(`self-test ${String(i + 1).padStart(2, '0')}: ${t.name}`, () => {
    const detail = t.run(); // throws on failure
    if (typeof detail !== 'string' || !detail.length) throw new Error('test returned no evidence string');
  });
}

test('the whole suite is exhaustive (16 assertions)', () => {
  if (C.SELF_TESTS.length !== 16) throw new Error(`expected 16 self-tests, found ${C.SELF_TESTS.length}`);
});
