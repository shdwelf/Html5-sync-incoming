# Deep code review — 2026-09-19

Full-tree review of every source file in the repo (JS, Python, shell, WAT, Java,
HTML) plus every `.xdc` container, checked against the published webxdc
container and API specs.

Findings are ordered by severity. Each one says what is wrong, how it was
proved, and whether it is fixed here or left open with a reason.

**Severity:** `CRIT` breaks the artifact's stated purpose · `HIGH` produces wrong
results or is exploitable · `MED` wrong in edge cases, or silently misleading ·
`LOW` hygiene, portability, dead code.

| # | Area | Severity | Status |
|---|------|----------|--------|
| XDC-1 | radar-scope package unusable | CRIT | fixed |
| XDC-2 | `webxdc.js` shipped inside `.xdc` | HIGH | fixed |
| XDC-3 | `manifest.xml` containing JSON | HIGH | fixed |
| XDC-4 | API never activated in messenger | HIGH | fixed |
| XDC-5 | duplicate `.webxdc` twins committed | MED | fixed |
| XDC-6 | non-spec manifest keys | LOW | fixed |
| XDC-7 | 96×96 icon below spec range | LOW | **open** |
| XDC-8 | three packages ship no icon | LOW | **open** |
| CRYPTO-1 | two event cards inverted | CRIT | fixed |
| CRYPTO-2 | tax drives cash negative | HIGH | fixed |
| CRYPTO-3 | own webxdc echo applied twice | HIGH | fixed |
| CRYPTO-4 | unescaped remote peer data in `innerHTML` | HIGH | fixed |
| CRYPTO-5 | `resetLocal()` message silently dropped | MED | fixed |
| CRYPTO-6 | unreachable 4th exchange-rent tier | MED | fixed |
| CRYPTO-7 | prototype-polluting player id accepted | MED | fixed |
| CRYPTO-8 | `setUpdateListener` re-registered per subscriber | MED | fixed |
| CRYPTO-9 | `tileByIndex` breaks on negative index | LOW | fixed |
| CRYPTO-10 | `s0of()` / dead `Engine` binding | LOW | fixed |
| PY-1 | `file_ext()` probes magic offsets instead of `e_lfanew` | HIGH | fixed |
| PY-2 | MZ load size off by 512 when `cblp == 0` | MED | fixed |
| PY-3 | "case-insensitive" password compare is case-sensitive | MED | fixed |
| PY-4 | `SIGPIPE` handler crashes on Windows at import | MED | fixed |
| PY-5 | stub written to the caller's cwd | MED | fixed |
| PY-6 | hardcoded Linux-only font path | LOW | fixed |
| PY-7 | arg parsing: tracebacks and swallowed typos | LOW | fixed |
| PY-8 | dead code (`guess_com`, `with_bar`, `ne`, `lastSerial`) | LOW | fixed |
| SH-1 | build failure downgraded to a "note" | HIGH | fixed |
| SH-2 | `.zip.xml` extension lies | MED | fixed |
| REPO-1 | committed `__pycache__/*.pyc` | LOW | fixed |
| REPO-2 | shareware committed against stated policy | HIGH | **open** |
| REPO-3 | `internal-storage.7z` unclassified | MED | **open** |

---

## 1. webxdc container conformance

Checked against <https://webxdc.org/docs/spec/format.html> and
<https://webxdc.org/docs/spec/api.html>. A validator was written for this rather
than eyeballing it: [`webxdc/webxdc_tool.py`](webxdc/webxdc_tool.py). Baseline
before the fixes — **2 of 5 packages failed, 3 warned**:

```
[FAIL] radar_scope_webxdc.zip
    ✗ extension is `.zip`; the spec requires `.xdc`
    ✗ `index.html` is not at the ZIP root (found nested: 'webxdc-radar/index.html')
[FAIL] projects/presskit-reassembler/dist/webxdc/presskit-reassembler.xdc
    ✗ `webxdc.js` is inside the package; the spec says the messenger provides it
    ✗ `manifest.xml` is present but contains JSON, not XML
    ! `manifest.json` is not part of the webxdc container spec
[WARN] cyberchef.xdc   ! `manifest.toml` has no `source_code_url`
[WARN] shamir.xdc      ! `manifest.toml` has no `source_code_url`
[WARN] Cryptomonopoly.xdc ! `manifest.toml` has no `source_code_url`
```

