#!/usr/bin/env python3
"""webxdc_tool.py — validate and build `.xdc` containers against the spec.

Spec: https://webxdc.org/docs/spec/format.html
  * a webxdc app is a ZIP file with the extension `.xdc`
  * the ZIP MUST use "Deflate" or "Store" compression (RFC 1950)
  * the ZIP MUST contain `index.html`
  * the ZIP MAY contain `manifest.toml` and `icon.png` / `icon.jpg`
  * from `manifest.toml`, `name` and `source_code_url` are the keys that are read
  * `webxdc.js` is provided by the messenger and MUST NOT be inside the package

Usage:
    python3 webxdc_tool.py validate [PATH ...]     # default: whole repo
    python3 webxdc_tool.py pack SRC_DIR OUT.xdc    # deterministic rebuild
    python3 webxdc_tool.py list [PATH ...]         # inventory of every package

Exit status is 1 if any package FAILs, so this can gate a CI job or a pre-push
hook:

    python3 webxdc/webxdc_tool.py validate || exit 1
"""
from __future__ import annotations

import argparse
import io
import os
import struct
import subprocess
import sys
import tomllib
import zipfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Directories never walked when scanning the whole repo. `incoming/` is raw,
# unprocessed sync payload — it deliberately holds mis-packaged artifacts kept
# for provenance (e.g. radar-scope-webxdc-INVALID.zip), so validating them as
# deliverables would be a false positive. Pass --all to include them anyway.
DEFAULT_EXCLUDE = {"incoming", ".git", "node_modules", "__pycache__", "dist"}

SPEC_MANIFEST_KEYS = {"name", "source_code_url"}
# Honourable extras that messenger UIs commonly read. Not in the spec's MUST list
# but harmless — reported as INFO, never as a failure.
EXTRA_MANIFEST_KEYS = {"description", "icon", "min_api"}
ALLOWED_COMPRESSION = {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}
ICON_RANGE = (128, 512)


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def png_size(data: bytes):
    """Return (w, h) for a PNG, or None. Reads IHDR directly — no Pillow needed."""
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    if data[12:16] != b"IHDR":
        return None
    w, h = struct.unpack(">II", data[16:24])
    return w, h


def jpeg_size(data: bytes):
    """Return (w, h) for a baseline/progressive JPEG, or None."""
    if len(data) < 4 or data[:2] != b"\xff\xd8":
        return None
    i = 2
    n = len(data)
    while i + 9 < n:
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
            i += 2
            continue
        seglen = struct.unpack(">H", data[i + 2:i + 4])[0]
        if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB,
                      0xCD, 0xCE, 0xCF):
            h, w = struct.unpack(">HH", data[i + 5:i + 9])
            return w, h
        i += 2 + seglen
    return None


def find_packages(roots, exclude=frozenset()):
    """Every `.xdc` in the repo, plus any file that *claims* to be a webxdc
    package under another name (`.webxdc`, `*webxdc*.zip`) — those are exactly
    the mis-packaged artifacts this tool exists to catch."""
    found = []
    for root in roots:
        if os.path.isfile(root):
            found.append(root)
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in exclude]
            for f in sorted(filenames):
                low = f.lower()
                if low.endswith(".xdc") or low.endswith(".webxdc") or ("webxdc" in low and low.endswith(".zip")):
                    found.append(os.path.join(dirpath, f))
    # stable, de-duplicated
    seen, out = set(), []
    for p in sorted(found):
        rp = os.path.realpath(p)
        if rp not in seen:
            seen.add(rp)
            out.append(p)
    return out


