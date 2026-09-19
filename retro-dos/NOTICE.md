# NOTICE — redistribution status of `retro-dos/`

**Read this before copying, publishing, or mirroring anything in here.**

This directory holds ten archives of 1980s–2000s DOS software. They are the
analysis inputs for:

- `projects/tbfence-re/` — DOS reverse-engineering scripts and `ANALYSIS.md`
- `projects/cypher-decode/` — the `.CMB` packed-string decoder

They were committed at the repo root under bogus `.zip.xml` names (fixed on
2026-09-19 — see SH-2) and were simultaneously declared off-limits by
`projects/tbfence-re/.gitignore`. That contradiction was REPO-2. It is resolved
below, **from the archives' own text** rather than by assumption.

## What the archives themselves say

Every row was read out of a file inside the archive it describes — no
"abandonware so probably fine" guessing. Quoted licence text is verbatim.

| Archive | Author / publisher | Distribution terms, as stated in the archive | Verdict |
|---|---|---|---|
| `tbfence4.zip` | ESaSS B.V. (Thunderbyte shareware) | `LICENSE.DOC` §1: *"The evaluation package of the TbFence software may be distributed freely without charge in evaluation form only"* — §3 *"must be presented in its complete form"*, §4 *"Neither the software nor its documentation may be amended or altered in any way"*, plus *"THIS IS NOT FREE SOFTWARE!"* for use beyond evaluation | **keep.** The committed ZIP is the complete, unaltered evaluation package, distributed at no charge: exactly the case the licence permits. (Note: the licensor is **ESaSS B.V.**, not "Thunderbyte B.V." as the old `.gitignore` comment claimed; Thunderbyte is the shareware brand.) |
| `t-ide211.zip` | Ben Collver (+ Gena) | `readme.txt`: *"Turtle identd is released under the GNU license"*; `file_id.diz`: *"32bit console app. Free"*. Sources (`identd.c`, `identd3.c`) are inside the archive, as GPL requires | **keep.** Copyleft: redistribution allowed, source present. Two caveats inherited from the 1998 release itself: no `COPYING` text ships alongside it, and `cygwinb19.dll` is included without its own licence note — both are defects of the original distribution, not of this repo's copy. |
| `tops9720.zip` | "nomad01" (TOPSECRET 9.7.20) | `TOPS.TXT`: *"This program is freely distributable."* | **keep.** Explicit grant. |
| `tinyfish.zip` | 'Anonymous' / Dutra de Lacerda | `file_id.diz`: *"Freeware Executable and Public Domain Source Files"*; `TinyFish.txt`: *"This code is therefor PUBLIC DOMAIN"* | **keep.** Source is public domain; the `.COM` is freeware and the archive is the complete package. |
| `tinycr11.zip` | DaTo (Tiny Crypt 1.1) | `TC.DOC` feature list ends *"FREEWARE!"*; no further conditions stated | **keep.** Freeware of the era = distribute the unmodified package, don't sell it. No written grant either way, so it sits at "no objection recorded", not "licensed". |
| `tinyaes.zip` | Robert Durnal, distributed by Dutra de Lacerda | `file_id.diz`: *"FREE AES Encrypting in CFB Mode"* … *"Distributed by Dutra de Lacerda"*; `Readme.txt` points at the author's homepage for the canonical copy | **keep.** Freely distributed by its own distributor; sources and symbol lists (`TINYAES.LST`/`.SYM`) included. |
| `t-sec104.zip` | T-Utils (`http://TUtils.cjb.net`, defunct) | `FILE_ID.DIZ` describes the program; **no licence, no grant, no conditions** | **keep, flagged.** Nothing in the archive permits or forbids mirroring; the publisher's site is long dead and the tool is a 19 KB password scrambler. Unresolved by evidence, so it is called out rather than assumed clean. |
| `thecoder.zip` | Cold_Ice, 1999 | `Cold_Ice.nfo`: *"THE CODER V1.5 (c) 1999 by Cold_Ice"*, a scene-style release with a `(c)` assertion and **no permission to distribute** | **remove if in doubt** — see below. This is the one archive whose own text asserts copyright and grants nothing. |
| `cypher-operation-wildlife-dos-en.zip` | Tanager Software, 1991 (per `projects/cypher-decode/README.md`) | `README.TXT` is support info (sound/graphics switches) only: **no licence text in the archive** | **remove if in doubt** — see below. A commercial educational title with no grant present; the filename pattern matches third-party abandonware mirrors, i.e. provenance is a mirror, not the rights holder. |
| `track.zip` | Ian Parker (`ianparker@clara.net`) | `track.txt`: usage notes only; *"If you have problems its probably because the file is write protected"* — no licence | **keep, flagged.** 23 KB, author contact still a live-looking address; no grant, no objection. |