After: **5/5 spec-valid**, one residual WARN (XDC-7).

### XDC-1 · CRIT · fixed — radar-scope could not load at all

`radar_scope_webxdc.zip` nested every entry under `webxdc-radar/`, so `index.html`
was not at the ZIP root. The spec requires `index.html` in the archive root; a
messenger opening this package finds nothing to run. It also used `.zip` instead
of `.xdc`, and its manifest declared `init = "index.html"` — `init` is not a
webxdc key (and the entry point is not configurable anyway), while
`source_code_url` was set to the empty string.

Rebuilt as [`webxdc/radar-scope/dist/radar-scope.xdc`](webxdc/radar-scope/dist/radar-scope.xdc)
from the extracted `index.html` with a spec-conformant manifest. The broken
original is preserved for provenance at
`incoming/exports/radar-scope-webxdc-INVALID.zip`.

### XDC-2 · HIGH · fixed — `webxdc.js` was packaged

`make_packages.sh` generated a webxdc shim and zipped it into the package. The
spec is explicit: *"webxdc.js must not be added to your .xdc file as they are
provided by the messenger."* Shipping it means the app's own stub can shadow the
real implementation. Removed from the generator; the packer and `build.sh` now
refuse to stage it.

The shim was also pointless here: `presskit-reassembler.html` never calls
`sendUpdate` / `setUpdateListener`. That package is a single-player offline tool
delivered in a webxdc container, not a collaborative app — now documented in the
manifest rather than implied by a dead shim.

### XDC-3 · HIGH · fixed — `manifest.xml` containing JSON

`make_packages.sh` did `cp "$wx/manifest.json" "$wx/manifest.xml"` under the
comment *"modern + classic manifests for widest app-compat"*. There is no classic
XML manifest in the webxdc spec, and the result was a file named `.xml` whose
bytes are JSON — invalid under any reading. Neither `manifest.json` nor
`manifest.xml` is read by any implementation, so both were dropped; only
`manifest.toml` is emitted now.

### XDC-4 · HIGH · fixed — the multiplayer API was never activated

`cryptomonopoly-webxdc/index.html` loaded `js/board.js`, `js/engine.js`,
`js/transport.js`, `js/app.js` and — per its own comment — deliberately carried
*"No webxdc shim here on purpose"*. But the spec says: *"To activate the webxdc
API you need to use a script reference for `webxdc.js` in your HTML5 app."*

With no reference, `window.webxdc` is never populated, `detectWebxdc()` returns
false, and the game silently falls back to **local hot-seat mode inside Delta
Chat** — every peer plays a private, unsynced game while believing they are in a
shared one. That defeats the entire reason the app exists.

`<script src="webxdc.js"></script>` added to `<head>`. The file is *not* staged
into the package (XDC-2), so in a plain browser the request 404s harmlessly and
the existing fallback still works. This is the standard webxdc pattern.

### XDC-5 · MED · fixed — duplicate `.webxdc` twins

Both build scripts emitted `.xdc` and then `cp`'d it to `.webxdc`; the committed
trees carried both. Byte-identical, so 100% waste and a standing invitation for
the two to drift apart. `Cryptomonopoly.webxdc` and
`presskit-reassembler.webxdc` removed, generators fixed, and `*.webxdc` is now
gitignored. Same story for the loose `cyberchef_webxdc.zip` /
`shamir_webxdc.zip`, which were byte-identical to `cyberchef.xdc` / `shamir.xdc`
under a third name.

### XDC-6 · LOW · fixed — manifest keys no implementation reads

`entry`, `version`, `summary`, `type` appear across the manifests. The spec reads
`name` and `source_code_url`; messengers commonly also honour `description` and
`icon`. The rest was folded into `description` or dropped, and `source_code_url`
was added to all five packages (it surfaces in the messenger's Help menu and was
missing everywhere, or set to `""`).

### XDC-7 · LOW · open — presskit icon is 96×96

The spec suggests a square icon between 128×128 and 512×512. `gen_gfx.py` has
been changed to emit 256×256, but the committed `icon.png` was **not**
regenerated: that script needs `pyfiglet` and `Pillow`, neither of which is
installed in this environment, and shipping an icon I could not render and
inspect would be guessing. Regenerate with:

