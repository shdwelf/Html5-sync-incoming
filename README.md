# Html5-sync-incoming

Drop target for single-file HTML5 apps, webxdc (`.xdc`) mini-apps, and the raw
archives they arrive in. It is an **archive + distribution repo**, not an
application: most of the value here is knowing *what each artifact is* and being
able to *rebuild the installable ones*.

Until 2026-09-19 every file sat loose in the repo root with browser-download
collision names (`index (1).html`, `foo (3).zip`), seven ZIPs carried a bogus
`.zip.xml` extension, and three unrelated apps were all called `index*.html`.
The tree is now classified — see [INVENTORY.md](INVENTORY.md) for what every
artifact is and where it came from, and [REVIEW.md](REVIEW.md) for the code
review that went with the reorganisation.

## Layout

```
apps/        single-file HTML5 apps, openable straight from disk
  crypto/      wallets, seed tools, recovery, cipher cookbook
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
  webxdc_tool.py           spec validator + deterministic packer
  build-all.sh             rebuild cyberchef, shamir, radar-scope
  cyberchef/ shamir/ radar-scope/     index.html + manifest.toml + dist/*.xdc
docs/        Greeran family-research notes and heraldry
retro-dos/   1980s-2000s DOS shareware corpus — analysis INPUT, see its NOTICE
incoming/    unprocessed sync payload, kept for provenance
  workspaces/  Arena workspace snapshots (UUID is the canonical id)
  exports/     named app-export ZIPs
```

## Validate and rebuild the webxdc packages

```bash
# check every .xdc in the repo against the container spec — exits non-zero on failure
python3 webxdc/webxdc_tool.py validate

# rebuild the packages that live in webxdc/ (deterministic: unchanged sources -> identical bytes)
./webxdc/build-all.sh

# rebuild the ones owned by a source project
bash projects/cryptomonopoly-webxdc/build.sh
bash projects/presskit-reassembler/dist/make_packages.sh
```

`.xdc` artifacts are committed on purpose (this repo is the distribution drop),
but only ever one copy per app: the container spec defines `.xdc`, so the
byte-identical `.webxdc` twins the build scripts used to emit are now gitignored.

## Run the tests

```bash
cd projects/cryptomonopoly-webxdc
node --test test/*.test.js
```

Three files: `engine.test.js` (pure-reducer determinism and rules),
`dom.test.js` (boots the real UI headlessly and plays a game), and
`regression.test.js` (added 2026-09-19; each test reproduces a specific defect
listed in [REVIEW.md](REVIEW.md) and fails against the pre-fix code).

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

## Known open items

Tracked with severity and evidence in [REVIEW.md](REVIEW.md#open-items):

- `retro-dos/` holds 1990s commercial shareware that `projects/tbfence-re/.gitignore`
  explicitly says must not be redistributed. Needs an owner decision.
- `incoming/internal-storage.7z` (6.2 MB, 302 HTML files) is still an
  unclassified bulk dump.
- Three `.xdc` packages ship no icon, so messengers fall back to a default.
- `projects/presskit-reassembler/dist/gfx/icon.png` is 96×96; the spec suggests
  128–512. Regenerating needs `pyfiglet` + `Pillow`, which are not installed here.
