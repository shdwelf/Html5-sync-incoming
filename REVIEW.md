# Deep code review — 2026-09-19

Full-tree review of every source file in the repo (JS, Python, shell, WAT, Java,
HTML) plus every `.xdc` container, checked against the published webxdc
container and API specs.

**Two passes.** §1–§6 are the first pass, which classified the tree and fixed 30
defects. §7 is the second pass over what that left behind: the three items marked
`open`, the two items marked "recorded rather than fixed", the build scripts that
the fixes themselves edited, and `apps/`. It found nine more defects (one HIGH),
closed every open item in this file, and says plainly which two findings were
deliberately **not** patched.

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
| XDC-7 | 96×96 icon below spec range | LOW | fixed (2nd pass) |
| XDC-8 | three packages ship no icon | LOW | fixed (2nd pass) |
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
| REPO-2 | shareware committed against stated policy | HIGH | resolved — kept, terms documented |
| REPO-3 | `internal-storage.7z` unclassified | MED | fixed (2nd pass) — indexed, not unpacked |
| XDC-9 | no `webxdc/` app activated the webxdc API | HIGH | **fixed (2nd pass)** |
| XDC-10 | radar-scope used a non-existent `webxdc.getInfo()` | MED | **fixed (2nd pass)** |
| JS-1 | `nav.js` mangled page names, duplicated the song list | LOW | **fixed (2nd pass)** |
| PY-9 | validator needed Python 3.11+ and had no test | MED | **fixed (2nd pass)** |
| PY-10 | Ghidra post-script lost same-named functions | MED | **fixed (2nd pass)** |
| SH-3 | `make_packages.sh` ran its own manifest through the shell | MED | **fixed (2nd pass)** |
| SH-4 | `wasm/build.sh` reported a refresh that had not happened | MED | **fixed (2nd pass)** |
| APP-1 | `apps/` are not all offline; 3 reference a missing `manifest.json` | MED | **recorded, not patched** |
| DOC-1 | two READMEs still described the pre-fix build | LOW | **fixed (2nd pass)** |

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

After the first pass: **5/5 spec-valid**, one residual WARN (XDC-7).
After the second pass: **5/5 spec-valid, zero warnings**, and `webxdc_tool.py
selftest` (23 checks) proves the validator itself still catches all of it.

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

### XDC-7 · LOW · fixed (2nd pass) — presskit icon is now 256×256

The spec suggests a square icon between 128×128 and 512×512; `gen_gfx.py` emitted
256×256 but the committed `icon.png` was still the old 96×96. The blocker recorded
in the first pass — *"that needs `pyfiglet` + `Pillow`, which are not installed
here"* — was simply a missing `pip install`; both were installed and the generator
run.

The useful part is what did **not** change: `intro.gif`, `boot.gif` and
`intro.txt` came out **byte-identical** to the committed artifacts (sha-256
compare), so `gen_gfx.py` is a faithful generator and `icon.png` is the only
artifact the run touched. `validator` went from `WARN icon.png is 96x96` to silent,
and `make_packages.sh` re-embedded the new PNG into both `.xdc` and `.war`
(12,877 / 12,908 bytes, rebuild byte-identical).

### XDC-8 · LOW · fixed (2nd pass) — the three missing icons are generated, not sourced

`cyberchef.xdc`, `shamir.xdc` and `radar-scope.xdc` contained only `index.html` +
`manifest.toml`. The first pass left them alone because "designing three icons is a
judgement call about appearance" — true, but the reason it could not be *settled*
was that the only way in was a binary blob nobody could review or rebuild.

[`webxdc/gen_icons.py`](webxdc/gen_icons.py) removes that: the three icons are
drawn from shapes in code, stdlib only (`math`, `struct`, `zlib` — no Pillow, no
`pyfiglet`), rendered at 256×256 RGBA with 3× supersampling, and encoded as a PNG
with no `tIME` chunk so two runs are byte-identical. Motifs come from what each app
is — a toque and cleaver for 416 CyberChef recipes, 3-of-5 shares around a key for
Shamir, a phosphor scope with sweep and three contacts for radar-scope — and every
colour is a hex the app's own stylesheet already uses, so "does the icon match the
app" is checkable rather than taste-based.

