#!/usr/bin/env python3
"""index_internal_storage.py — make `internal-storage.7z` inspectable without a 7z.

REPO-3 (REVIEW.md) was "this 6.2 MB archive is the one unclassified object in
the repo": 302 HTML files, 104 MB unpacked, and no way to see what was in it
without tooling nothing here depends on. This is the missing step: it walks the
archive and writes `internal-storage.index.tsv`, one row per entry, so the
contents are greppable, diffable and reviewable as plain text. The archive stays
the container — 302 more loose files would be a worse tree, not a better one.

  python3 index_internal_storage.py             # needs py7zr: pip install py7zr
  python3 index_internal_storage.py --dir DIR   # or index an already-extracted tree
  python3 index_internal_storage.py --report    # + duplicate/family analysis vs the repo
  python3 index_internal_storage.py --check     # exit 1 if the committed TSV is stale

TSV columns, tab-separated, one row per entry, sorted by path:

    sha256  bytes  mtime  path  <title>

`mtime` is the entry's own timestamp (not the archive's), which is what makes
the rebuild series orderable. `<title>` is the document's own title, decoded
best-effort: it is how `INVENTORY.md` names apps whose filenames were collision
junk like `index (37).html`, and it is the only reliable name inside here.

The 7z is read once and streamed; nothing is written outside the workspace.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
ARCHIVE = os.path.join(HERE, "internal-storage.7z")
INDEX = os.path.join(HERE, "internal-storage.index.tsv")
COLUMNS = ("sha256", "bytes", "mtime", "path", "title")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def read_title(path):
    """Best-effort <title>. Only the first 256 KB is read: every document here
    declares its title in the head, and some of these files are 5 MB quines."""
    try:
        with open(path, "rb") as fh:
            head = fh.read(1 << 18)
    except OSError:
        return ""
    m = re.search(rb"<title[^>]*>(.*?)</title>", head, re.S | re.I)
    if not m:
        return ""
    t = re.sub(rb"\s+", b" ", m.group(1)).decode("utf-8", "replace").strip()
    return t.replace("\t", " ")


def iter_entries(archive):
    """Yield (name, mtime_iso, tmpdir) by extracting the archive once.

    7z blocks are usually solid: re-reading one entry means decompressing the
    whole archive, so `read()` per entry is O(n^2) here and extraction is not."""
    import shutil
    import tempfile
    import py7zr

    tmp = tempfile.mkdtemp(prefix="internal-storage-")
    try:
        with py7zr.SevenZipFile(archive) as z:
            mtimes = {e.filename: e.creationtime for e in z.list()}
            z.extractall(tmp)
        for base, _, files in os.walk(tmp):
            for f in sorted(files):
                full = os.path.join(base, f)
                rel = os.path.relpath(full, tmp).replace(os.sep, "/")
                dt = mtimes.get(rel)
                yield rel, (dt.strftime("%Y-%m-%d") if dt else ""), full
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def iter_dir(root):
    for base, _, files in os.walk(root):
        for f in sorted(files):
            full = os.path.join(base, f)
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            yield rel, "", full


def family(path):
    """Collapse an export filename to the app it belongs to.

    These names are sync-tool output: collision counters, millisecond stamps,
    ISO timestamps, `-rN`/`-vN` revision tags and underscore/dash drift all mark
    *builds of one app*, not different apps — the same rule INVENTORY.md applies
    to the classified tree."""
    stem = os.path.basename(path)
    stem = re.sub(r"\.(html?|htm)$", "", stem, flags=re.I)
    stem = re.sub(r"\s*\(\d+\)", "", stem)                   # browser collision " (3)"
    stem = re.sub(r"[-_]\d{13}", "", stem)                    # epoch-ms stamp
    stem = re.sub(r"[-_]\d{4}-\d{2}-\d{2}([T_]\d\d-\d\d(-\d\d)?)?", "", stem)
    stem = re.sub(r"[-_]v?\d+$", "", stem)                    # trailing revision
    stem = re.sub(r"(?:[-_.]?)(?:final|fixed|optimized|repaired|standalone|offline|working|latest|copy|new|old|copy\d*|v\d+)(?=[-_.]|$)",
                  "", stem, flags=re.I)
    stem = re.sub(r"[^a-z0-9]+", "-", stem.lower()).strip("-")
    return stem or "untitled"


def build_index(source, use_archive):
    """Rows sorted by path, so the TSV is stable and its diff is only ever content."""
    it = iter_entries(source) if use_archive else iter_dir(source)
    rows = [{
        "sha256": sha256_file(full),
        "bytes": os.path.getsize(full),
        "mtime": mtime or fs_mtime(full),
        "path": name,
        "title": read_title(full),
    } for name, mtime, full in it]
    rows.sort(key=lambda r: r["path"].lower())
    return rows


def fs_mtime(path):
    import datetime
    return datetime.date.fromtimestamp(os.path.getmtime(path)).isoformat()


def write_index(rows, out):
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\t".join(COLUMNS) + "\n")
        for r in rows:
            fh.write("\t".join(str(r[c]) for c in COLUMNS) + "\n")
    return out


def repo_hashes():
    """sha256 -> repo-relative path, for every tracked-ish file outside incoming/."""
    out = {}
    for base, dirs, files in os.walk(REPO):
        dirs[:] = [d for d in dirs if d not in (".git", "node_modules", "__pycache__", "incoming")]
        for f in files:
            full = os.path.join(base, f)
            if os.path.getsize(full) == 0:
                continue
            out.setdefault(sha256_file(full), os.path.relpath(full, REPO).replace(os.sep, "/"))
    return out


def report(rows):
    dup_in = collections.Counter(r["sha256"] for r in rows)
    internal_dupes = sum(v - 1 for v in dup_in.values() if v > 1)
    print(f"{len(rows)} entries, {sum(r['bytes'] for r in rows):,} unpacked bytes, "
          f"{len(dup_in)} distinct payloads ({internal_dupes} redundant copies inside the archive)")

    rh = repo_hashes()
    hits = [r for r in rows if r["sha256"] in rh]
    print(f"\nbyte-identical to a file already classified in the tree: {len(hits)}")
    for r in sorted(hits, key=lambda r: rh[r["sha256"]]):
        print(f"    {r['path'][:56]:58s} -> {rh[r['sha256']]}")
    print(f"\n{len(rows) - len(hits)} entries have no twin in the tree.")

    fam = collections.Counter(family(r["path"]) for r in rows)
    multi = [(k, v) for k, v in fam.most_common() if v > 1]
    print(f"\n{len(fam)} distinct apps; {len(multi)} of them exist as several builds:")
    for k, v in multi[:22]:
        sample = next(r["title"] for r in rows if family(r["path"]) == k and r["title"])
        print(f"    {v:3d} x  {k[:34]:36s} {sample[:52]}")
    singles = [k for k, v in fam.items() if v == 1]
    print(f"    ... and {len(singles)} single-build apps")

    stamps = sorted(r["mtime"] for r in rows if r["mtime"])
    if stamps:
        print(f"\nentry mtimes span {stamps[0]} -> {stamps[-1]}"
              f" ({len(stamps)} dated entries)")
    titled = sum(1 for r in rows if r["title"])
    print(f"titles recoverable for {titled}/{len(rows)} entries; "
          f"{len(rows) - titled} have no <title> tag (truncated or non-HTML payloads).")
    empty = [r["path"] for r in rows if r["bytes"] == 0]
    if empty:
        print(f"empty files: {len(empty)} — {', '.join(empty[:6])}")
    return len(hits)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Index or verify `internal-storage.7z`.",
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--archive", default=ARCHIVE)
    ap.add_argument("--dir", help="index an extracted tree instead of the .7z (no py7zr needed)")
    ap.add_argument("--report", action="store_true", help="also print the dedupe/family analysis")
    ap.add_argument("--check", action="store_true", help="exit 1 if the committed TSV is stale")
    ap.add_argument("--out", default=INDEX)
    args = ap.parse_args(argv)

    if args.dir:
        rows = build_index(args.dir, use_archive=False)
    else:
        if not os.path.isfile(args.archive):
            sys.exit(f"error: no archive at {args.archive}")
        try:
            import py7zr  # noqa: F401
        except ImportError:
            sys.exit("error: reading a .7z needs py7zr (pip install py7zr), or pass --dir DIR "
                     "pointing at an already-extracted copy of the archive.")
        rows = build_index(args.archive, use_archive=True)

    body = "\t".join(COLUMNS) + "\n" + "".join(
        "\t".join(str(r[c]) for c in COLUMNS) + "\n" for r in rows)
    if args.check:
        if not os.path.isfile(args.out):
            print(f"[MISSING] {os.path.relpath(args.out, REPO)} — run: python3 index_internal_storage.py")
            return 1
        if open(args.out, encoding="utf-8").read() == body:
            print(f"[OK] internal-storage.index.tsv matches the archive ({len(rows)} rows)")
            return 0
        print(f"[DRIFT] internal-storage.index.tsv is stale ({len(rows)} entries now)")
        return 1
    if args.dir:
        print("note: --dir carries no per-entry mtimes; the mtime column uses filesystem dates")
    write_index(rows, args.out)
    print(f"wrote {os.path.relpath(args.out, REPO)} — {len(rows)} rows, "
          f"{sum(r['bytes'] for r in rows):,} bytes of content indexed")
    if args.report:
        print()
        report(rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