```bash
pip install pyfiglet pillow
python3 projects/presskit-reassembler/dist/gfx/gen_gfx.py
bash projects/presskit-reassembler/dist/make_packages.sh
```

### XDC-8 · LOW · open — three packages ship no icon

`cyberchef.xdc`, `shamir.xdc` and `radar-scope.xdc` contain only `index.html` +
`manifest.toml`. Legal — the messenger substitutes a default icon — but they
look unfinished in a chat. Designing three icons is a judgement call about
appearance, so it was left to the owner rather than invented here.

---

## 2. Cryptomonopoly game logic

### CRYPTO-1 · CRIT · fixed — two event cards did the exact opposite of their text

`board.js` declares the "pay into the pot" cards with a **negative** `value`:

```js
{ text: "🩸 Bear market. Pay 100 network fee into the pot.", kind: "cash", value: -100, toPot: true },
{ text: "📉 Liquidation cascade. Pay 120 into the pot.",     kind: "cash", value: -120, toPot: true },
```

but the reducer applied it as if `value` were already positive:

```js
if (card.toPot) { p.cash -= v; s.pot += v; }
```

With `v = -100` that is `cash += 100; pot -= 100`. A card that says *pay 100 into
the pot* **handed the player 100 and drained the pot by 100** — a double sign
error, and it could drive the shared pot negative.

Reproduced against the original code (player starts at 1500 cash, pot at 200):

```
 1 🩸 Bear market. Pay 100 network fee into the pot.   cash: 1500 -> 1600   pot: 200 -> 100
 5 📉 Liquidation cascade. Pay 120 into the pot.       cash: 1500 -> 1620   pot: 200 ->  80
```

Both moved the wrong way. `applyEvent` now treats `value` as the **signed change
to the player's cash** everywhere, with `fromPot` capping a gain at what the pot
actually holds and `toPot` routing a loss into it. The full deck re-checked:

```
 1 🩸 Bear market. Pay 100 network fee into the pot.   cash: 1500 -> 1400   pot: 200 -> 300
 5 📉 Liquidation cascade. Pay 120 into the pot.       cash: 1500 -> 1380   pot: 200 -> 320
```

**Why the existing suite missed it:** `engine.test.js` reports "All engine checks
passed" and does assert `pot >= 0` over a 1200-step random game — but it never
compares an effect against the *text* that promises it. The new
`test/regression.test.js` parses each card's own wording (`/pay/i` vs
`/collect|receive/i`) and asserts the observed cash and pot deltas match. It
fails 26 checks against the pre-fix code.

### CRYPTO-2 · HIGH · fixed — Gas Fee could push cash below zero with no bankruptcy

```js
const tax = Math.max(40, Math.floor(p.cash * 0.1));
p.cash -= tax; s.pot += tax;
```

The 40 floor is unconditional, and there is no bankruptcy check — unlike every
other money-losing path in the reducer (`pay()`, `applyEvent()`). A player
holding 10 lands on Gas Fee, pays 40, and continues playing at **−30**. Verified
against the original code at cash 0/5/10/39: `-40`, `-35`, `-30`, `-1`, all still
`alive: true`.

The suite's `full: no negative cash while alive` assertion never tripped because
1200 random steps did not happen to land a nearly-broke player on the tax tile.

Now: the charge is clamped to the balance (`TAX_RATE` / `TAX_FLOOR` promoted to
board data instead of magic numbers in the reducer), and wiping a player out
bankrupts them, matching `pay()`.

### CRYPTO-3 · HIGH · fixed — our own webxdc update was applied twice

`createWebxdcAdapter().broadcast()` did both:

```js
fire(action);                    // apply locally
xdc.sendUpdate({ payload: action }, ...);
```

The API spec says of `setUpdateListener`: *"The callback is called for updates
sent by you or other peers"* — and the Delta Chat developer reference is blunter:
*"All peers, **including the sending one**, will receive the update."* So the
sender's action came straight back through the listener and was reduced a second
time: double movement, double rent, double-spent cash, and every peer diverging
from the sender. For a game whose whole design premise is *"every peer applying
the same action stream converges on the same state"*, this is the one bug that
matters most.

Naively deleting the local `fire()` is **not** the fix: the spec also notes that
when a user has left a group *"you won't get the update by setUpdateListener()"*,
so echo-only would freeze the UI. The adapter now applies optimistically and
de-duplicates its own echo by `(player, seq)` — correct whether or not the host
echoes.

