# Research findings — shdwelf repos, PR #2 "missing blanks", and the Sneakers kit

Session branch: `arena/01a07c7b-html5-sync-incoming` · repo: `Html5-sync-incoming`

## 1. What is on github.com/shdwelf (scanned 2026-09-07)
The org contains **three** public repositories. All `main` contents (and every
branch of each) were enumerated.

| Repo | Description | Notes |
|---|---|---|
| `Html5` | webxdc "Apps" | `godseye.html`, `greeran-book*.html`, `cylinder-sync.html`, `dalton-race-4dwm.html`, `keyspace.html`, `terrarium.html`, `art-studio.html`, `haiku.*`, `validator.html`, `manifest.*` … plus 18 `arena/*` branches. |
| `bip39-haiku-workbench` | Haiku mnemonic workbook | HTML workbooks + a Vite/TypeScript project. |
| `Html5-sync-incoming` | (this repo) | ~80 loose `.html`/`.zip` sync dump files (GEDCOM visualizers, CyberChef, crypto/haiku wallets, prior-session `workspace-*.zip` exports). |

The much-referenced **Sneakers press-kit / WASM DOS loader work lives in a PR**,
not on any `main` branch:

- **PR #2 in `shdwelf/Html5`** — "x86:LE:16:Real Mode — WASM DOS Binary Loader &
  Sneakers Analysis", from branch `arena/01a02664-html5`, currently **open**.
  Files: `index.html`, `dos_loader.wat`, `dos_loader.wasm`, `webxdc-dos/…`
  (Vite + js-dos DOSBox project), `SNEAKERS.EXE`/`.DAT`/`.ZIP` reconstruction,
  and `webxdc-dos/public/roms/README_SNEAKERS.md` (780-line analysis report).

## 2. "The missing blanks" in PR #2 — what is actually unfinished there
From a full read of `README_SNEAKERS.md`, the reconstruction is self-documented
as a *hand-crafted, WASM-safe subset* — **not** a byte-faithful recovery of the
original 1992 floppy. The concrete gaps ("blanks") it records:

1. **The original media was never ingested.** archive.org TLS was egress-blocked
   in the sandbox that produced PR #2, so the real `sneakers.img` (1,474,560 B =
   1440 KiB FAT12) and `Sneakers_Promotional_Diskette.zip` (2,066,643 B, filecount 2)
   were never downloaded. Only metadata + the bencoded torrent fetched. (§19)
2. **Reconstruction is additive/invented where the source couldn't be checked.**
   The report states hidden messages it added are "consistent with" — not proven
   from — the original; sizes/headers are inferred from archive metadata, not hexdump. (§19.4)
3. **PCX images are placeholders** — 907 B minimal valid headers with a 10-byte RLE
   stub + a palette ramp, not the real 320×200 rasters/photos. (§14)
4. **Vigenère cipher is "documented, stubbed"** — not implemented. (§12)
5. **The original ZIP's two inner files were never extracted** (presumed raw
   `sneakers.img` + README/INSTALL). (§19.2)

## 3. Scope decision made for this session
Reproducing the actual **Universal Pictures 1992 promotional copy** (verbatim cast
bios, plot synopsis, production notes) and packaging it as a reassembled press kit
would be reproducing a film studio's copyrighted promotional material wholesale —
so that specific "blank-filling" is **out of scope** regardless of how much is
"missing."

What **is** delivered instead (in `presskit-reassembler/`): an **original** HTML5
tool that reassembles a classic DOS press-kit program from **user-supplied text**
using an embedded WebAssembly cipher engine — the same engineering idea as PR #2,
without reproducing anyone's studio copy. Default content is original placeholder
text, and the tool is explicitly labelled non-official.

## 4. Genealogical / GEDCOM research — status
Not continued this session for lack of an input, not because it's blocked:
- No actual `.ged` dataset or `.ged`-style record file is present in this repo
  (only GEDCOM *visualizer apps*), and no specific living/deceased research target
  was provided.
- The repo does show an active **Greeran** genealogy line
  (`Greeran_COMPLETE_BREAKTHROUGH_Final.html`, `Greeran_Military_Service_Map.html`,
  `Greeran_Seize_Quartiers_Session8_Final.html`).

**To continue:** provide (a) the specific person/family + era to research and
(b) the data source (a `.ged` file, or which of the above HTML files to mine).
Public-genealogy of deceased ancestors is fine to work on; identifiable
living-person profiles are handled with care (structure/visualization only).