# --------------------------------------------------------------------------
# validate
# --------------------------------------------------------------------------
def validate(path: str):
    """Return (errors, warnings, infos) for one package."""
    err, warn, info = [], [], []
    name = os.path.basename(path)
    rel = os.path.relpath(path, REPO_ROOT)

    if not name.lower().endswith(".xdc"):
        err.append(f"extension is `{os.path.splitext(name)[1] or '(none)'}`; the spec requires `.xdc`")

    if not zipfile.is_zipfile(path):
        err.append("not a ZIP file at all")
        return err, warn, info

    try:
        zf = zipfile.ZipFile(path)
    except Exception as e:
        err.append(f"cannot open ZIP: {e}")
        return err, warn, info

    with zf:
        infos = zf.infolist()
        names = [i.filename for i in infos]

        # -- compression -------------------------------------------------
        bad = {i.filename for i in infos if i.compress_type not in ALLOWED_COMPRESSION}
        if bad:
            err.append(f"compression must be Deflate or Store, got other for: {', '.join(sorted(bad)[:4])}")

        # -- path safety -------------------------------------------------
        for n in names:
            if n.startswith("/") or n.startswith("\\") or ".." in n.replace("\\", "/").split("/") or "\\" in n:
                err.append(f"unsafe or non-portable entry path: {n!r}")
                break

        # -- index.html at root -----------------------------------------
        if "index.html" not in names:
            nested = [n for n in names if n.endswith("index.html")]
            if nested:
                err.append(f"`index.html` is not at the ZIP root (found nested: {nested[0]!r}) — the app will not load")
            else:
                err.append("required entry `index.html` is missing")

        # -- webxdc.js must not be shipped ------------------------------
        if "webxdc.js" in names:
            err.append("`webxdc.js` is inside the package; the spec says the messenger provides it and it must not be added to the .xdc")

        # -- non-spec manifest formats ----------------------------------
        for extra in ("manifest.json", "manifest.xml"):
            if extra in names:
                body = zf.read(extra)[:200]
                kind = "JSON" if body.lstrip()[:1] in (b"{", b"[") else ("XML" if body.lstrip()[:1] == b"<" else "unknown")
                if extra == "manifest.xml" and kind != "XML":
                    err.append(f"`{extra}` is present but contains {kind}, not XML")
                else:
                    warn.append(f"`{extra}` is not part of the webxdc container spec (only `manifest.toml` is) — {len(zf.read(extra))} bytes of dead weight")

        # -- manifest.toml ----------------------------------------------
        if "manifest.toml" in names:
            raw = zf.read("manifest.toml")
            try:
                man = tomllib.loads(raw.decode("utf-8"))
            except Exception as e:
                err.append(f"`manifest.toml` does not parse: {e}")
                man = None
            if isinstance(man, dict):
                if not man.get("name"):
                    err.append("`manifest.toml` has no `name`; the messenger will fall back to the filename")
                if not man.get("source_code_url"):
                    warn.append("`manifest.toml` has no `source_code_url` (recommended — surfaced in the messenger Help menu)")
                unknown = sorted(set(man) - SPEC_MANIFEST_KEYS - EXTRA_MANIFEST_KEYS)
                if unknown:
                    info.append(f"`manifest.toml` carries keys no implementation reads: {', '.join(unknown)}")
        else:
            info.append("no `manifest.toml` — the messenger will use the filename as the app name")

        # -- icon --------------------------------------------------------
        icon = next((n for n in ("icon.png", "icon.jpg") if n in names), None)
        if icon:
            data = zf.read(icon)
            size = png_size(data) if icon.endswith(".png") else jpeg_size(data)
            if size is None:
                err.append(f"`{icon}` is not a valid {'PNG' if icon.endswith('.png') else 'JPEG'}")
            else:
                w, h = size
                if w != h:
                    warn.append(f"`{icon}` is {w}x{h}; the spec asks for a square icon")
                if not (ICON_RANGE[0] <= min(w, h) <= ICON_RANGE[1]):
                    warn.append(f"`{icon}` is {w}x{h}; the spec suggests {ICON_RANGE[0]}–{ICON_RANGE[1]}px")
        else:
            info.append("no `icon.png` / `icon.jpg` — the messenger will use a default icon")

        total = sum(i.file_size for i in infos)
        info.append(f"{len(names)} entries, {os.path.getsize(path)} bytes packed / {total} bytes unpacked")

    return err, warn, info


