# NOTICE — redistribution status of this directory is unresolved

**Read this before copying, publishing, or mirroring anything in `retro-dos/`.**

This directory holds ten archives of 1980s–2000s DOS software, including what
appear to be Thunderbyte B.V. shareware (TbFence / ThunderBYTE Fence) and PC-SIG
disc material such as *The Secret Codes of CYPHER: Operation Wildlife*. They are
the analysis inputs for:

- `projects/tbfence-re/` — DOS reverse-engineering scripts and `ANALYSIS.md`
- `projects/cypher-decode/` — the `.CMB` packed-string decoder

## The conflict

`projects/tbfence-re/.gitignore` states the repo's own policy, verbatim:

```
# TbFence binaries are 1990s shareware (Thunderbyte B.V.). They are analyzed
# locally but NOT committed here (that would redistribute the shareware).
_src/
analysis/
*.exe
*.com
*.sys
*.dat
*.zip
```

That `.gitignore` only applies inside `projects/tbfence-re/`. These ten archives
were committed at the repository **root**, outside its scope, so the `*.zip` and
`*.exe`/`*.com` patterns never matched them. Seven of them were additionally
hidden behind a bogus `.zip.xml` extension, which is one more reason an
extension-based ignore rule would not have caught them.

So the repo simultaneously (a) declares that this class of artifact must not be
redistributed and (b) redistributes ten of them. Whichever half is wrong, the
current state is not defensible, and it is not something a reorganisation should
resolve silently.

## What was NOT done, and why

The files were **moved and classified, not deleted**. Removing them would be an
irreversible decision about someone else's data and research inputs, the analysis
notes in `projects/tbfence-re/ANALYSIS.md` refer to them, and "abandonware from a
defunct 1990s publisher" is a legal judgement, not a cleanup task. Flagging it is
the honest move; guessing is not.

They are also **not** being treated as deliverables: the webxdc validator skips
`incoming/` and nothing in `apps/`, `webxdc/` or `projects/` depends on files
here at build time.

## Options for the owner

1. **Keep them, delete the policy note.** If redistribution is considered fine
   (period shareware, defunct publisher, research use), then
   `projects/tbfence-re/.gitignore` is stating a rule the repo does not follow and
   should say so plainly instead.
2. **Move them out of git.** Private storage, Git LFS with access controls, or a
   documented fetch step. Replace this directory with a manifest of what to
   obtain and from where.
3. **Untrack but keep on disk.** `git rm --cached retro-dos/*.zip` plus a
   directory-scoped `.gitignore`, matching the policy that
   `projects/tbfence-re/.gitignore` already describes.

Option 3 makes the repo consistent with its own stated intent with the least
data loss, and is a one-line change once decided.

Tracked as **REPO-2 (HIGH, open)** in [../REVIEW.md](../REVIEW.md).

## Contents

| File | Internal timestamp | Bytes | Former name |
|------|--------------------|-------|-------------|
| `tbfence4.zip` | 1995-08-01 | 53,473 | `tbfence4.zip.xml` |
| `tops9720.zip` | 1997-04-20 | 14,154 | `tops9720.zip` |
| `tinyfish.zip` | 1998-06-10 | 10,746 | `tinyfish.zip.xml` |
| `t-ide211.zip` | 1998-11-10 | 251,654 | `t-ide211.zip` |
| `tinycr11.zip` | 1998-11-16 | 13,736 | `tinycr11.zip.xml` |
| `t-sec104.zip` | 1999-03-14 | 16,401 | `t-sec104.zip.xml` |
| `thecoder.zip` | 1999-04-22 | 50,092 | `thecoder.zip.xml` |
| `track.zip` | 1999-10-30 | 14,504 | `track.zip` |
| `tinyaes.zip` | 2001-10-03 | 30,820 | `tinyaes.zip.xml` |
| `cypher-operation-wildlife-dos-en.zip` | 2008-06-23 | 481,436 | `The-Secret-Codes-of-CYPHER-Operation-Wildlife_DOS_EN.zip.xml` |

Internal timestamps are the ZIP entries' own mtimes, which is what distinguishes
this period material from the 2026 app exports in `incoming/`.