### CRYPTO-5 · MED · fixed — `resetLocal()` was a no-op that looked like it worked

```js
resetLocal() { if (bc) bc.postMessage({ kind: "reset" }); }
...
bc.onmessage = (e) => { if (e.data && e.data.kind === "action") fire(e.data.action); };
```

The reset message was posted and then dropped on the floor, because the handler
only matched `kind === "action"`. Compounding it, `app.js`'s `resetAll()` never
called `resetLocal()` *or* broadcast anything — it reset local state directly. So
in a mirrored two-tab game, and in a webxdc game, "Return to lobby?" reset one
device and left everyone else on the finished game. Reset is now a normal
`RESET` action routed through the transport, handled on the BroadcastChannel
side, and covered by tests.

### CRYPTO-6 · MED · fixed — exchange rent table had an unreachable tier

```js
return [25, 50, 100, 200][Math.min(n, 4) - 1] || 0;
```

The board has **three** `EXCH` tiles (Uniswap, Binance, Coinbase), so `n` can
only reach 3 and the 200 tier was dead data; `Math.min(n, 4)` advertised a
fourth that could never be earned. `EXCH_RENT` is now board data sized to the
tiles that actually exist, with a test asserting the two stay in step.

### CRYPTO-9 · LOW · fixed — `tileByIndex` returned `undefined` for negatives

`TILES[i % BOARD_SIZE]` — JS `%` keeps the sign of the dividend, so
`tileByIndex(-1)` indexes `TILES[-1]` → `undefined` → `tile.type` throws. No
caller passes a negative today, but `applyEvent`'s `move` cards write `p.pos`
from card data, so this is one bad card away from a crash. Now wraps properly.

### CRYPTO-10 · LOW · fixed — misleading dead abstraction

```js
function s0of(s) { return s; } // keep mutated copy; harmless
```

An identity function named as if it returned the *original* state, used in two
guards. Every other guard in the reducer returns `s` directly, so the helper only
obscured which object was being handed back. Removed; guards now `return s`.
`transport.js` also bound `const Engine = global.CryptoEngine` and never used it
(removed), and tracked a `lastSerial` that was written but never read (now
exposed as a getter, since it is the natural resume point).

---

## 3. Cryptomonopoly security

### CRYPTO-4 · HIGH · fixed — remote peer data reached `innerHTML` and CSS unescaped

`app.js` escapes player *names* through `esc()` (which correctly covers
`& < > " '`), but interpolated two other peer-controlled fields raw:

```js
`<div class="join" style="--pc:${p.color}">`      // joinChip
`<span class="join-tok">${p.token}</span>`
`<div class="tt-owner" style="background:${owner.color}">${owner.token}</div>`
`<span class="marker" style="--mc:${state.players[id].color}">${state.players[id].token}</span>`
```

In webxdc mode `color` and `token` arrive from an `ADD_PLAYER` action that any
peer in the chat can craft. `escAttr` is also just an alias of `esc`, so it
provides no attribute-context-specific guarantee. A colour value containing a
quote breaks out of `style="..."`; a token containing markup lands directly in
the DOM.

Fixed at **both** boundaries:

- the reducer now validates on the way into state — `ADD_PLAYER` rejects unsafe
  ids, clips `name` to 18 chars, strips control/angle characters from `token`,
  and only accepts a colour matching `#hex`, a CSS keyword, or `rgb()/rgba()`
  (falling back to the palette otherwise);
- the renderer sanitises again through a new `escColor()` before any value
  reaches a `style` attribute, and escapes every `token`.

Defence in depth is deliberate: state is also rebuilt from replayed webxdc
history on a fresh join, so a value that entered state before this fix could
still be rendered.

### CRYPTO-7 · MED · fixed — prototype-polluting player id accepted

`s.players[p.id] = {...}` with `p.id === "__proto__"` reassigns the map's
prototype instead of adding an entry. `Object.keys()` then hides it while
`s.order` still holds the id, so `s.players[id].alive` resolves against
`Object.prototype` and the roster silently corrupts — a one-line denial of
service from any peer. `__proto__` / `constructor` / `prototype` are now
rejected, and `UPGRADE` requires a real in-range integer tile index (it used
`s.ownership[action.tile]` as a key with the same exposure, masked only by an
`o.ownerId` comparison that happens to fail).

