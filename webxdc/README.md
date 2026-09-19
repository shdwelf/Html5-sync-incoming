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

Each app directory is `index.html` + `manifest.toml` + `icon.png`, with the built
package in `dist/`. All of it is committed: this repo is the distribution drop,
so the installable artifact ships beside its source.

## Validate

```bash
python3 webxdc_tool.py validate            # every .xdc in the repo, exits non-zero on failure
python3 webxdc_tool.py validate --all      # also scan incoming/ (raw payload)
python3 webxdc_tool.py selftest            # 23 checks: feed the validator packages built to fail
python3 webxdc_tool.py list                # just enumerate what was found
```

`selftest` exists because this tool is the only gate between the repo and
another package that cannot load, and it had no test of its own: it builds
synthetic packages in a temp directory — nested `index.html`, a packaged
`webxdc.js`, `manifest.xml` containing JSON, a `.zip` extension, path traversal,
non-spec compression, undersized icons — and asserts each verdict. It also pins
`pack()`'s determinism and exercises the fallback manifest reader used on Python
< 3.11 (no `tomllib`, no third-party dependency). `build-all.sh` runs it first.

`webxdc_tool.py` checks the rules from the
[container spec](https://webxdc.org/docs/spec/format.html): `.xdc` extension,
Deflate/Store compression only, `index.html` at the ZIP **root**, a parseable
`manifest.toml` carrying `name`, no unsafe entry paths, no `webxdc.js` inside the
package, and icon format/size. It distinguishes hard failures from warnings from
informational notes, and it deliberately does not walk `incoming/` — that
directory keeps mis-packaged artifacts on purpose, for provenance.

Already wired: [`.github/workflows/verify.yml`](../.github/workflows/verify.yml)
runs `selftest`, `validate`, `gen_icons.py --check`, a full rebuild of all five
packages and `git diff --exit-code`, so nothing can be committed that a messenger
cannot load, and no shipped artifact can drift from the sources that build it.

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

`build-all.sh` also runs `gen_icons.py --check` before it packs: each
`webxdc/<app>/icon.png` must be byte-reproducible from
[`gen_icons.py`](gen_icons.py), so no icon in here is a binary blob that nothing
can rebuild. Regenerate deliberately with `python3 gen_icons.py`.

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

## Icons

| Package | Icon | Source |
|---|---|---|
| `cyberchef.xdc` | 256×256 RGBA, toque + cleaver | drawn by [`gen_icons.py`](gen_icons.py) |
| `shamir.xdc` | 256×256 RGBA, 3-of-5 shares around a key | drawn by [`gen_icons.py`](gen_icons.py) |
| `radar-scope.xdc` | 256×256 RGBA, scope, sweep, three contacts | drawn by [`gen_icons.py`](gen_icons.py) |
| `Cryptomonopoly.xdc` | 256×256 | `../projects/cryptomonopoly-webxdc/icon.png` (a committed asset, no generator) |
| `presskit-reassembler.xdc` | 256×256 | `../projects/presskit-reassembler/dist/gfx/gen_gfx.py`, needs `pyfiglet` + `Pillow` |

Every colour in `gen_icons.py` is lifted from the app's own stylesheet, and the
shapes are polygons — the whole toolchain is `math` + `struct` + `zlib`, so no
PNG in `webxdc/` is unreviewable or unrebuildable. Both icons-in-this-repo gaps
(XDC-7, XDC-8) are closed; `python3 webxdc_tool.py validate` now reports 5/5
with **zero warnings**.
