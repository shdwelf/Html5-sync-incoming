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
import ast
import contextlib
import io
import os
import re
import struct
import sys
import zipfile

try:                                    # tomllib is Python 3.11+
    import tomllib as _tomllib
except ImportError:                     # pragma: no cover - version dependent
    _tomllib = None

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
# manifest.toml
# --------------------------------------------------------------------------
class ManifestSyntaxError(Exception):
    """The package really does carry a manifest that cannot be read."""


class ManifestReaderUnavailable(Exception):
    """The *tool* cannot read it: no `tomllib` before Python 3.11 and the
    manifest uses TOML the fallback below will not guess at. Reported as a
    warning about this script, never as a failure of the package."""


def _strip_toml_comment(line: str) -> str:
    out, quote, i = [], None, 0
    while i < len(line):
        ch = line[i]
        if quote:
            out.append(ch)
            if ch == "\\" and i + 1 < len(line):
                out.append(line[i + 1])
                i += 2
                continue
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
            out.append(ch)
        elif ch == "#":
            break
        else:
            out.append(ch)
        i += 1
    if quote:
        raise ManifestSyntaxError(f"unterminated string: {line!r}")
    return "".join(out).strip()


def _toml_min(text: str) -> dict:
    """Reader for exactly what a webxdc manifest is: top-level `key = literal`
    lines and `#` comments (https://toml.io).

    Anything else raises, because a silently-wrong value here would be worse
    than a refusal: sections, dotted keys, inline tables, multi-line strings and
    TOML datetimes all parse to something other than what the spec means."""
    out = {}
    for lineno, raw in enumerate(text.splitlines(), 1):
        line = _strip_toml_comment(raw)
        if not line:
            continue
        if line.startswith("["):
            raise ManifestReaderUnavailable(f"line {lineno}: tables are beyond the fallback reader")
        m = re.match(r"^([A-Za-z0-9_.-]+)\s*=\s*(.+)$", line)
        if not m:
            raise ManifestSyntaxError(f"line {lineno}: not a `key = value` line")
        key, val = m.group(1), m.group(2).strip()
        if val.lower() in ("true", "false"):
            val = val.capitalize()
        if val.endswith(","):
            val = val[:-1]
        try:
            parsed = ast.literal_eval(val)
        except (ValueError, SyntaxError) as exc:
            raise ManifestSyntaxError(f"line {lineno}: cannot parse {val!r} ({exc})") from exc
        if not isinstance(parsed, (str, int, float, bool, list)):
            raise ManifestSyntaxError(f"line {lineno}: unsupported value {type(parsed).__name__}")
        out[key] = parsed
    return out