Verification beyond looking at them:

- `python3 gen_icons.py --check` compares the committed PNGs with a fresh render
  **pixel for pixel** (decoding them with the same minimal reader it uses for
  nothing else), so `build-all.sh` can refuse to pack drifted art. It does.
- legibility at the sizes that matter was checked at 48×48 rather than assumed.
- `pack()` picks `icon.png` up from the app directory, and the manifests gained
  `icon = "icon.png"`; all five packages still validate with zero warnings and the
  rebuilt `.xdc`s are byte-reproducible.
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

### REPO-2 · HIGH · resolved (2nd pass) — shareware kept, and the policy note corrected

`projects/tbfence-re/.gitignore` claimed this class of artifact "must NOT be
committed here (that would redistribute the shareware)", while ten archives of
exactly that class sat in `retro-dos/` outside the directory's scope. First pass
flagged it and stopped, because choosing between "delete the files" and "delete the
note" is an owner decision.

The second pass found the thing that actually settles it, which nobody had read:
**the licence text inside the archives themselves.** Every row of
[`retro-dos/NOTICE.md`](retro-dos/NOTICE.md) is quoted from a file in the ZIP it
describes:

- TbFence's own `LICENSE.DOC` grants it: *"The evaluation package of the TbFence
  software may be distributed freely without charge in evaluation form only"*,
  conditioned on completeness and no alteration — which is what this repo ships
  (contents untouched; only the bogus `.zip.xml` container name was fixed). So the
  repo was never in breach; the note was over-broad, and also misattributed the
  licensor (ESaSS B.V., not "Thunderbyte B.V." — Thunderbyte is the brand).
- Turtle Identd is GPL with its sources in the archive; TOPSECRET says *"This
  program is freely distributable"*; TinyFish is *"Freeware Executable and Public
  Domain Source Files"*; TinyAES, TinyCrypt and TinyAES declare themselves free.
