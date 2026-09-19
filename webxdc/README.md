# webxdc packages

Installable [webxdc](https://webxdc.org) mini-apps — ZIP archives with a `.xdc`
extension that Delta Chat and compatible messengers run in an isolated web view.

This directory holds the packages that have **no separate source project**. The
two that do live next to their sources:

- `projects/cryptomonopoly-webxdc/dist/Cryptomonopoly.xdc`
- `projects/presskit-reassembler/dist/webxdc/presskit-reassembler.xdc`

| App | What it does | Source |
|-----|--------------|--------|
| `cyberchef/` | offline CyberChef build, 416 recipes | `cyberchef/index.html` (1.64 MB, single file) |
| `shamir/` | Shamir Secret Sharing over GF(256) | `shamir/index.html` |
| `radar-scope/` | ADS-B flight-radar HUD | `radar-scope/index.html` |

Each app directory is `index.html` + `manifest.toml`, with the built package in
`dist/`. Both are committed: this repo is the distribution drop, so the
installable artifact ships beside its source.

## Validate

```bash
python3 webxdc_tool.py validate            # every .xdc in the repo, exits non-zero on failure
python3 webxdc_tool.py validate --all      # also scan incoming/ (raw payload)
python3 webxdc_tool.py list                # just enumerate what was found
```

`webxdc_tool.py` checks the rules from the
[container spec](https://webxdc.org/docs/spec/format.html): `.xdc` extension,
Deflate/Store compression only, `index.html` at the ZIP **root**, a parseable
`manifest.toml` carrying `name`, no unsafe entry paths, no `webxdc.js` inside the
package, and icon format/size. It distinguishes hard failures from warnings from
informational notes, and it deliberately does not walk `incoming/` — that
directory keeps mis-packaged artifacts on purpose, for provenance.

Worth wiring into CI or a pre-push hook; it is the only thing standing between
this repo and another package that cannot load.

## Build

```bash
./build-all.sh                             # cyberchef, shamir, radar-scope
bash ../projects/cryptomonopoly-webxdc/build.sh
bash ../projects/presskit-reassembler/dist/make_packages.sh
```

Packing is **deterministic** — entries sorted, timestamps pinned to 1980-01-01,
permissions normalised — so rebuilding from unchanged sources produces identical
bytes and `git status` stays clean. Before this, every rebuild churned the
committed packages.

`build-all.sh` finishes by running the validator over the whole repo, so a build
that produces a non-conformant package fails instead of quietly committing one.

## Rules this directory enforces

1. **`.xdc` is the only extension.** The spec defines it; `.webxdc` does not
   exist. The build scripts used to `cp` out a byte-identical `.webxdc` twin and
   both were committed. `*.webxdc` is now gitignored.
2. **`webxdc.js` is never packaged.** The spec: *"webxdc.js must not be added to
   your .xdc file as they are provided by the messenger."* Both packers refuse to
   stage it. Apps that want the API reference it with
   `<script src="webxdc.js"></script>` — without that reference
   `window.webxdc` is never populated and the app silently runs in local-only
   mode inside a messenger.
3. **`manifest.toml` only.** No `manifest.json`, no `manifest.xml`. The spec
   reads `name` and `source_code_url`; messengers commonly honour `description`
   and `icon`. Keys nothing reads (`entry`, `version`, `summary`, `type`) were
   dropped — the revision lives in git.
4. **`index.html` at the archive root.** `radar-scope` is here because the
   original `radar_scope_webxdc.zip` nested everything under `webxdc-radar/` and
   therefore could not load. That broken original is preserved at
   `../incoming/exports/radar-scope-webxdc-INVALID.zip`.

## Known gaps

- `cyberchef.xdc`, `shamir.xdc` and `radar-scope.xdc` ship **no icon**, so
  messengers show a default. Adding three icons is an appearance decision, left
  to the owner.
- `presskit-reassembler.xdc` ships a 96×96 icon; the spec suggests a square
  between 128×128 and 512×512. The generator now emits 256×256 but the committed
  PNG was not regenerated — that needs `pyfiglet` + `Pillow`.

Both are tracked as XDC-7 / XDC-8 in [../REVIEW.md](../REVIEW.md).