def parse_manifest(raw: bytes) -> dict:
    """`manifest.toml` bytes -> dict, via tomllib when it exists."""
    text = raw.decode("utf-8", "replace")
    if _tomllib is not None:
        try:
            return _tomllib.loads(text)
        except Exception as exc:                       # tomllib.TOMLDecodeError
            raise ManifestSyntaxError(str(exc)) from exc
    return _toml_min(text)


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
                man = parse_manifest(raw)
            except ManifestSyntaxError as e:
                err.append(f"`manifest.toml` does not parse: {e}")
                man = None
            except ManifestReaderUnavailable as e:
                warn.append(f"`manifest.toml` not checked (needs Python 3.11+): {e}")
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
# selftest
# --------------------------------------------------------------------------
def selftest():
    """Run the validator against packages built to be right and to be wrong.

    This tool is the only thing standing between the repo and another package
    that cannot load (REVIEW.md XDC-1), and it had no test of its own. Stdlib
    only, no network, no fixtures committed: every case is constructed in a
    temp directory, so `python3 webxdc_tool.py selftest` is safe to run from CI
    or from a pre-push hook — `build-all.sh` runs it before it packs anything."""
    import tempfile
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from gen_icons import png_encode

    checks = {"pass": 0, "fail": []}

    def check(cond, label):
        if cond:
            checks["pass"] += 1
        else:
            checks["fail"].append(label)

    manifest = (b'name = "Selftest App"\n'
                b'source_code_url = "https://example.invalid/webxdc/selftest"\n'
                b'description = "built by selftest"\n'
                b'icon = "icon.png"\n')
    icon128 = png_encode(128, bytes((10, 20, 30, 255)) * (128 * 128))
    icon96 = png_encode(96, bytes((10, 20, 30, 255)) * (96 * 96))
    index = b"<!doctype html><title>selftest</title>"

    def package(tmp, name, entries, compression=zipfile.ZIP_DEFLATED):
        path = os.path.join(tmp, name)
        with zipfile.ZipFile(path, "w", compression) as z:
            for arc, data in entries:
                zi = zipfile.ZipInfo(arc, date_time=(1980, 1, 1, 0, 0, 0))
                zi.compress_type = compression
                zi.external_attr = 0o644 << 16
                z.writestr(zi, data)
        return path

    good = [("index.html", index), ("manifest.toml", manifest), ("icon.png", icon128)]

    with tempfile.TemporaryDirectory(prefix="xdc-selftest-") as tmp:
        # --- the happy path: zero errors AND zero warnings -----------------
        err, warn, info = validate(package(tmp, "good.xdc", good))
        check(not err and not warn, f"a conformant package must be silent, got {err} {warn}")
        check(any("3 entries" in m for m in info), "info should report the entry count")

        # --- every failure mode this repo has actually shipped -------------
        err, _, _ = validate(package(tmp, "nested.xdc", [("webxdc-app/index.html", index)]))
        check(any("not at the ZIP root" in e for e in err), "nested index.html must FAIL (XDC-1)")

        err, _, _ = validate(package(tmp, "shim.xdc", good + [("webxdc.js", b"window.webxdc={}")]))
        check(any("webxdc.js" in e for e in err), "a packaged webxdc.js must FAIL (XDC-2)")

        err, warn, _ = validate(package(tmp, "xml.xdc", good + [("manifest.xml", b'{"name":1}')]))
        check(any("contains JSON, not XML" in e for e in err), "manifest.xml holding JSON must FAIL (XDC-3)")
        err, warn, _ = validate(package(tmp, "json.xdc", good + [("manifest.json", manifest)]))
        check(not err and any("not part of the webxdc container spec" in w for w in warn),
              "a stray manifest.json is a WARN (dead weight), not a failure")
        err, _, _ = validate(package(tmp, "wrongext.zip", good))
        check(any("requires `.xdc`" in e for e in err), "a .zip extension must FAIL (SH-2)")

        err, _, _ = validate(package(tmp, "noname.xdc",
                                      [("index.html", index), ("manifest.toml", b'description = "x"\n')]))
        check(any("no `name`" in e for e in err), "a manifest without `name` must FAIL (XDC-6)")

        err, warn, info = validate(package(tmp, "junk.xdc", good[:1] + [("manifest.toml", manifest + b'version = "3"\n')]))
        check(not err and any("no implementation reads" in m for m in info),
              "non-spec manifest keys are INFO, never a failure")

        err, warn, _ = validate(package(tmp, "tiny.xdc", [("index.html", index), ("icon.png", icon96)]))
        check(not err and any("96x96" in w for w in warn), "an undersized icon must WARN, not fail (XDC-7)")

        err, _, _ = validate(package(tmp, "traversal.xdc", good + [("../evil.txt", b"nope")]))
        check(any("unsafe or non-portable entry path" in e for e in err), "path traversal must FAIL")

        err, _, _ = validate(package(tmp, "bzip.xdc", good, compression=zipfile.ZIP_BZIP2))
        check(any("Deflate or Store" in e for e in err), "non-spec compression must FAIL")

        err, warn, info = validate(package(tmp, "store.xdc", good, compression=zipfile.ZIP_STORED))
        check(not err and not warn, "Store compression is allowed by the spec")

        err, warn, info = validate(package(tmp, "nomanifest.xdc", [("index.html", index)]))
        check(not err and any("no `manifest.toml`" in m for m in info), "a bare package is legal, and says so")

        # --- pack() refuses what the spec forbids, and is reproducible -----
        src = os.path.join(tmp, "src")
        os.makedirs(src)
        for arc, data in good:
            with open(os.path.join(src, arc), "wb") as fh:
                fh.write(data)
        a = os.path.join(tmp, "pack", "a.xdc")
        b = os.path.join(tmp, "pack", "b.xdc")
        quiet = contextlib.redirect_stdout(io.StringIO())
        with quiet:                                   # pack() is chatty; tests are not
            pack(src, a)
            pack(src, b)
        check(open(a, "rb").read() == open(b, "rb").read(), "packing must be deterministic (SH-2)")
        with open(os.path.join(src, "webxdc.js"), "wb") as fh:
            fh.write(b"window.webxdc={}")
        try:
            with quiet:
                pack(src, os.path.join(tmp, "pack", "c.xdc"))
            check(False, "pack() must refuse a source dir containing webxdc.js")
        except SystemExit as e:
            check("must not be packaged" in str(e), "pack() refusal should explain itself")

        # --- the manifest reader itself ------------------------------------
        check(_toml_min(manifest.decode()) == {"name": "Selftest App",
                                               "source_code_url": "https://example.invalid/webxdc/selftest",
                                               "description": "built by selftest",
                                               "icon": "icon.png"},
              "the fallback TOML reader must agree with tomllib on a real manifest")
        check(_toml_min('a = "b"  # trailing comment\nc = true\n') == {"a": "b", "c": True},
              "fallback reader: comments and booleans")
        try:
            _toml_min("[section]\nname = \"x\"\n")
            check(False, "fallback reader must refuse tables, not mis-parse them")
        except ManifestReaderUnavailable:
            check(True, "fallback reader refuses tables with the right exception")
        try:
            _toml_min('name = "unterminated\n')
            check(False, "fallback reader must refuse an unterminated string")
        except ManifestSyntaxError:
            check(True, "fallback reader reports unterminated strings as a syntax error")
        check(parse_manifest(manifest).get("name") == "Selftest App", "parse_manifest works end to end")

        # --- image sniffing --------------------------------------------------
        check(png_size(b"not a png") is None and jpeg_size(b"not a jpeg") is None,
              "size sniffers return None rather than guessing")
        check(png_size(icon128) == (128, 128), "png_size reads IHDR")

    total = checks["pass"] + len(checks["fail"])
    for f in checks["fail"]:
        print(f"  FAIL  {f}")
    print(f"selftest: {checks['pass']}/{total} checks passed")
    return 1 if checks["fail"] else 0


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

    sub.add_parser("selftest", help="verify this validator against synthetic packages")

    p_list = sub.add_parser("list", help="list every webxdc package found")
    p_list.add_argument("paths", nargs="*")
    p_list.add_argument("--all", action="store_true", help="also scan excluded dirs")

    args = ap.parse_args(argv)

    if args.cmd == "pack":
        return pack(args.src, args.out)
    if args.cmd == "selftest":
        return selftest()

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
