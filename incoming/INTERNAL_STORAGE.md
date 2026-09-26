# `internal-storage.7z` — classification

Was **REPO-3 (MED, open)** in [../REVIEW.md](../REVIEW.md): the largest object in
the repo and the only one whose contents nobody could name. Resolved 2026-09-19
by indexing it instead of unpacking it.

| | |
|---|---|
| SHA-256 | `705743b8fdc5076e40a9d7c69c9b3e3e80416a526c67d2ce86db42364739d283` |
| Packed / unpacked | 6,236,510 bytes / 104,024,159 bytes |
| Entries | 302, all files, no directories, no paths (flat) |
| Distinct payloads | 265 — 37 of the 302 are copies of another entry in the same archive |
| Extensions | `.html` × 301, `.old` × 1 (`index.html.old`, a save-backup whose bytes are still a complete HTML app) |
| Entry mtimes | 1980-01-02 → 2026-08-01 (40 carry the 1980 filler stamp, 262 are real) |
| Index | [internal-storage.index.tsv](internal-storage.index.tsv) — 302 rows: `sha256 bytes mtime path title` |

## What it is

The **working directory the root-level exports were downloaded from**, not another
app source. That is no longer an inference: 20 entries are byte-identical to
files already classified under `apps/`, so the archive is provably the same corpus
the loose `index (N).html` / `crypto-recovery-os-*` / `netscope*` files came out
of. Those 20 rows double as independent confirmation of the rename map in
[../INVENTORY.md](../INVENTORY.md#rename-map) — including the judgement calls on
collision-junk names:

| entry inside the archive | byte-identical to |
|---|---|
| `index (1) (1).html` | `apps/misc/hacker-dice-8ball-3d.html` |
| `index (2).html` | `apps/misc/hacker-dice-8ball-2d.html` |
| `index (56).html` | `apps/crypto/banano-paper-wallet-generator.html` |
| `netscope.html` | `apps/network/netscope-v2.html` |
| `netscope (2).html` | `apps/network/netscope-v5.html` |
| `crypto-recovery-os-offline.html` | `apps/crypto/crypto-recovery-os-offline.html` |
| `crypto-recovery-os-standalone.html` | `apps/crypto/crypto-recovery-os-standalone-r1.html` |
| `crypto-recovery-os-standalone (1).html` | `apps/crypto/crypto-recovery-os-standalone-r2.html` |
| `generator.offline.repaired (1).html` | `apps/crypto/banano-paper-wallet-generator-offline.html` |
| `gedcom_tsp_final_inline.html` | `apps/genealogy/gedcom-tsp-visualizer-r1.html` |
| `gedcom_tsp_final_inline (1).html` | `apps/genealogy/gedcom-tsp-visualizer-r2.html` |
| `Resume.html` | `apps/genealogy/greeran-resume-portfolio.html` |
| `Greeran_Military_Service_Map.html` | `apps/genealogy/greeran-military-service-map.html` |
| `Greeran_COMPLETE_BREAKTHROUGH_Final.html` | `apps/genealogy/greeran-seize-quartiers-breakthrough.html` |
| `Greeran_Seize_Quartiers_Session8_Final.html` | `apps/genealogy/greeran-seize-quartiers-session8.html` |
| `seize_quartiers_quine_2026-07-20T12-30-45.html` | `apps/genealogy/seize-quartiers-quine-2026-07-20.html` |
| `image-encyclopedia-quine.html` | `apps/media/image-format-encyclopedia-quine.html` |
| `censorbench.html` | `apps/misc/censorbench.html` |
| `index.offline.repaired.html` | `apps/misc/membershub-private-app-store.html` |
| `zip_offline_viewer.html` | `apps/misc/zip-offline-audit-viewer.html` |

## The other 282

`--report` collapses each filename to the app it belongs to (`family()` in
[index_internal_storage.py](index_internal_storage.py): collision counters, epoch-ms
stamps and ISO timestamps mark *builds of one app*, not apps). Counted over the 282
entries with no twin in the tree, the 16 largest families are:

| builds | MB | dates | family | recovered title |
|---|---|---|---|---|
| 68 | 1.9 | 1980→2026-07-16 | `index (N).html` | 43 distinct titles — Ensō haiku wallets, Cryptopoly, Bananocoin miner… |
| 17 | 12.1 | 2026-07-16→08-01 | `seize-quartiers-quine-*` | Seize Quartiers — family-tree visualisation |
| 16 | 21.8 | 2026-06-17→06-19 | `cybervault-*` | The Vault — Members Only |
| 10 | 5.8 | 1980→2026-07-12 | `generator.offline.repaired (N)` | Banano Paper Wallet Generator |
| 9 | 7.6 | 2026-07-27→08-01 | `cipher-machines-and-cryptology-*` | Cipher Machines & Cryptology simulator |
| 8 | 5.9 | 2026-06-21→06-22 | `multitool-app-quine` / `hyper-portal-*` | Hyper-Portal HTML5 Multitool |
| 8 | 3.1 | 2026-06-21 | `patent-office-*` | Patent Office Secret Bookshelf |
| 6 | 6.2 | 2026-06-23→06-24 | `hyper-portal-2.27.0-piped-installer` | Hyper-Portal Multitool (installed-build variant) |
| 4 | 6.2 | 2026-07-04 | `sanborn-codex (N).html` | Sanborn Codex |
| 4 | 1.4 | 2026-07-04 | `noise-canceling-sanctuary-*` | Noise Canceling Sanctuary |
| 4 | 0.2 | 1980-01-02 | `secops-purple-team-suite-*` | Purple Team Training Suite |

By title, the archive holds **129** distinct apps, of which **120** have no
representation anywhere in `apps/`: they are superseded revisions of things that
were promoted, or builds that were never promoted at all. Promoting them is not a
reorganisation task — every one of those 120 would need the same `<title>`-based
naming, dedupe and "is this the good build" review that `INVENTORY.md` records for
the 20 apps in `apps/`, and 37 more entries are copies of each other.

Four entries are not documents at all, which is worth knowing before anyone
"fixes" them by opening them in a browser:

| entry | bytes | what it actually is |
|---|---|---|
| `Haikuie.html` | 0 | empty |
| `patent_office_standalone_2026-06-21T12-24-47.html` | 0 | empty — a save that never completed |
| `ndx.js.html` | 25,352 | a *fragment*: inline `<script>` bodies extracted from a page, no `<html>` wrapper |
| `variables.html` | 234 | a *fragment*: the text of the Ensō brush-variables panel, markup stripped |

## Why it stays one archive

Unpacking 302 files into `incoming/` would add 104 MB of loose HTML — 17× the
archive's own size — and the whole tree would gain 302 files whose names are
`index (13).html`. The classification problem was never "the archive is packed",
it was "nobody can say what is in it". That is solved by the TSV: it is
grep-friendly, diff-friendly, reviewable without 7z tooling, and it is the reason
`sha256` is column 1 (find an entry in the index, you can prove whether any file
on disk matches it).

If the repo ever decides it *does* want the sources, the rule to follow is the one
`INVENTORY.md` uses: one directory per app, title-derived names, `-rN` where the
bytes genuinely differ.

## Reproducing or refreshing

```bash
pip install py7zr          # dev-only; nothing in this repo depends on it at build time
python3 incoming/index_internal_storage.py --report     # regenerate + print the analysis above
python3 incoming/index_internal_storage.py --check      # exit 1 if the committed TSV is stale
python3 incoming/index_internal_storage.py --dir DIR    # no py7zr: index an extracted copy instead
```

`mtime` per entry comes from the archive's own headers, which is why reading the
`.7z` (rather than an extracted directory) gives 1980-01-02 filler stamps instead
of filesystem dates. Two 1980-01-02 conventions exist in this repo: `workspaces/`
ZIPs are normalised to 1980-01-02 by the sync tool that wrote them, and the
packers in `webxdc/` pin entries to 1980-01-01 (a day apart, so one can never be
mistaken for the other).