- Two archives assert copyright and grant **nothing**: `thecoder.zip` (*"THE CODER
  V1.5 (c) 1999 by Cold_Ice"*, a scene release) and
  `cypher-operation-wildlife-dos-en.zip` (no licence text at all, third-party
  abandonware-mirror provenance). Those two are named as removal candidates with
  the exact command, and were not executed: deleting research inputs over a judgement
  about period publishing, while the bytes stay reachable from this repo's history
  anyway, is not a cleanup. `cypher-decode` does not depend on the CYPHER archive —
  the decoder is data-agnostic — so removal would cost nothing but that is the
  owner's call, not a side effect of tidying.

`projects/tbfence-re/.gitignore` now states the rule it actually enforces (this
directory's own extracted/derived artifacts stay out) and points at the evidence.
The directory SHA-256 table in `NOTICE.md` lets anyone confirm they are reading the
same ten files that were reviewed.

### REPO-3 · MED · fixed (2nd pass) — `internal-storage.7z` is indexed, not unpacked

6.2 MB, 302 entries, 104 MB unpacked, and the one object in the repo whose contents
nobody could name. `py7zr` was installable, so "needs tooling that isn't here" was
not a real blocker either.

[`incoming/index_internal_storage.py`](incoming/index_internal_storage.py) walks the
archive and writes [`incoming/internal-storage.index.tsv`](incoming/internal-storage.index.tsv):
`sha256 bytes mtime path title` for all 302 entries, sorted, regenerable, and
`--check`-able so the committed index cannot silently go stale.
[`incoming/INTERNAL_STORAGE.md`](incoming/INTERNAL_STORAGE.md) is the
classification. The interesting result is the first one:

**20 of the 302 entries are byte-identical to files already in `apps/`.** That is
not a tidy-up, it is proof — the archive *is* the working directory those
downloads came from, and the first pass's rename calls were right, including the
ones that looked like guesses (`index (1) (1).html` → `hacker-dice-8ball-3d.html`,
`netscope (2).html` → `netscope-v5.html`, the `-r1`/`-r2` ordering). Everything the
tree claims about provenance is now checkable with `sha256sum` and a `grep`.

The other 282: 37 are duplicates of each other, 68 are still named `index (N).html`
across 43 different apps, 120 titles exist nowhere in the tree (superseded builds
and unpromoted exports), 2 entries are 0 bytes, and 2 are not documents at all
(`ndx.js.html` is an extracted script fragment, `variables.html` is a form panel with
the markup stripped). All recorded. The archive stays as the container: unpacking
would add 302 loose files and 17× the bytes to buy nothing but filenames.

---

## 7. Second pass — what the first pass left behind

Nine findings. The pattern in most of them: a fix that was applied in one place and
not in the others, or a check that reported success without verifying anything.

### XDC-9 · HIGH · fixed — none of the three `webxdc/` apps could ever reach the API

XDC-4 was "cryptomonopoly loaded no `webxdc.js`, so the multiplayer API was never
activated". The same defect was still live in **all three** packages in `webxdc/`,
each of which has real webxdc code:

```
webxdc/shamir/index.html       8 × sendUpdate     9 × setUpdateListener     0 × <script src="webxdc.js">
webxdc/cyberchef/index.html    7 × sendUpdate     8 × setUpdateListener     0 × <script src="webxdc.js">
webxdc/radar-scope/index.html  2 × sendUpdate     1 × setUpdateListener     0 × <script src="webxdc.js">
```

Shamir shares secret-shares to the chat, CyberChef shares recipes, radar-scope
broadcasts aircraft. All three probe `window.webxdc || null` at parse time and
"degrade gracefully" when it is absent — which is exactly the trap: inside Delta
Chat, without the script reference the host never injects the API, so the probe
finds nothing, every capability flag stays false, and the feature is silently
unavailable **in the only environment it was written for**. The repo's own
`webxdc/README.md` rule 2 states the requirement; three of its five packages
broke it, and one of them (radar-scope) was *rebuilt* by the first pass without
this being noticed, because the rebuild was byte-faithful to a broken source.

Fix: `<script src="webxdc.js"></script>` first in `<head>` of each `index.html`,
with a comment saying why the 404 when opened from disk is expected. The file is
still never packaged — `webxdc_tool.py pack` refuses it and all five `.xdc`s
contain zero `webxdc.js` entries, verified after the rebuild.

### XDC-10 · MED · fixed — radar-scope asked the API for a method that does not exist

```js
const selfAddrInfo = webxdc.getInfo();
myAddr = selfAddrInfo.selfAddr || 0;
```

The webxdc API exposes identity as **properties** — `selfAddr`, `selfName`,
`serial` — there is no `getInfo()`. So on a real host that line threw a `TypeError`,
the `catch` replaced `webxdc` with the app's own standalone simulator, and peer
sharing stayed dead even after XDC-9 was fixed. That is the value of reading the
API surface rather than the container format: fixing the script tag alone would
have shipped a package that *looks* activated.

Now reads `webxdc.selfAddr` / `webxdc.selfName`, and the simulator only exists in
the `else` branch. Both paths executed against a stubbed `window.webxdc`:

```
in a messenger   -> myAddr = "alice@example.org"   myName = "Alice"   uses the real object, no getInfo
straight from disk -> myAddr = number              myName = "Standalone User"   sim sendUpdate present
```

Also recorded, not fixed: the app's feeds go through `fetch()` plus five public CORS
proxies, which a webxdc webview does not provide. Its `demoMode` fallback is what
runs inside a messenger, so the package is functional but not live there — stated in
`webxdc/radar-scope/manifest.toml` rather than discovered by whoever installs it.

### JS-1 · LOW · fixed — `nav.js` page-name mangling and a duplicated song list

The nit the first pass "left alone because it is presentational":

- `(pathname.split("/").pop() || "index.html").replace(".html", "")` replaced the
  **first** `.html` anywhere in the segment, so `foo.html.bak.html` became `foo`
  and the nav highlighted nothing (or the wrong thing). Now `/\.html?$/i`.
- the song picker fell back to a hardcoded `["title","arcade","ballad"]` when
  `window.chip` was missing — a copy of `chip.js`'s `SONGS` keys that could drift,
  and a play button that did nothing when clicked. The list now comes from
  `chip.js` only, and with no engine present the control is not rendered at all.

Verified headlessly against a stub DOM over the real file: 3 controls with the
engine, 2 without (control omitted), `arcade`/`index` active states correct, and
`foo.html.bak.html` no longer resolves to a chapter.

### PY-9 · MED · fixed — the validator needed Python 3.11, and nothing tested it

`import tomllib` at module scope means the tool that gates every `.xdc` in the repo
raised `ModuleNotFoundError` on Python 3.8–3.10 — on the machine most likely to be
a random contributor's. Two dead imports (`io`, `subprocess`) were still there too.

`parse_manifest()` now uses `tomllib` when it exists and otherwise
`_toml_min()`: `key = literal` lines and `#` comments, quote-aware. Anything it
cannot be sure about — tables, dotted keys, an unterminated string — **raises
instead of guessing**, and `validate()` reports that as a warning about the tool
("not checked, needs Python 3.11+"), never as a failure of the package. All five
real manifests parse to the same dict either way (checked by forcing
`_tomllib = None`).

The bigger gap was that the validator had no test. `webxdc_tool.py selftest` builds
synthetic packages in a temp directory and asserts 23 checks — every failure class
from §1 (nested `index.html`, packaged `webxdc.js`, JSON inside `manifest.xml`,
`.zip` extension, missing `name`, non-spec keys as INFO, 96×96 icon as WARN, path
traversal, bzip2 rejection, `Store` accepted, "no manifest is legal and says so"),
plus `pack()` determinism, `pack()`'s refusal to stage the shim, the fallback
reader, and the size sniffers. It is mutation-tested by construction: disabling the
ZIP-root check drops it to 22/23 and exits 1. `build-all.sh` now runs it before it
packs anything.

### PY-10 · MED · fixed — the Ghidra post-script threw away decompilations

First pass: *"Not fixed: it is a Ghidra/Jython post-script that cannot be executed
or tested here, so changing it would be guesswork."* The two bugs were concrete
enough to fix, and both are now covered by an executable harness
(`ghidra`/`jython2` stubs for `DecompInterface`, `FunctionManager`,
`getScriptArgs`) rather than eyeballing:

- `len(funcs)` on a drained `FunctionIterator` is unreliable. `funcs` is a real
  list now, so the success line counts what it says it counts, and failures are
  counted separately: `Decompiled 3/5 functions into /tmp/gout (2 failed)`.
- output files were keyed by function name only, so same-named functions — routine
  in 16-bit DOS binaries with thunks and per-segment duplicates — overwrote each
  other and the last one won silently. `slug()` appends the entry point and
  sanitises the characters `::`/`/` replacement missed; the harness feeds two
  functions both named `entry` and both files come out (`entry__0x100.c`,
  `entry__0x180.c`).
- `getDecompiledFunction()` can return `None` on a completed-but-empty result; that
  path is now a counted failure instead of an `AttributeError` that aborts the run
  mid-way and leaves a half-written `_combined.c`.

Jython 2.7 constraint recorded in the header: no f-strings, and single-argument
`print` only, because `print(a, b)` there is a tuple dump.

### SH-3 · MED · fixed — `make_packages.sh` ran its own manifest through the shell

```
projects/presskit-reassembler/dist/make_packages.sh: line 23: source_code_url: command not found
```

That message appeared on **every build** of the presskit package, and the committed
artifact proves what it did: the heredoc delimiter was unquoted (`<<TOML`), the
comment line contains backticks, so bash executed `name` and `source_code_url` as
commands and shipped a manifest beginning

```
# webxdc manifest -- the spec reads  and 
```

Verified straight out of `git show HEAD:...presskit-reassembler.xdc`. Only a comment
was eaten here, so the damage is small — the *class* is not: build scripts that
interpolate text into shipped files must not run the shell over them, and `set -euo
pipefail` does **not** abort on a failed command substitution inside a heredoc, so
this was silent for a whole release cycle. Both heredocs are quoted (`<<'TOML'`,
`<<'XML'`) and the script now ends by parsing the manifest it generated and running
the container validator over the `.xdc` — the gate `webxdc/build-all.sh` had and
this one did not.

### SH-4 · MED · fixed — `wasm/build.sh` reported a refresh that had not happened

```python
s = re.sub(r'(const WASM_B64 = ")[^"]*(";)', ..., s, count=1)
open(app, "w").write(s)
print("refreshed WASM_B64 in", app)
```

If the constant is renamed, re-quoted, or dropped, `re.sub` returns the input
unchanged, `count=1` is satisfied by zero substitutions, and the script prints
success while leaving the app embedding a **stale WASM engine** — then
`make_packages.sh` dutifully ships it into `.xdc` and `.war`. Same failure shape as
SH-1, one file over. Also `base64 -w0` is GNU-only; macOS/BSD die on `-w`.

Now: `subn` + `n != 1` → hard error naming the file; portable
`base64 | tr -d '\n\r'`; no write when the bytes already match; and a fourth step
that re-reads the app and asserts the embedded base64 equals the freshly compiled
`presskit.wasm`. Run against the committed tree it says `verified: … embeds
presskit.wasm (367 bytes)`, and both packages embed that same constant. Injecting
truncated bytes makes it fail with `embeds 268 chars of base64, presskit.wasm needs
492 — stale engine bytes`.

### APP-1 · MED · recorded, deliberately not patched — `apps/` is not uniformly offline

The apps are the one part of the tree the first pass reorganised but did not open.
Scanned for external loads and unresolvable local references:

| file | what it reaches for |
|---|---|
| `apps/misc/hacker-dice-8ball-3d.html` | `cdn.tailwindcss.com`, `cdnjs.cloudflare.com/…/three.min.js` |
| `apps/crypto/banano-paper-wallet-generator{,-offline}.html` | `cdn.tailwindcss.com`, Google Fonts, `monkey.banano.cc` API — the one named **`-offline`** included |
| `apps/crypto/crypto-recovery-os-*.html` | Cloudflare Insights beacon, `react.dev`, `monkey.banano.cc` |
| `apps/genealogy/gedcom-tsp-visualizer-r2.html`, `apps/media/image-format-encyclopedia-quine.html`, `apps/genealogy/greeran-resume-portfolio.html` | Cloudflare Insights beacon |
| `apps/crypto/crypto-recovery-os-{offline,standalone-r1,standalone-r2}.html` | `<link rel="manifest" href="./manifest.json">` — **no such file exists**, ever did, or is in the sync payload |

Three separate things, three different verdicts:

1. **The beacon is not the app.** `static.cloudflareinsights.com/beacon.min.js` was
   injected by the host the file was downloaded *from*; it is third-party telemetry
   in a "crypto recovery" tool, and it fires whenever the file is opened while
   online. Deletion is a one-line change (`sed -i '/cdn-cgi\|cloudflareinsights/d'`
   or your editor) and it would break nothing — the apps guard for their CDN
   scripts (`typeof THREE !== 'undefined'` in the dice app; Tailwind degrades to
   unstyled), so it is offered rather than applied.
2. **The CDN dependencies are the app.** Inlining Tailwind/three.js would make these
   genuinely offline but would fork the artifacts; recorded in
   [`INVENTORY.md`](INVENTORY.md#runtime-dependencies) instead.
3. **The dangling `manifest.json` is a lie about the artifact**, and cheap to fix —
   but see the reason below.

Why none of this was patched here, in one sentence: **20 of the 302 files in
`incoming/internal-storage.7z` are byte-identical to files in `apps/`, and that hash
identity is the repo's only proof that a classified artifact is the artifact as
received.** Editing an app in place trades a console warning and a 404 for the
ability to tell "what arrived" from "our fork" — a bad trade for a repo whose stated
purpose is being a distribution drop. If `apps/` should become maintained forks
rather than received artifacts, that is a change in what this repo *is*, and it
should be decided as such: introduce `apps/upstream/` (pristine) and
`apps/fixed/`, or add a patch series, and record the mapping the way the rename
table already does.

### DOC-1 · LOW · fixed — two READMEs documented the pre-fix build

`projects/cryptomonopoly-webxdc/README.md` still said `./build.sh` writes
"`dist/Cryptomonopoly.xdc` (+ `.webxdc` copy)" (XDC-5 deleted that copy and
gitignores the extension), and `dist/README.md` for presskit still advertised
`webxdc/presskit-reassembler.webxdc` and `manifest.{json,xml,toml}` (XDC-2/-3/-5).
Both corrected, with the *why* rather than just the new text; the presskit gfx row
now records that regenerating reproduces `intro.gif` / `boot.gif` / `intro.txt`
byte-identically, which is the assurance that the icon change was isolated.

`README.md` also linked to `REVIEW.md#open-items`, an anchor that has never existed
in this file — every "open item" was a status flag on a finding. Fixed by pointing at
this section, and every relative markdown link and anchor in the repo was checked with
a link/anchor walk: 0 broken.

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
- **Script-reference discipline in the other apps.** `shamir`, `cyberchef` and
  `radar-scope` all probe the webxdc capability-by-capability (`selfName`, `sendUpdate`,
  `setUpdateListener`, `sendToChat`) instead of assuming them, and all three send
  spec-shaped `{payload: …}` updates with a human `info` string — the payload shapes
  were checked, not assumed. The bug was the missing `<script>` tag (XDC-9) and one
  invented method (XDC-10), both of which made correct code unreachable; the code
  itself was right.
- **`retro-media-doc/js/nav.js`** and **`tbfence-re/ghidra_decompile_all.py`** were
  left in this list by the first pass with nits attached and "not fixed" reasons
  attached. Both are fixed in §7 (JS-1, PY-10), the second one under a stubbed-Ghidra
  harness that executes the loop rather than reading it.
- **`apps/` self-containment, mostly.** A scan of every `<script src>` / `<link href>` /
  `<img src>` in `apps/*.html` and `webxdc/*/index.html` for local references found no
  dangling sibling files at all after the reorganisation — the single-file promise
  holds for structure (no app lost a `wordlist.js` or an `assets/` directory when the
  tree was classified). The exceptions are third-party CDNs and one absent PWA
  manifest, all in APP-1.
- **Provenance, now checkable.** `incoming/internal-storage.index.tsv` gives a SHA-256
  per archive entry; 20 match files in `apps/` exactly, which independently confirms
  the rename map including which of a differing pair was the newer build.
- **Artifact↔generator agreement.** `gen_gfx.py` reproduces the committed GIFs and
  `intro.txt` byte-for-byte; `gen_icons.py --check` reproduces the three PNGs
  pixel-for-pixel; `pack()`/`make_packages.sh` rebuilds all four packers to identical
  bytes. `build-all.sh` runs the selftest and both icon checks, so a drifted artifact
  fails the build instead of being committed quietly.
