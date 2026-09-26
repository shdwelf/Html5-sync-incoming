# Inventory & classification

Every tracked artifact, what it actually is, and where it came from.

This exists because the repo had no such record: 89 files sat loose in the root,
three unrelated apps were all named `index*.html`, seven ZIPs were named
`.zip.xml`, and 22 files carried browser-download ` (N)` collision suffixes with
no indication of whether the copies differed. Nothing was mis-classified more
dangerously than `netscope (2).html`, which turned out to be **v5** while the
unsuffixed `netscope.html` was **v2** — a naive "keep the base name, delete the
numbered copy" cleanup would have thrown away the newer build.

Classification is by **what the artifact is**, not by how it arrived.

| Directory | Contains | Trust level |
|-----------|----------|-------------|
| `apps/` | finished single-file HTML5 apps | open directly in a browser |
| `projects/` | source trees with build scripts | build, test, then use |
| `webxdc/` | installable `.xdc` packages | spec-validated, drop into a messenger |
| `docs/` | Greeran family-research notes | prose |
| `retro-dos/` | 1980s–2000s DOS shareware corpus | **analysis input — see NOTICE** |
| `incoming/` | unprocessed sync payload | provenance, not deliverables |

---

## `webxdc/` — validated mini-app packages

All six packages in the repo now pass [`webxdc_tool.py validate`](webxdc/webxdc_tool.py)
(see [REVIEW.md §1](REVIEW.md#1-webxdc-container-conformance) for what was wrong before).

| Package | Source | Status |
|---------|--------|--------|
| `webxdc/cyberchef/dist/cyberchef.xdc` | `webxdc/cyberchef/index.html` (1.68 MB single-file CyberChef build, 441 recipes; 26 Boxentriq recipes added 2026-09-25, see docs/BOXENTRIQ_DEEP_DIVE.md) | rebuilt, manifest normalised |
| `webxdc/shamir/dist/shamir.xdc` | `webxdc/shamir/index.html` (Shamir Secret Sharing over GF-256) | rebuilt, manifest normalised |
| `webxdc/radar-scope/dist/radar-scope.xdc` | `webxdc/radar-scope/index.html` (ADS-B flight-radar HUD) | **repacked from an invalid package** |
| `webxdc/eeg-feedback-lab/dist/eeg-feedback-lab.xdc` | `webxdc/eeg-feedback-lab/index.html` (synthetic EEG-feedback architecture demonstrator) | non-clinical simulator; raw samples never use messenger updates; source-check and safety boundary in `docs/EEG_PATHWAYS_RESEARCH_AND_RECONSTRUCTION.md` |
| `projects/cryptomonopoly-webxdc/dist/Cryptomonopoly.xdc` | full source tree + test suite | rebuilt after logic and API fixes |
| `projects/presskit-reassembler/dist/webxdc/presskit-reassembler.xdc` | `projects/presskit-reassembler/presskit-reassembler.html` | rebuilt; icon regenerated to 256×256 |

`radar-scope` is the one that was broken: the original `radar_scope_webxdc.zip`
nested everything under `webxdc-radar/`, so `index.html` was not at the ZIP root
and no messenger could run it. The invalid original is kept at
`incoming/exports/radar-scope-webxdc-INVALID.zip`. Its source workspace is
`incoming/workspaces/workspace-019f130a-…zip` ("Flight Radar HUD - ADS-B Tracker").

All six packages validate. The three original missing icons (XDC-8) are drawn
by [`webxdc/gen_icons.py`](webxdc/gen_icons.py) — 256×256 RGBA, stdlib only, no
binary asset in git that cannot be rebuilt — and the 96×96 presskit icon (XDC-7)
was regenerated at 256×256 by its own `gen_gfx.py`. `build-all.sh` refuses to
pack unless `python3 webxdc/gen_icons.py --check` still reproduces the committed
PNGs. `eeg-feedback-lab` deliberately has no custom icon; the messenger default
is an accepted presentation fallback, not a validation failure.

---

## `projects/` — source trees

| Project | Language | Build | Test | Notes |
|---------|----------|-------|------|-------|
| `cryptomonopoly-webxdc/` | JS (browser, no bundler) | `build.sh` | `node --test test/*.test.js` — **3 files, all passing** | gameplay and webxdc tests |
| `eeg-timing-reference/` | portable C11 | no release build; `make test` writes a temporary `/tmp` host test | ordered latency-trace + clock-health test | non-clinical PTP/TSN/SPI/I²C instrumentation reference; no AFE or hardware driver |
| `eeg-ip67-onewire-reference/` | Autodesk EAGLE 9 XML + Markdown/CSV + Python | no board/release build; schematic-only by design | `python3 tools/validate_eagle_schematic.py` | pre-production, non-patient 1-Wire accessory-ID reference; candidate BOM and IP67 verification plan; no patient circuit or ingress/safety/medical claim |
| `presskit-reassembler/` | HTML5 + WAT/WASM + Python + Java + QBASIC | `wasm/build.sh`, `dist/make_packages.sh`, `dist/java/build.sh` | none | emits `.xdc`, `.war`, `.jar`, QBASIC runner |
| `retro-media-doc/` | HTML/CSS/JS static site | none (7 chapters) | none | multi-page; nav in `js/nav.js` |
| `demoscene-introz/` | single HTML page | none | none | |
| `cypher-decode/` | Python 3 | none | none | `.CMB` packed-string decoder |
| `tbfence-re/` | Python 3 + Bash + Ghidra/Jython | `run.sh` | none | DOS RE scripts; `ghidra_decompile_all.py` needs Ghidra |

Undeclared third-party dependencies, none of them recorded in any requirements
file (there is no `requirements.txt` or `package.json` anywhere in the repo):

| Needed by | Package | Available here |
|-----------|---------|----------------|
| `presskit-reassembler/wasm/build_dos_stub.py` | `keystone-engine` | yes (installed ad hoc) |
| `presskit-reassembler/dist/gfx/gen_gfx.py` | `pyfiglet`, `Pillow` | **no** |
| `presskit-reassembler/wasm/build.sh` | `wabt` (`wat2wasm`) | **no** |
| `presskit-reassembler/dist/java/build.sh` | a JDK | **no** |
| `tbfence-re/ghidra_decompile_all.py` | Ghidra + Jython | **no** |
| `cryptomonopoly-webxdc/test/dom.test.js` | Node ≥ 18 (`node:test`) | yes (v22) |
| `eeg-timing-reference/Makefile` | `make` + a C11 compiler (`cc`) | yes (host-only test) |

---

## `apps/` — single-file HTML5 apps

Names in **bold** were changed; the old name is in the rename map at the bottom.

### `apps/crypto/`
| File | Title | Note |
|------|-------|------|
| **`banano-paper-wallet-generator.html`** | Banano Paper Wallet Generator & Rare MonKey Scanner | was the root `index.html` |
| **`banano-paper-wallet-generator-offline.html`** | same app, offline-repaired build | was `generator.offline.repaired (1).html`, an orphan with no base file |
| **`crypto-cookbook.html`** | Crypto Cookbook — Block, Stream, Asymmetric, MAC, PQC | 251 KB; a distinct app from the 1.64 MB CyberChef build in `webxdc/cyberchef/`, despite the similar subject |
| `crypto-recovery-os-offline.html` | Crypto Recovery OS \| Vanity Miner | |
| **`crypto-recovery-os-standalone-r1.html`** | Crypto Recovery OS \| Vanity Miner | was the unsuffixed original |
| **`crypto-recovery-os-standalone-r2.html`** | same, larger build | was `… (1).html` |
| `nsa-enigma.html` | NSA Enigma Suite — machine & Rejewski attack lab | converted from NationalSecurityAgency/enigma-simulator@f234ee6 (MIT + US-Gov PD); fully offline; 16-assertion self-test in-page, CI-gated by `nsa-enigma.test.mjs`; see [docs/nsa-github-deep-dive.md](../docs/nsa-github-deep-dive.md) |

### `apps/genealogy/`
| File | Title |
|------|-------|
| **`greeran-seize-quartiers-breakthrough.html`** | Greeran Seize Quartiers — COMPLETE |
| **`greeran-seize-quartiers-session8.html`** | Greeran Seize Quartiers — Session 8 · Final Findings |
| **`greeran-military-service-map.html`** | Greeran Family — Military Service Map |
| **`greeran-resume-portfolio.html`** | ACME Cryptographic Audit Workstation // Steven Greeran Portfolio (was `Resume.html`) |
| **`seize-quartiers-quine-2026-07-20.html`** | Seize Quartiers — Family Tree Visualization & Query Workbench |
| **`gedcom-tsp-visualizer-r1.html`** / **`-r2.html`** | GEDCOM → HTML5 + Melissa Geocoding + TSP Route Planner |

Referenced by prose in `docs/GREERAN_HERALDRY.md` and `docs/RESEARCH_FINDINGS.md`
under their **old** filenames. Those are plain-text mentions, not links, so
nothing breaks — but they are now stale. Updating them means editing research
notes, which is the author's call.

### `apps/network/`
| File | Title | Note |
|------|-------|------|
| **`netscope-v2.html`** | NetScope v2 — IPv4/IPv6 + HTML5 Nmap + Bypass Lab | was the unsuffixed `netscope.html` |
| **`netscope-v5.html`** | NetScope v5 — Mobile UX Overhaul + Bottom Nav | was `netscope (2).html` — **the newer build** |

### `apps/media/`
| File | Title |
|------|-------|
| **`image-format-encyclopedia-quine.html`** | Image Format Encyclopedia — All Formats, Encodings & Transfer Protocols |

### `apps/misc/`
| File | Title | Note |
|------|-------|------|
| **`hacker-dice-8ball-3d.html`** | Hacker Dice & Mystic 8-Ball | was `index (1).html`. Three.js/WebGL build (`initThreeJS`, `idleRotate`, `animateCube`) |
| **`hacker-dice-8ball-2d.html`** | Hacker Dice & Mystic 8-Ball | was `index (2).html`. 2D-canvas build (`drawDice`, `shakeBall`, `setBallMode`) |
| **`membershub-private-app-store.html`** | MembersHub · Private App Store | was `index.offline.repaired.html` — a *third* unrelated app named `index` |
| `censorbench.html` | CensorBench — Censorship Testing & Sorting Benchmark Suite | source project is `incoming/workspaces/workspace-019f17c5-…zip` (50 files: `analytics.py`, `bandit.py`, `benchmark.py`, `.env.example`) |
| **`zip-offline-audit-viewer.html`** | HTML5 Offline ZIP Audit & Repair Viewer | |

The three `-3d` / `-2d` dice builds are **variants, not revisions** (39.6%
similar, disjoint function sets) — both were kept and named for what they are.

---

### Runtime dependencies

`apps/` are single *files*, so nothing here lost a sibling `assets/` or `wordlist.js`
when the tree was classified — every local `src`/`href` in all 20 documents resolves
(swept with a link checker over `apps/**` and `webxdc/*`). Five of them do reach out
to the internet, and six carry a Cloudflare Insights beacon that was injected by the
site they were downloaded from, not written by the app:

| file | needs the network for | third-party payload |
|---|---|---|
| `misc/hacker-dice-8ball-3d.html` | Tailwind CDN, three.js r128 (guarded by `typeof THREE !== 'undefined'`, so it renders without) | — |
| `crypto/banano-paper-wallet-generator.html` | Tailwind CDN, Google Fonts | — |
| `crypto/banano-paper-wallet-generator-offline.html` | as above **plus** the `monkey.banano.cc` image API — despite the name, "offline" means self-contained UI, not no-network | — |
| `crypto/crypto-recovery-os-{offline,standalone-r1,standalone-r2}.html` | `monkey.banano.cc` | Cloudflare Insights beacon; a `<link rel="manifest" href="./manifest.json">` that has never had a target |
| `genealogy/gedcom-tsp-visualizer-r2.html` | geocoding APIs, user-supplied keys | Cloudflare Insights beacon |
| `genealogy/greeran-resume-portfolio.html`, `media/image-format-encyclopedia-quine.html` | — | Cloudflare Insights beacon |
| `network/netscope-v2.html` | 7 probes (Cloudflare trace, `captive.apple.com`, ipify…) — that *is* the app | Cloudflare email-protection markup around one obfuscated address |

Left exactly as received, on purpose: 20 of these files are byte-identical to entries
in `incoming/internal-storage.7z`, and that identity is the proof that what is in
`apps/` is the artifact as it arrived. See
[REVIEW.md APP-1](REVIEW.md#app-1--med--recorded-deliberately-not-patched--apps-is-not-uniformly-offline)
for what stripping the beacon would cost and why it was not done here.

## `retro-dos/` — DOS shareware corpus

Ten archives with internal timestamps from 1980 to 2008, i.e. genuine period
material rather than 2026 exports. They are the analysis inputs for
`projects/tbfence-re/` and `projects/cypher-decode/`.

| File | Internal date | Bytes |
|------|---------------|-------|
| `tbfence4.zip` | 1995-08-01 | 53,473 |
| `tops9720.zip` | 1997-04-20 | 14,154 |
| `tinyfish.zip` | 1998-06-10 | 10,746 |
| `t-ide211.zip` | 1998-11-10 | 251,654 |
| `tinycr11.zip` | 1998-11-16 | 13,736 |
| `t-sec104.zip` | 1999-03-14 | 16,401 |
| `thecoder.zip` | 1999-04-22 | 50,092 |
| `track.zip` | 1999-10-30 | 14,504 |
| `tinyaes.zip` | 2001-10-03 | 30,820 |
| `cypher-operation-wildlife-dos-en.zip` | 2008-06-23 | 481,436 |

All ten were named `.zip.xml` or had no classification at all; seven of them
carried the bogus `.xml` extension while containing ZIP data.

**Read [`retro-dos/NOTICE.md`](retro-dos/NOTICE.md) before redistributing this
directory** — it now records what each archive's *own* text says about
redistribution, quoted from the `LICENSE.DOC` / `FILE_ID.DIZ` / `README` inside
each one, with a SHA-256 per file. REPO-2 is resolved as "keep and document":
TbFence's licence expressly permits free distribution of the complete unaltered
evaluation package (which is what is committed here), Turtle Identd is GPL with
its sources in the archive, TOPSECRET/TinyFish/TinyAES/TinyCrypt are freeware or
public domain by their own statement, and the two archives that assert copyright
while granting nothing — `thecoder.zip` (Cold_Ice, 1999) and
`cypher-operation-wildlife-dos-en.zip` (no licence text at all) — are named as
removal candidates with the exact command, deliberately not executed on their
behalf. `projects/tbfence-re/.gitignore` was corrected to say what it actually
enforces instead of a blanket prohibition its own sibling directory contradicts.

---

## `incoming/` — unprocessed sync payload

Kept for provenance. Nothing in here is a deliverable, and the validator
deliberately does not scan it (see `DEFAULT_EXCLUDE` in `webxdc_tool.py`).

### `incoming/workspaces/` — 19 Arena workspace snapshots

Filenames kept verbatim: the UUID is the only stable identifier the sync source
provides. All have ZIP timestamps normalised to 1980-01-02 (machine-generated).
What is actually inside each:

| UUID (short) | Contents | Bytes |
|--------------|----------|-------|
| `019ebb94` | Ensō × BIP-39 Haiku Wallet | 144,000 |
| `019ebce4` | PIM — Peer Instant Messaging (Web) | 80,587 |
| `019ec234` | `enso/enso-vault.html`, `enso/wordlist.js` | 93,908 |
| `019ec266` | Crypto Monopoly — NFT Edition | 63,400 |
| `019ec268` | Crypto Monopoly — NFT Edition (later build) | 64,316 |
| `019ec66d` | `gedcom-viewer/index.html` | 38,369 |
| `019ec8fc` | `news-globe/` (README, app.js, gazetteer.js, index.html) | 42,086 |
| `019ec900` | `news-globe/` + `news-globe.htm` | 82,405 |
| `019ec90e` | `family-tree/` + `news-globe/` | 134,899 |
| `019f0a80` | `zip_offline_viewer.html` | 67,279 |
| `019f0df1` | GitCrypt Push — Codeberg & Bitbucket Secure Client | 109,570 |
| `019f0e7b` | Banano Seed & Address Studio | 78,088 |
| `019f0e81` | Banano Seed & Address Studio (later build) | 77,789 |
| `019f130a` | **Flight Radar HUD — ADS-B Tracker** → source of `radar-scope.xdc` | 137,031 |
| `019f17c5` | **CensorBench project** — 50 files incl. `analytics.py`, `bandit.py`, `benchmark.py`, `artifacts/calibrators.json`, `.env.example` | 154,116 |
| `019f1abe` | FILOFAX Digital Time Machine | 35,443 |
| `019f2d39` | `kryptos_vrml.html` | 54,049 |
| `019fbf6f` | AETHERIS — 3D Ahnentafel Doughnut & ZPE Module | 79,097 |
| `019fbfd8` | AETHERIS — 3D Ahnentafel Doughnut & ZPE Module (later build) | 85,544 |

### `incoming/exports/` — 31 app-export ZIPs

Internal timestamps run 2015-11-19 → 2026-09-14. Where a ` (N)` collision pair
differed, the newer archive (by internal timestamp and, in every observed case,
by size and feature count) became the higher `-rN`:

| Old name | New name | Internal title of each |
|----------|----------|------------------------|
| `advanced-gedcom-visualization-application.zip` | `gedcom-visualizer-arena-r1.zip` | "Arena Web Dev App" |
| `… (1).zip` | `gedcom-visualizer-cryptomonopoly-r2.zip` | "CryptoMonopoly — GEDCOM Family Tree Visualizer" |
| `cost-optimized-model-routing-agent.zip` | `model-routing-agent-r1.zip` | "AI Task Router Dashboard" |
| `… (1).zip` | `model-routing-agent-r2.zip` | "Router Agent — Cost-Optimized LLM Routing" |
| `create-inlined-html5-app.zip` | `seed-haiku-lab-r1.zip` | "Seed Haiku Lab — BIP-39/44/49/84" |
| `… (1).zip` | `bip39-haiku-forge-r2.zip` | "BIP-39 Haiku Forge — Corrected Validator" |
| `crypto-nft-monopoly-game.zip` | `cryptopoly-r1.zip` | "Cryptopoly - The Crypto & NFT Board Game" |
| `… (1).zip` | `cryptopoly-live-r2.zip` | "Cryptopoly Live - HTML5 Monopoly Crypto NFT Game" |
| `html5-bananocoin-miner-development.zip` | `bananocoin-monkey-miner-r1.zip` | "MonKey Miner — Banano Rare Attribute Hunter" |
| `… (1).zip` | `bananocoin-miner-r2.zip` | "Bananocoin Miner - Mine Rare Attributes!" |
| `html5-noise-cancellation-app.zip` | `anc-studio-pro-multiband-r1.zip` | "ANC Studio Pro — Adaptive Multi-Band FxLMS" |
| `… (1).zip` | `anc-studio-ultra-r2.zip` | "ANC Studio Ultra - HTML5 Active Noise Control" |
| `… (2).zip` | `anc-studio-pro-howling-r3.zip` | "ANC Studio Pro — Adaptive FxLMS + Howling Suppression" |
| `… (3).zip` | `anc-studio-pro-optimized-r4.zip` | "ANC Studio Pro — Optimized FxLMS" |
| `masonic-symbols-educational-app (1).zip` | `masonic-symbols-explorer.zip` | orphan suffix dropped — no base file existed |
| `radar_scope_webxdc.zip` | `radar-scope-webxdc-INVALID.zip` | invalid container, kept as evidence |
| `Haiku Supplies.zip` | `haiku-supplies.zip` | space and case normalised only |

Fourteen further exports already had meaningful slugs and were moved unchanged (14 unchanged + 17 renamed = the 31 files in `incoming/exports/`).

### `incoming/internal-storage.7z`

6,236,510 bytes packed / 104,024,159 unpacked, 302 flat entries (301 `.html`,
one `.old`), 265 distinct payloads. The largest single object in the repo and the
only 7z.

**Classified 2026-09-19 — see
[incoming/INTERNAL_STORAGE.md](incoming/INTERNAL_STORAGE.md)** and its
[302-row index](incoming/internal-storage.index.tsv)
(`sha256 bytes mtime path title`, regenerable with
`incoming/index_internal_storage.py`). It is the working directory these exports
were downloaded *from*: 20 entries are byte-identical to files now in `apps/`
(`index (56).html` → `apps/crypto/banano-paper-wallet-generator.html`,
`netscope (2).html` → `apps/network/netscope-v5.html`, …), which also confirms the
rename map below was resolved the right way round. The remaining 282 are
superseded builds — 68 of them still named `index (N).html` across 43 different
apps — plus 120 titles that were never promoted, 2 empty files and 2 non-HTML
fragments. Kept packed: unpacking would add 302 loose files and 17× the bytes for
no new information. `py7zr` is only needed to *regenerate* the index, never to use
this repo.

---

## Removed

Ten byte-identical duplicate groups (2,346,151 bytes) plus one committed build
artifact. Everything is recoverable from git history.

| Removed | Identical to | Bytes |
|---------|--------------|-------|
| `sfx_installer.html` | `cyberchef.html` | 1,639,661 |
| `cyberchef_webxdc.zip` | `cyberchef.xdc` | 463,033 |
| `cryptomonopoly-webxdc/dist/Cryptomonopoly.webxdc` | `…/Cryptomonopoly.xdc` | 103,743 |
| `workspace-019f0e81-…(1).zip` | same UUID, unsuffixed | 77,789 |
| `workspace-019ec66d-…(1).zip` | same UUID, unsuffixed | 38,369 |
| `presskit-reassembler/dist/webxdc/presskit-reassembler.webxdc` | `…/presskit-reassembler.xdc` | 11,749 |
| `shamir_webxdc.zip` | `shamir.xdc` | 5,345 |
| `pim-alpha (1).zip` | `pim-alpha.zip` | 4,420 |
| `convert-pcglobe-to-html5 (1).zip` | unsuffixed original | 168,336 |
| `research-first-development-approach (3).zip` | unsuffixed original | 156,042 |
| `cypher-decode/__pycache__/decode_cmb.cpython-311.pyc` | build artifact | 5,038 |

`sfx_installer.html` deserves a note: a 1.6 MB file named like a self-extracting
installer whose bytes were an exact copy of `cyberchef.html`, confirmed by
`<title>` ("CyberChef — HTML5 (Renovated Kitchen)"). The filename was the only
thing distinguishing it and it was wrong.

**Not** removed, because they are *not* duplicates:
`presskit-reassembler/dist/gfx/intro.txt` and `dist/qbasic/INTRO.TXT` are
byte-identical, but `make_packages.sh` copies one to the other on purpose
(`cp "$here/gfx/intro.txt" "$here/qbasic/INTRO.TXT"`). They are two build outputs
of one source, not an accident.

---

## Rename map

Complete `git mv` record. Git detected all 138 as renames at 100% similarity, so
`git log --follow` still works on every one of these paths.

| Old path | New path |
|----------|----------|
| `generator.offline.repaired (1).html` | `apps/crypto/banano-paper-wallet-generator-offline.html` |
| `index.html` | `apps/crypto/banano-paper-wallet-generator.html` |
| `cookbook.html` | `apps/crypto/crypto-cookbook.html` |
| `crypto-recovery-os-offline.html` | `apps/crypto/crypto-recovery-os-offline.html` |
| `crypto-recovery-os-standalone.html` | `apps/crypto/crypto-recovery-os-standalone-r1.html` |
| `crypto-recovery-os-standalone (1).html` | `apps/crypto/crypto-recovery-os-standalone-r2.html` |
| `gedcom_tsp_final_inline.html` | `apps/genealogy/gedcom-tsp-visualizer-r1.html` |
| `gedcom_tsp_final_inline (1).html` | `apps/genealogy/gedcom-tsp-visualizer-r2.html` |
| `Greeran_Military_Service_Map.html` | `apps/genealogy/greeran-military-service-map.html` |
| `Resume.html` | `apps/genealogy/greeran-resume-portfolio.html` |
| `Greeran_COMPLETE_BREAKTHROUGH_Final.html` | `apps/genealogy/greeran-seize-quartiers-breakthrough.html` |
| `Greeran_Seize_Quartiers_Session8_Final.html` | `apps/genealogy/greeran-seize-quartiers-session8.html` |
| `seize_quartiers_quine_2026-07-20T12-30-45.html` | `apps/genealogy/seize-quartiers-quine-2026-07-20.html` |
| `image-encyclopedia-quine.html` | `apps/media/image-format-encyclopedia-quine.html` |
| `censorbench.html` | `apps/misc/censorbench.html` |
| `index (2).html` | `apps/misc/hacker-dice-8ball-2d.html` |
| `index (1).html` | `apps/misc/hacker-dice-8ball-3d.html` |
| `index.offline.repaired.html` | `apps/misc/membershub-private-app-store.html` |
| `zip_offline_viewer.html` | `apps/misc/zip-offline-audit-viewer.html` |
| `netscope.html` | `apps/network/netscope-v2.html` |
| `netscope (2).html` | `apps/network/netscope-v5.html` |
| `advanced-html5-control-room.zip` | `incoming/exports/advanced-html5-control-room.zip` |
| `html5-noise-cancellation-app (2).zip` | `incoming/exports/anc-studio-pro-howling-r3.zip` |
| `html5-noise-cancellation-app.zip` | `incoming/exports/anc-studio-pro-multiband-r1.zip` |
| `html5-noise-cancellation-app (3).zip` | `incoming/exports/anc-studio-pro-optimized-r4.zip` |
| `html5-noise-cancellation-app (1).zip` | `incoming/exports/anc-studio-ultra-r2.zip` |
| `html5-bananocoin-miner-development (1).zip` | `incoming/exports/bananocoin-miner-r2.zip` |
| `html5-bananocoin-miner-development.zip` | `incoming/exports/bananocoin-monkey-miner-r1.zip` |
| `create-inlined-html5-app (1).zip` | `incoming/exports/bip39-haiku-forge-r2.zip` |
| `build-bip-39-haiku-wallet.zip` | `incoming/exports/build-bip-39-haiku-wallet.zip` |
| `build-generative-haiku-wallet.zip` | `incoming/exports/build-generative-haiku-wallet.zip` |
| `convert-opml-to-hosted-rss.zip` | `incoming/exports/convert-opml-to-hosted-rss.zip` |
| `convert-pcglobe-to-html5.zip` | `incoming/exports/convert-pcglobe-to-html5.zip` |
| `crypto-mnemonic-mining-app.zip` | `incoming/exports/crypto-mnemonic-mining-app.zip` |
| `crypto-nft-monopoly-game (1).zip` | `incoming/exports/cryptopoly-live-r2.zip` |
| `crypto-nft-monopoly-game.zip` | `incoming/exports/cryptopoly-r1.zip` |
| `gedcom-family-tree-application.zip` | `incoming/exports/gedcom-family-tree-application.zip` |
| `gedcom-visualizer-and-cryptomonopoly.zip` | `incoming/exports/gedcom-visualizer-and-cryptomonopoly.zip` |
| `advanced-gedcom-visualization-application.zip` | `incoming/exports/gedcom-visualizer-arena-r1.zip` |
| `advanced-gedcom-visualization-application (1).zip` | `incoming/exports/gedcom-visualizer-cryptomonopoly-r2.zip` |
| `Haiku Supplies.zip` | `incoming/exports/haiku-supplies.zip` |
| `html5-gedcom-tree-visualizer.zip` | `incoming/exports/html5-gedcom-tree-visualizer.zip` |
| `html5-image-enhancement-workstation.zip` | `incoming/exports/html5-image-enhancement-workstation.zip` |
| `java-to-js-enso-conversion.zip` | `incoming/exports/java-to-js-enso-conversion.zip` |
| `masonic-symbols-educational-app (1).zip` | `incoming/exports/masonic-symbols-explorer.zip` |
| `cost-optimized-model-routing-agent.zip` | `incoming/exports/model-routing-agent-r1.zip` |
| `cost-optimized-model-routing-agent (1).zip` | `incoming/exports/model-routing-agent-r2.zip` |
| `pim-alpha.zip` | `incoming/exports/pim-alpha.zip` |
| `radar_scope_webxdc.zip` | `incoming/exports/radar-scope-webxdc-INVALID.zip` |
| `research-first-development-approach.zip` | `incoming/exports/research-first-development-approach.zip` |
| `rodger-ramrod-archive.zip` | `incoming/exports/rodger-ramrod-archive.zip` |
| `create-inlined-html5-app.zip` | `incoming/exports/seed-haiku-lab-r1.zip` |
| `Internal storage.7z` | `incoming/internal-storage.7z` |
| `workspace-019ebb94-0ad9-791e-8594-df17eecfa0b3.zip` | `incoming/workspaces/workspace-019ebb94-0ad9-791e-8594-df17eecfa0b3.zip` |
| `workspace-019ebce4-dc09-75cd-b196-ae07de281525.zip` | `incoming/workspaces/workspace-019ebce4-dc09-75cd-b196-ae07de281525.zip` |
| `workspace-019ec234-e099-747b-99ac-0342a3f282bb.zip` | `incoming/workspaces/workspace-019ec234-e099-747b-99ac-0342a3f282bb.zip` |
| `workspace-019ec266-db4b-7e2c-813b-c3f8a2708035.zip` | `incoming/workspaces/workspace-019ec266-db4b-7e2c-813b-c3f8a2708035.zip` |
| `workspace-019ec268-efe7-7195-b456-aea071c2c56c.zip` | `incoming/workspaces/workspace-019ec268-efe7-7195-b456-aea071c2c56c.zip` |
| `workspace-019ec66d-762c-7581-97a4-da38f171b334.zip` | `incoming/workspaces/workspace-019ec66d-762c-7581-97a4-da38f171b334.zip` |
| `workspace-019ec8fc-4714-7ea8-8cd5-c7e9391f5df3.zip` | `incoming/workspaces/workspace-019ec8fc-4714-7ea8-8cd5-c7e9391f5df3.zip` |
| `workspace-019ec900-e5d8-7d0b-8f7f-06bfa930f6b8.zip` | `incoming/workspaces/workspace-019ec900-e5d8-7d0b-8f7f-06bfa930f6b8.zip` |
| `workspace-019ec90e-7b8f-771d-a00d-3185296ef177.zip` | `incoming/workspaces/workspace-019ec90e-7b8f-771d-a00d-3185296ef177.zip` |
| `workspace-019f0a80-7db2-774d-a895-b7b78e84b065.zip` | `incoming/workspaces/workspace-019f0a80-7db2-774d-a895-b7b78e84b065.zip` |
| `workspace-019f0df1-c9a0-789e-a7d8-5522fd3c47b9.zip` | `incoming/workspaces/workspace-019f0df1-c9a0-789e-a7d8-5522fd3c47b9.zip` |
| `workspace-019f0e7b-20a8-74f8-9860-04f3e01cfba6.zip` | `incoming/workspaces/workspace-019f0e7b-20a8-74f8-9860-04f3e01cfba6.zip` |
| `workspace-019f0e81-c647-75b4-be2e-6a46e3112feb.zip` | `incoming/workspaces/workspace-019f0e81-c647-75b4-be2e-6a46e3112feb.zip` |
| `workspace-019f130a-724f-7704-ba1a-34a0d7e6751c.zip` | `incoming/workspaces/workspace-019f130a-724f-7704-ba1a-34a0d7e6751c.zip` |
| `workspace-019f17c5-d46b-747c-b61a-3063f6b66c9e.zip` | `incoming/workspaces/workspace-019f17c5-d46b-747c-b61a-3063f6b66c9e.zip` |
| `workspace-019f1abe-63ed-7bf8-8672-4b4e43469fbb.zip` | `incoming/workspaces/workspace-019f1abe-63ed-7bf8-8672-4b4e43469fbb.zip` |
| `workspace-019f2d39-403b-74c2-8d28-d5c9092c995d.zip` | `incoming/workspaces/workspace-019f2d39-403b-74c2-8d28-d5c9092c995d.zip` |
| `workspace-019fbf6f-ebc8-7681-8e4a-d74065ead8f7.zip` | `incoming/workspaces/workspace-019fbf6f-ebc8-7681-8e4a-d74065ead8f7.zip` |
| `workspace-019fbfd8-78ab-7a76-bc1f-8b5071be58f8.zip` | `incoming/workspaces/workspace-019fbfd8-78ab-7a76-bc1f-8b5071be58f8.zip` |
| `cryptomonopoly-webxdc/README.md` | `projects/cryptomonopoly-webxdc/README.md` |
| `cryptomonopoly-webxdc/css/style.css` | `projects/cryptomonopoly-webxdc/css/style.css` |
| `cryptomonopoly-webxdc/dist/Cryptomonopoly.xdc` | `projects/cryptomonopoly-webxdc/dist/Cryptomonopoly.xdc` |
| `cryptomonopoly-webxdc/icon.png` | `projects/cryptomonopoly-webxdc/icon.png` |
| `cryptomonopoly-webxdc/js/app.js` | `projects/cryptomonopoly-webxdc/js/app.js` |
| `cryptomonopoly-webxdc/js/board.js` | `projects/cryptomonopoly-webxdc/js/board.js` |
| `cryptomonopoly-webxdc/js/engine.js` | `projects/cryptomonopoly-webxdc/js/engine.js` |
| `cryptomonopoly-webxdc/test/dom.test.js` | `projects/cryptomonopoly-webxdc/test/dom.test.js` |
| `cryptomonopoly-webxdc/test/engine.test.js` | `projects/cryptomonopoly-webxdc/test/engine.test.js` |
| `cypher-decode/README.md` | `projects/cypher-decode/README.md` |
| `cypher-decode/decode_cmb.py` | `projects/cypher-decode/decode_cmb.py` |
| `demoscene-introz/README.md` | `projects/demoscene-introz/README.md` |
| `demoscene-introz/index.html` | `projects/demoscene-introz/index.html` |
| `presskit-reassembler/README.md` | `projects/presskit-reassembler/README.md` |
| `presskit-reassembler/dist/JDK_VIA_NPM.md` | `projects/presskit-reassembler/dist/JDK_VIA_NPM.md` |
| `presskit-reassembler/dist/README.md` | `projects/presskit-reassembler/dist/README.md` |
| `presskit-reassembler/dist/gfx/boot.gif` | `projects/presskit-reassembler/dist/gfx/boot.gif` |
| `presskit-reassembler/dist/gfx/gen_gfx.py` | `projects/presskit-reassembler/dist/gfx/gen_gfx.py` |
| `presskit-reassembler/dist/gfx/icon.png` | `projects/presskit-reassembler/dist/gfx/icon.png` |
| `presskit-reassembler/dist/gfx/intro.gif` | `projects/presskit-reassembler/dist/gfx/intro.gif` |
| `presskit-reassembler/dist/gfx/intro.txt` | `projects/presskit-reassembler/dist/gfx/intro.txt` |
| `presskit-reassembler/dist/java/PressKitServer.java` | `projects/presskit-reassembler/dist/java/PressKitServer.java` |
| `presskit-reassembler/dist/java/build.sh` | `projects/presskit-reassembler/dist/java/build.sh` |
| `presskit-reassembler/dist/java/presskit-reassembler.jar` | `projects/presskit-reassembler/dist/java/presskit-reassembler.jar` |
| `presskit-reassembler/dist/make_packages.sh` | `projects/presskit-reassembler/dist/make_packages.sh` |
| `presskit-reassembler/dist/qbasic/INTRO.TXT` | `projects/presskit-reassembler/dist/qbasic/INTRO.TXT` |
| `presskit-reassembler/dist/qbasic/PRESSKIT.BAS` | `projects/presskit-reassembler/dist/qbasic/PRESSKIT.BAS` |
| `presskit-reassembler/dist/qbasic/build/build_runner.py` | `projects/presskit-reassembler/dist/qbasic/build/build_runner.py` |
| `presskit-reassembler/dist/qbasic/build/runner.template.html` | `projects/presskit-reassembler/dist/qbasic/build/runner.template.html` |
| `presskit-reassembler/dist/qbasic/qbasic-runner.html` | `projects/presskit-reassembler/dist/qbasic/qbasic-runner.html` |
| `presskit-reassembler/dist/war/presskit-reassembler.war` | `projects/presskit-reassembler/dist/war/presskit-reassembler.war` |
| `presskit-reassembler/dist/webxdc/presskit-reassembler.xdc` | `projects/presskit-reassembler/dist/webxdc/presskit-reassembler.xdc` |
| `presskit-reassembler/presskit-reassembler.html` | `projects/presskit-reassembler/presskit-reassembler.html` |
| `presskit-reassembler/wasm/build_dos_stub.py` | `projects/presskit-reassembler/wasm/build_dos_stub.py` |
| `presskit-reassembler/wasm/presskit.wasm` | `projects/presskit-reassembler/wasm/presskit.wasm` |
| `presskit-reassembler/wasm/presskit.wat` | `projects/presskit-reassembler/wasm/presskit.wat` |
| `retro-media-doc/README.md` | `projects/retro-media-doc/README.md` |
| `retro-media-doc/chapters/arcade.html` | `projects/retro-media-doc/chapters/arcade.html` |
| `retro-media-doc/chapters/ctf.html` | `projects/retro-media-doc/chapters/ctf.html` |
| `retro-media-doc/chapters/eggs.html` | `projects/retro-media-doc/chapters/eggs.html` |
| `retro-media-doc/chapters/gamewizard.html` | `projects/retro-media-doc/chapters/gamewizard.html` |
| `retro-media-doc/chapters/presskit.html` | `projects/retro-media-doc/chapters/presskit.html` |
| `retro-media-doc/chapters/scene.html` | `projects/retro-media-doc/chapters/scene.html` |
| `retro-media-doc/css/style.css` | `projects/retro-media-doc/css/style.css` |
| `retro-media-doc/index.html` | `projects/retro-media-doc/index.html` |
| `retro-media-doc/js/chip.js` | `projects/retro-media-doc/js/chip.js` |
| `retro-media-doc/js/nav.js` | `projects/retro-media-doc/js/nav.js` |
| `retro-media-doc/js/stage.js` | `projects/retro-media-doc/js/stage.js` |
| `tbfence-re/.gitignore` | `projects/tbfence-re/.gitignore` |
| `tbfence-re/ANALYSIS.md` | `projects/tbfence-re/ANALYSIS.md` |
| `tbfence-re/README.md` | `projects/tbfence-re/README.md` |
| `tbfence-re/analyze_dos.py` | `projects/tbfence-re/analyze_dos.py` |
| `tbfence-re/ghidra_decompile_all.py` | `projects/tbfence-re/ghidra_decompile_all.py` |
| `tbfence-re/run.sh` | `projects/tbfence-re/run.sh` |
| `The-Secret-Codes-of-CYPHER-Operation-Wildlife_DOS_EN.zip.xml` | `retro-dos/cypher-operation-wildlife-dos-en.zip` |
| `t-ide211.zip` | `retro-dos/t-ide211.zip` |
| `t-sec104.zip.xml` | `retro-dos/t-sec104.zip` |
| `tbfence4.zip.xml` | `retro-dos/tbfence4.zip` |
| `thecoder.zip.xml` | `retro-dos/thecoder.zip` |
| `tinyaes.zip.xml` | `retro-dos/tinyaes.zip` |
| `tinycr11.zip.xml` | `retro-dos/tinycr11.zip` |
| `tinyfish.zip.xml` | `retro-dos/tinyfish.zip` |
| `tops9720.zip` | `retro-dos/tops9720.zip` |
| `track.zip` | `retro-dos/track.zip` |
| `cyberchef.html` | `webxdc/cyberchef/index.html` |
| `shamir.xdc` | `webxdc/shamir/dist/shamir.xdc` |
