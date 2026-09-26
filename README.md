# Html5-sync-incoming

Drop target for single-file HTML5 apps, webxdc (`.xdc`) mini-apps, and the raw
archives they arrive in. It is an **archive + distribution repo**, not an
application: most of the value here is knowing *what each artifact is* and being
able to *rebuild the installable ones*.

Until 2026-09-19 every file sat loose in the repo root with browser-download
collision names (`index (1).html`, `foo (3).zip`), seven ZIPs carried a bogus
`.zip.xml` extension, and three unrelated apps were all called `index*.html`.
The tree is now classified — see [INVENTORY.md](INVENTORY.md) for what every
artifact is and where it came from, and [REVIEW.md](REVIEW.md) for the code review
that went with it. Two review passes ran: the first classified the tree and fixed
30 defects, the second closed everything it left open and fixed nine more. 39
findings, 37 fixed, one resolved by documenting evidence instead of guessing
(`retro-dos/`), one deliberately recorded and not patched (`apps/` — see
[REVIEW.md APP-1](REVIEW.md#app-1--med--recorded-deliberately-not-patched--apps-is-not-uniformly-offline)).

## Layout

```
apps/        single-file HTML5 apps, openable straight from disk
  crypto/      wallets, seed tools, recovery, cipher cookbook, NSA Enigma suite
  genealogy/   GEDCOM viewers, Greeran family research, résumé
  network/     NetScope scanners
  media/       image-format encyclopedia
  misc/        everything else that is still a standalone app
projects/    real source trees with their own build scripts
  cryptomonopoly-webxdc/   webxdc board game (+ the only test suite in repo)
  presskit-reassembler/    HTML5/WASM -> DOS .COM, also builds .war and .jar
  retro-media-doc/         multi-chapter static documentary site
  demoscene-introz/        single-page static site
  cypher-decode/           .CMB animal-list decoder for CYPHER Operation Wildlife
  tbfence-re/              DOS reverse-engineering scripts + notes
webxdc/      installable .xdc packages that have no separate source project
  webxdc_tool.py           spec validator + deterministic packer + selftest
  gen_icons.py             draws the three icon.png files from source
  build-all.sh             selftest -> icon-reproducibility check -> rebuild all four
  cyberchef/ shamir/ radar-scope/     index.html + manifest.toml + icon.png + dist/*.xdc
  eeg-feedback-lab/         index.html + manifest.toml + dist/*.xdc (deliberate messenger-default icon)
docs/        research notes and reconstruction boundaries
  nsa-github-deep-dive.md    NSA org survey + enigma-simulator conversion record
  EEG_PATHWAYS_RESEARCH_AND_RECONSTRUCTION.md  historical source-check and non-clinical EEG simulator boundary
retro-dos/   1980s-2000s DOS shareware corpus — analysis INPUT, see its NOTICE
incoming/    unprocessed sync payload, kept for provenance
  workspaces/  Arena workspace snapshots (UUID is the canonical id)
  exports/     named app-export ZIPs
  INTERNAL_STORAGE.md + internal-storage.index.tsv + index_internal_storage.py
               the classification of the 302-entry 7z, indexed rather than unpacked
```

## Validate and rebuild the webxdc packages

```bash
# check every .xdc in the repo against the container spec — exits non-zero on failure
python3 webxdc/webxdc_tool.py validate

# check the checker: 23 assertions over synthetic bad packages (run by build-all.sh)
python3 webxdc/webxdc_tool.py selftest

# the three icons must still be reproducible from gen_icons.py (also run by build-all.sh)
python3 webxdc/gen_icons.py --check

# rebuild the packages that live in webxdc/ (deterministic: unchanged sources -> identical bytes)
./webxdc/build-all.sh
# Includes eeg-feedback-lab, a non-clinical EEG-feedback architecture simulator.
# Its historical source-checking and hard safety/transport boundaries are in
# docs/EEG_PATHWAYS_RESEARCH_AND_RECONSTRUCTION.md.

# rebuild the ones owned by a source project
bash projects/cryptomonopoly-webxdc/build.sh
bash projects/presskit-reassembler/dist/make_packages.sh   # ends by validating its own output

# re-verify that the committed internal-storage index matches the 7z (needs py7zr)
python3 incoming/index_internal_storage.py --check
```

Current state: **6/6 packages spec-valid**, on Python 3.8+
(no `tomllib` needed — the validator has a fallback manifest reader).

## CI

[`.github/workflows/verify.yml`](.github/workflows/verify.yml) runs exactly the
commands above on every push and PR, plus the step that makes the whole
"deterministic builds" claim worth something: after rebuilding all five packages it
runs `git diff --exit-code`, so a committed `.xdc` that no longer matches its own
sources fails CI instead of drifting. It also re-runs `gen_icons.py --check`, the
validator's selftest and the Cryptomonopoly suite. No third-party actions and no
extra dependencies — every check is a command that works from a bare checkout.

`.xdc` artifacts are committed on purpose (this repo is the distribution drop),
but only ever one copy per app: the container spec defines `.xdc`, so the
byte-identical `.webxdc` twins the build scripts used to emit are now gitignored.

## Run the tests

```bash
cd projects/cryptomonopoly-webxdc
node --test test/*.test.js

node --test apps/crypto/nsa-enigma.test.mjs

# From the repository root: portable C11 timing-ledger test for the
# non-clinical EEG timing reference.
make -C projects/eeg-timing-reference test

# Check the EAGLE 9 XML's well-formedness and the bounded non-patient
# 1-Wire topology. This is not EAGLE ERC/DRC or an IP/safety certification.
python3 projects/eeg-ip67-onewire-reference/tools/validate_eagle_schematic.py
```

Three Cryptomonopoly files: `engine.test.js` (pure-reducer determinism and
rules), `dom.test.js` (boots the real UI headlessly and plays a game), and
`regression.test.js` (added 2026-09-19; each test reproduces a specific defect
listed in [REVIEW.md](REVIEW.md) and fails against the pre-fix code). The EEG timing
test validates only ordered, bounded timestamp tracing and clock-health gating;
it is not a medical-device or hardware-driver test. The EAGLE check only guards
the reference XML and its non-patient 1-Wire topology; see
[`projects/eeg-ip67-onewire-reference/`](projects/eeg-ip67-onewire-reference/)
for its BOM, ingress verification plan, and release blockers.

`nsa-enigma.test.mjs` (added 2026-09-21) extracts the embedded core from
`apps/crypto/nsa-enigma.html` and runs its 16-assertion self-test — Enigma
golden vectors (`ZPJJSVSPGBW`, `BDZGO`/`EWTYX`, double-stepping), the full
Rejewski attack end-to-end (intercepts → chain index → 105,456-setting
catalogue → plugboard recovery → decrypted plaintexts), and a check that the
app file makes zero network references. The same assertions run in the app's
Self-test tab, so the committed HTML and CI cannot drift apart.

## Naming rules

Applied when the tree was classified, and worth keeping:

- **No ` (N)` suffixes.** Those are browser-download collisions, not revisions.
  Where the copies really differed, the suffix became a `-rN` revision or a name
  taken from the artifact's own `<title>`.
- **The extension must match the bytes.** A ZIP is `.zip`; a webxdc package is
  `.xdc`. Seven files were named `.zip.xml` while containing ZIP data.
- **`index.html` is never a top-level name** unless it is genuinely a site root.
  Three different apps were called `index*.html`.
- **Workspace snapshots keep their UUID.** It is the only stable id the sync
  source gives them; the app inside is recorded in the inventory instead.

## Status of the open items

Nothing in the tree is unclassified or unfixed any more; what is left is two
decisions that belong to the owner, each with the command that makes it.

- **`retro-dos/` (REPO-2) — resolved by reading the archives.** The license text
  *inside* `tbfence4.zip` grants exactly what this repo does:
  *"The evaluation package of the TbFence software may be distributed freely
  without charge in evaluation form only"*, complete and unaltered. Turtle Identd
  is GPL with its sources in the archive, TOPSECRET says *"freely distributable"*,
  TinyFish is public-domain source. Two archives carry a copyright assertion with
  no grant — `thecoder.zip` (Cold_Ice, 1999) and
  `cypher-operation-wildlife-dos-en.zip` (no licence text at all) — and are named as
  removal candidates in [`retro-dos/NOTICE.md`](retro-dos/NOTICE.md) with the
  one-line `git rm` to run if you agree. They were not deleted here: this is someone
  else's research input, and the bytes stay in git history either way.
- **`apps/` third-party payload (APP-1) — recorded, deliberately not patched.** Five
  apps load Tailwind/three.js from CDNs, six carry a Cloudflare Insights beacon
  injected by the host they were downloaded from, and three reference a
  `./manifest.json` that has never existed. Stripping the beacon is safe and
  one line; it was not done because 20 of these files are byte-identical to entries
  in `incoming/internal-storage.7z`, and that hash identity is the only proof the
  repo has that a classified artifact is the artifact as received.
- `retro-media-doc/js/nav.js` and `tbfence-re/ghidra_decompile_all.py` were "left
  alone, cannot be tested here". Both are now fixed and both are exercised — nav.js
  against a stub DOM, the Ghidra post-script against a stubbed `DecompInterface`.
- The presskit `.jar` still needs a JDK (`java/build.sh` anywhere on OpenJDK 17+);
  no prebuilt jar ships here because the sandbox could not reach a JDK host.

## Conventions worth keeping

- Deterministic packing is not cosmetic: `git status` staying clean after a rebuild
  is what makes "did this change alter the shipped bytes?" a question you can ask.
- Any generated asset must have a generator in the tree, and the build must check it
  (`gen_icons.py --check` inside `build-all.sh`). A committed PNG with no source is
  how `boot.gif` grew a progress bar in a comment and never in the file.
- Shipped text never goes through an unquoted heredoc. See
  [REVIEW.md SH-3](REVIEW.md#sh-3--med--fixed--make_packagessh-ran-its-own-manifest-through-the-shell).