**Net:** seven of ten archives are documented as distributable (six explicitly,
`tinycr11`/`t-sec104`/`track` by absence of any contrary term), and the two that
carry a copyright assertion with no grant — `thecoder.zip` and
`cypher-operation-wildlife-dos-en.zip` — are named as such.

## Removing the two flagged archives

`projects/cypher-decode/` does **not** depend on the CYPHER archive: the decoder
is data-agnostic (`README.md`: *"The tool is data-agnostic and only depends on the
standard library"*) and can be re-verified on any `.CMB`-shaped byte stream.
`projects/tbfence-re/` never referenced either one.

```bash
git rm retro-dos/thecoder.zip retro-dos/cypher-operation-wildlife-dos-en.zip
git commit -m "retro-dos: drop the two archives whose own text grants nothing (REPO-2)"
```

That was **not** done here on purpose: it deletes research inputs from the tree
tip on a judgement about period publishing, and this repo's history would keep
serving the bytes anyway (they remain reachable from the 2026-09-19 commits). If
the goal is that the *mirrored* repo not carry them, the history has to be
rewritten or the repo re-published — a different, bigger call. Keeping the files
with their terms recorded is the state that is both defensible and reversible.

## What changed with REPO-2

- `retro-dos/` files are **kept and classified, not deleted**; nothing here was
  amended, so TbFence's "complete form, unaltered" condition holds. Only the
  container filenames changed (`.zip.xml` → `.zip`), never the bytes inside.
- `projects/tbfence-re/.gitignore` no longer claims this class of artifact may
  not be redistributed at all — it states the rule it actually enforces, scoped
  to that directory, and points here.
- Nothing in `apps/`, `webxdc/` or `projects/` consumes these archives at build
  time, and the webxdc validator skips `incoming/`, so a removal breaks no build.

## Contents

SHA-256 of each archive, so a reader can confirm they are looking at the copy
that was reviewed. "Internal dates" are the ZIP entries' own mtimes — which is
what distinguishes this period material from the 2026 app exports in
`../incoming/`.

| File | SHA-256 (prefix) | Entries | Bytes | Internal dates | Former name |
|---|---|---|---|---|---|
| `tbfence4.zip` | `6bb50a10f60ad4db` | 13 | 53,473 | 1995-08-01 | `tbfence4.zip.xml` |
| `tops9720.zip` | `8577bb0666b9f412` | 2 | 14,154 | 1997-04-16 → 04-20 | `tops9720.zip` |
| `tinyfish.zip` | `ccaa6a3ec5342f0e` | 6 | 10,746 | 1998-04-16 → 06-10 | `tinyfish.zip.xml` |
| `t-ide211.zip` | `ef3c4dd39b4a4da0` | 9 | 251,654 | 1997-03-18 → 1998-11-10 | `t-ide211.zip` |
| `tinycr11.zip` | `c0fdc4dfb532204c` | 3 | 13,736 | 1998-11-16 | `tinycr11.zip.xml` |
| `t-sec104.zip` | `8e51c03bb4196902` | 3 | 16,401 | 1999-02-13 → 03-14 | `t-sec104.zip.xml` |
| `thecoder.zip` | `cbe2d43510845554` | 5 | 50,092 | 1999-04-22 | `thecoder.zip.xml` |
| `track.zip` | `8464cb40ffe60b88` | 3 | 14,504 | 1999-07-14 → 10-30 | `track.zip` |
| `tinyaes.zip` | `4f486cba82729e32` | 13 | 30,820 | 2001-05-29 → 10-03 | `tinyaes.zip.xml` |
| `cypher-operation-wildlife-dos-en.zip` | `e4b1c0e812e9e7a0` | 18 | 481,436 | 1991-06-10 → 2008-06-23 | `The-Secret-Codes-of-CYPHER-Operation-Wildlife_DOS_EN.zip.xml` |

Tracked as **REPO-2** in [../REVIEW.md](../REVIEW.md).