# --------------------------------------------------------------------------
# pack
# --------------------------------------------------------------------------
def pack(src_dir: str, out_path: str):
    """Build a spec-valid `.xdc` from a directory, deterministically.

    Fixed timestamps + sorted entries mean rebuilding from unchanged sources
    produces a byte-identical package, so `git status` stays clean.
    `webxdc.js` is refused: it must never be packaged.
    """
    src_dir = os.path.abspath(src_dir)
    if not os.path.isfile(os.path.join(src_dir, "index.html")):
        raise SystemExit(f"error: {src_dir} has no index.html — nothing to package")
    if not out_path.lower().endswith(".xdc"):
        raise SystemExit(f"error: output must end in .xdc (got {out_path!r})")
    if os.path.exists(os.path.join(src_dir, "webxdc.js")):
        raise SystemExit("error: webxdc.js is present in the source dir; the spec says it must not be packaged. Remove it or exclude it from staging.")

    entries = []
    for dirpath, dirnames, filenames in os.walk(src_dir):
        dirnames[:] = sorted(d for d in dirnames if d not in (".git", "__pycache__", "node_modules", "test", "dist"))
        for f in sorted(filenames):
            if f == "webxdc.js":
                continue
            full = os.path.join(dirpath, f)
            arc = os.path.relpath(full, src_dir).replace(os.sep, "/")
            entries.append((arc, full))
    entries.sort()

    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        for arc, full in entries:
            zi = zipfile.ZipInfo(arc, date_time=(1980, 1, 1, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            with open(full, "rb") as fh:
                z.writestr(zi, fh.read())

    errs, warns, _ = validate(out_path)
    print(f"packed {out_path} ({os.path.getsize(out_path)} bytes, {len(entries)} entries)")
    for e in errs:
        print(f"  FAIL {e}")
    for w in warns:
        print(f"  WARN {w}")
    return 1 if errs else 0


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_val = sub.add_parser("validate", help="check packages against the container spec")
    p_val.add_argument("paths", nargs="*", help="files or directories (default: repo root)")
    p_val.add_argument("-q", "--quiet", action="store_true", help="only print failures")
    p_val.add_argument("--all", action="store_true",
                       help="also scan incoming/ and other excluded dirs")

    p_pack = sub.add_parser("pack", help="build a .xdc deterministically from a directory")
    p_pack.add_argument("src")
    p_pack.add_argument("out")

    p_list = sub.add_parser("list", help="list every webxdc package found")
    p_list.add_argument("paths", nargs="*")
    p_list.add_argument("--all", action="store_true", help="also scan excluded dirs")

    args = ap.parse_args(argv)

    if args.cmd == "pack":
        return pack(args.src, args.out)

    roots = args.paths or [REPO_ROOT]
    # `dist` is excluded from the *walk* only when scanning the repo root, so
    # that project build output is still found; an explicitly named path always
    # wins. Excluding it outright would hide every real deliverable.
    exclude = frozenset() if args.all else frozenset(DEFAULT_EXCLUDE - {"dist"})
    pkgs = find_packages(roots, exclude)
    if args.cmd == "list":
        for p in pkgs:
            print(os.path.relpath(p, REPO_ROOT))
        print(f"\n{len(pkgs)} package(s)")
        return 0

    if not pkgs:
        print("no webxdc packages found")
        return 0

    failures = 0
    for p in pkgs:
        err, warn, info = validate(p)
        rel = os.path.relpath(p, REPO_ROOT)
        status = "FAIL" if err else ("WARN" if warn else "OK")
        if status == "FAIL":
            failures += 1
        if args.quiet and status == "OK":
            continue
        print(f"[{status}] {rel}")
        for m in err:
            print(f"    ✗ {m}")
        for m in warn:
            print(f"    ! {m}")
        if not args.quiet:
            for m in info:
                print(f"    · {m}")
    print()
    print(f"{len(pkgs) - failures}/{len(pkgs)} package(s) spec-valid")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