### CRYPTO-8 · MED · fixed — listener re-registered per subscriber

```js
onAction(cb) { listeners.push(cb); if (typeof xdc.setUpdateListener === "function") { xdc.setUpdateListener(...) } }
```

The spec: *"Calling `setUpdateListener()` multiple times is undefined behavior:
in current implementations only the last invocation works."* Registering inside
`onAction` means an Nth subscriber silently discards the previous N−1
registrations. `app.js` calls it once today, so it did not bite — but it is a
trap. Registration is now done once per adapter, idempotently, regardless of
subscriber count, and asserted by a test.

---

## 4. Python tooling

### PY-1 · HIGH · fixed — `file_ext()` guessed instead of reading the header

`tbfence-re/analyze_dos.py` located the NE/LE/PE signature by probing a hardcoded
offset list:

```python
ne = mz[0x40-0x40:][:2]        # dead: always data[:2], i.e. the MZ magic
for probe in (0x40, 0x80, 0x100, 0x180, 0x200, 0x400):
    if mz[probe:probe+2] in (b"NE", b"LE", b"PE", b"LX", b"W3"): return ...
```

Wrong in both directions — a header at an unlisted offset is missed, and an
incidental `NE`/`PE` byte pair inside the DOS stub is reported as the header.
The offset is *stored in the header itself* at `e_lfanew` (0x3C). Proven on
synthetic images:

```
  PE image (e_lfanew=0x40)  -> PE      (correct before and after)
  NE at 0x60                -> NE      (old code returned MZ — missed it)
  stub decoy at 0x80        -> PE?     (old code returned PE — a lie; now flagged heuristic)
  plain .COM                -> raw
```

The fallback scan is kept for DOS tools that leave `e_lfanew` zero, but it is
paragraph-aligned, bounded to the stub region, and its result is suffixed `?` so
a guess is never presented as a fact. The parameter was also named `mz` while
every caller passed the whole file — renamed to `data`.

### PY-2 · MED · fixed — MZ load size off by 512

`cp_pages*512-512+cblp_lastpage` is right for `cblp != 0`, but per the MZ format
`cblp == 0` means the last page is **full**, not empty. Every image whose size is
an exact multiple of 512 was reported 512 bytes short (`cp=4, cblp=0` → 1536
instead of 2048). Extracted into `load_size()` with the rule stated, and tested.

### PY-3 · MED · fixed — "case-insensitive" compare was case-sensitive

`build_dos_stub.py` folds the *typed* character to lowercase but compares it
against the stored password byte untouched:

```asm
    cmp  al, 'A'
    jb   cmp_skip
    cmp  al, 'Z'
    ja   cmp_skip
    or   al, 0x20            ; force lowercase
cmp_skip:
    cmp  al, bl              ; bl never folded
```

So typing `a` against a stored `A` compared 0x61 with 0x41 and denied. The
comment claims case-insensitivity; it only held when the stored password was
already lowercase. Both sides are now folded, and the regenerated machine code
was checked to contain the second fold (`80 fb 41 / 72 08 / 80 fb 5a / 77 03 /
80 cb 20` = `cmp bl,'A'; jb; cmp bl,'Z'; ja; or bl,0x20`). Behaviour verified by
emulating the loop over mixed-case pairs. Stub regenerated: 151 → 164 bytes, and
the two-pass length assertion still holds.

### PY-4 · MED · fixed — `decode_cmb.py` crashed on Windows before doing anything

```python
signal.signal(signal.SIGPIPE, signal.SIG_DFL)
```

`signal.SIGPIPE` does not exist on Windows, so this raised `AttributeError` at
import time — the tool was unusable there regardless of what it was asked to do.
Guarded with `hasattr`.

### PY-5 · MED · fixed — stub written to the caller's cwd

`build_dos_stub.py` opened the relative path `"dos_stub.bin"`, and `wasm/build.sh`
invoked it as `python3 "$here/build_dos_stub.py"` from an arbitrary cwd. Run from
anywhere but `wasm/`, it dropped a stray `dos_stub.bin` in the caller's directory
and left the real one stale — the build still printed "rebuilt dos_stub.bin". Now
writes next to its own source via `__file__`; verified by running from `/tmp` and
confirming no stray file appears. `build.sh` also `cd`s into `$here` for
belt-and-braces.

### PY-6 · LOW · fixed — hardcoded Linux-only font path

`FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"` died with a bare
`OSError` on macOS, Windows, Fedora and Arch. Now searches a candidate list
across platforms, overridable with `PRESSKIT_FONT`, and exits with an actionable
message. The `pyfiglet` / `Pillow` imports are guarded the same way — running the
script here used to produce a raw `ModuleNotFoundError` traceback.

### PY-7 · LOW · fixed — arg parsing tracebacks and swallowed typos

Both CLI tools did `i += 1; int(argv[i])` unguarded (IndexError on a trailing
flag, ValueError on a non-numeric one) and swallowed unknown options with
`elif a.startswith("-"): pass`. A typo like `--uniq` therefore did nothing at all
and still exited 0 — the worst failure mode for a CLI. Now: real messages to
stderr, exit 1, `-h/--help`, and `decode_cmb.py` continues past an unreadable
file instead of tracebacking. Verified:

```
decode_cmb.py: --max needs a value
decode_cmb.py: --max needs an integer, got 'abc'
decode_cmb.py: unknown option '--uniq' (try --help)
decode_cmb.py: cannot read /nope/missing.CMB: [Errno 2] No such file or directory
```

Decoder correctness re-confirmed after the changes (`egre 0xF4 | mallar 0xE4 |
condo 0xF2` → condor, egret, mallard).

### PY-8 · LOW · fixed — dead code

- `analyze_dos.guess_com()` — defined, never called. Removed.
- `gen_gfx.with_bar()` — built a list of `"##"*i` progress-bar strings, returned
  its input **unchanged**, and was never called. So the committed `boot.gif` has
  never had the bar its own comment promised. Removed rather than wired up:
  regenerating the GIFs needs `pyfiglet` + `Pillow`, which are not available
  here, and a script whose output does not match the committed artifact is worse
  than one that does. Re-add it at the marked spot if you want the boot bar.
- `transport.js`'s unused `Engine` binding and write-only `lastSerial`.
- `open(path).write(...)` without a context manager in `gen_gfx.py` and
  `decode_cmb.py` — both now use `with`.

---

## 5. Build scripts

### SH-1 · HIGH · fixed — build failure downgraded to a "note"

```bash
python3 "$here/build_dos_stub.py" >/dev/null 2>&1 \
  && echo "rebuilt dos_stub.bin" || echo "note: dos_stub.bin not rebuilt (keystone missing?)"
```

Under `set -euo pipefail`, the `||` swallows the failure, and `>/dev/null 2>&1`
hides the reason. A build with a missing dependency — or with the two-pass length
assertion firing, which is the script's own correctness check — printed success
and shipped a **stale** `dos_stub.bin`. Now fails loudly with the real error and
the install command, with an explicit `PRESSKIT_SKIP_STUB=1` opt-out for when
skipping is intentional.

Also noted while in here: `dos_stub.bin` has **no runtime consumer**. The app
embeds only the WASM engine (`WASM_B64`); the stub is referenced in prose by
`README.md` and the app's "how it works" panel. That is now stated in the
generator's docstring so nobody assumes editing it changes the shipped app.

### SH-2 · MED · fixed — `.zip.xml` extension lies

Seven files were named `.zip.xml` while their first bytes were `PK\x03\x04` —
plain ZIP data. Anything dispatching on extension (including GitHub's linguist
and any sync tooling) classified them as XML. Renamed to `.zip`. The `.xml`
suffix looks like damage from whatever upload path ingested them; the same
process is the likely source of the ` (N)` collision suffixes.

Non-determinism was also removed from **all four** packers in the repo
(`webxdc_tool.py pack`, `cryptomonopoly-webxdc/build.sh`, and both the `.xdc` and
`.war` steps of `make_packages.sh`): entries sorted, timestamps fixed at
1980-01-01, permissions normalised. They used `z.write()`, which stamps the
current mtime, so every rebuild produced different bytes and churned committed
artifacts — the `.war` was still doing it after the `.xdc` step was fixed, and
was caught only by rebuilding twice and diffing. A rebuild from unchanged sources
is now byte-identical across all four, verified by exactly that test: zero
changed files. This is what makes package diffs meaningful and keeps `git status`
clean.

---

## 6. Repo hygiene

### REPO-1 · LOW · fixed — committed bytecode and duplicated ignores

`cypher-decode/__pycache__/decode_cmb.cpython-311.pyc` was tracked. Removed, and
the four near-identical nested `.gitignore` files (`__pycache__/` + `*.pyc`, plus
`.stage/` in one) were consolidated into a single root `.gitignore`.
`tbfence-re/.gitignore` was **kept** — it carries a redistribution policy
statement, not just patterns (and see REPO-2).

Ten groups of byte-identical files were also removed, 2.35 MB of pure
duplication, most notably `sfx_installer.html` — a 1.6 MB file whose name
suggests a self-extracting installer and whose bytes are an exact copy of
`cyberchef.html`. The name was the only thing distinguishing it, and it was
wrong.

### REPO-2 · HIGH · open — shareware committed against the repo's own stated policy

`projects/tbfence-re/.gitignore` says, verbatim:

> TbFence binaries are 1990s shareware (Thunderbyte B.V.). They are analyzed
> locally but NOT committed here (that would redistribute the shareware).

It then ignores `_src/`, `analysis/`, `*.exe`, `*.com`, `*.sys`, `*.dat`, `*.zip`
— but only within its own directory. The ten archives now in `retro-dos/`
(`tbfence4.zip`, `tinyaes.zip`, `t-ide211.zip`,
`cypher-operation-wildlife-dos-en.zip`, …) sit outside that path and are tracked.
They are exactly the class of artifact the note says must not be redistributed,
and they include what look like PC-SIG shareware discs.

**Not actioned, deliberately.** Removing them is an irreversible call about
somebody else's data and possibly their research inputs, and the analysis notes
in `tbfence-re/ANALYSIS.md` reference them. This needs an owner decision. The
options are: keep them and delete the misleading policy note; move them to
private/LFS storage; or drop them from tracking and document where to obtain
them. A `retro-dos/NOTICE.md` records the conflict so it cannot be missed again.

### REPO-3 · MED · open — `internal-storage.7z` is still unclassified

6.2 MB, 302 HTML entries, and the single largest object in the repo. It overlaps
the loose files already at root (`crypto-recovery-os-*`, `netscope*`,
`index (1..58).html`, twenty `seize_quartiers_quine_<timestamp>.html` builds) so
it looks like the working directory these exports came from. Left intact: it
needs 7z tooling to unpack (`py7zr` was installed ad hoc for this review, not
added as a dependency) and a decision about whether the repo wants 302 more
classified files or one archive that stands in for them.

---

## Reviewed and found sound

Worth recording, so the diff above is not read as "everything was broken":

- **`engine.js` determinism.** The reducer is genuinely pure — no `Date`, no
  `Math.random`, dice carried in the action, event draws driven by a counter.
  Two peers fed the same action stream converge byte-for-byte, and the existing
  test proves it. This is the right design for webxdc and it was already correct.
- **Board geometry.** `buildPositions()` claims a 7×7 ring of 24 perimeter cells
  with corners at 0/6/12/18. Counted: 7 + 6 + 6 + 5 = 24, and the corner indices
  land exactly where the comment says. Correct and correctly documented.
- **`esc()`** covers `& < > " '` — the right set, including the single quote most
  escapers miss.
- **`build_dos_stub.build()`** two-pass assembly with
  `assert len(code) == len(once)` is a genuinely good way to catch
  position-dependent codegen, and it held across the CRYPTO/PY-3 changes.
- **`decode_cmb.decode_tokens()`** — the bit-7-terminated packed-string decode is
  correct and the docstring explains the format better than most published
  notes on it.
- **`analyze_dos.pascal_strings()` / `ascii_strings()`** — correct, including the
  skip-past-consumed-bytes advance that naive scanners get wrong.
- **`retro-media-doc/js/nav.js`** — one real nit: `location.pathname.split("/").pop().replace(".html", "")`
  replaces the *first* `.html` anywhere in the segment rather than a suffix, and
  the song list is duplicated from `chip.js` so the two can drift. Neither
  misbehaves on the current filenames; left alone because `nav.js` is presentational
  and the chapter set is stable.
- **`tbfence-re/ghidra_decompile_all.py`** — flagged in passing: `len(funcs)` on a
  Ghidra `FunctionIterator` after the iterator has been consumed is unreliable, and
  same-named functions overwrite each other's `.c` output. Not fixed: it is a
  Ghidra/Jython post-script that cannot be executed or tested here, so changing it
  would be guesswork. Recorded rather than "fixed" blind.
