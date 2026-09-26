#!/usr/bin/env bash
# Rebuild the WASM engine and refresh the base64 constant embedded in the app.
# Requires: `wabt` on PATH (e.g. `npm i -g wabt`) and Python (for the stub).
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
app="$here/../presskit-reassembler.html"

# 1. Compile WAT -> WASM
command -v wat2wasm >/dev/null 2>&1 || { echo "wat2wasm not found (install wabt)"; exit 1; }
wat2wasm "$here/presskit.wat" -o "$here/presskit.wasm"
echo "compiled presskit.wasm"

# 2. (Re)assemble the static 16-bit DOS runtime skeleton.
#
# This used to run the generator with stdout AND stderr discarded and downgrade
# any failure to a soft "note: ... (keystone missing?)", so a build whose stub
# did not regenerate -- missing dependency, or the two-pass length assert firing
# -- still reported success and shipped a stale dos_stub.bin. Fail loudly, and
# show the real error. Set PRESSKIT_SKIP_STUB=1 to opt out deliberately.
if [ "${PRESSKIT_SKIP_STUB:-0}" = "1" ]; then
  echo "skipping dos_stub.bin (PRESSKIT_SKIP_STUB=1)"
elif command -v python3 >/dev/null 2>&1; then
  if ! (cd "$here" && python3 build_dos_stub.py); then
    echo "error: build_dos_stub.py failed; dos_stub.bin was NOT rebuilt." >&2
    echo "       Install the assembler with:  pip install keystone-engine" >&2
    echo "       (add --break-system-packages on PEP 668 distros)" >&2
    exit 1
  fi
  echo "rebuilt dos_stub.bin"
else
  echo "error: python3 not found; cannot rebuild dos_stub.bin" >&2
  exit 1
fi

# 3. Inject the fresh base64 into the app's WASM_B64 constant
#
# `base64 -w0` is GNU coreutils only — macOS and the BSDs have no -w and the
# command dies with a usage error (PY-6 fixed the same class of Linux-only
# assumption in gen_gfx.py). `tr -d` is portable and does the same job.
b64="$(base64 < "$here/presskit.wasm" | tr -d '\n\r')"
python3 - "$app" "$b64" <<'PY'
import re
import sys

app, b64 = sys.argv[1], sys.argv[2]
with open(app, encoding="utf-8") as fh:
    src = fh.read()
# count=1 alone was the bug: if the constant is renamed, quoted differently or
# dropped, re.sub silently returns the file unchanged and the script still
# printed "refreshed". Assert exactly one substitution happened.
new, n = re.subn(r'(const WASM_B64 = ")[^"]*(";)', lambda m: m.group(1) + b64 + m.group(2), src, count=1)
if n != 1:
    sys.exit("error: no `const WASM_B64 = \"…\";` line found in %s — refusing to report a "
             "refresh that did not happen. If the constant was renamed, fix this script too." % app)
if new == src:
    print("WASM_B64 already current in %s (%d chars, file left untouched)" % (app, len(b64)))
else:
    with open(app, "w", encoding="utf-8") as fh:
        fh.write(new)
    print("refreshed WASM_B64 in %s (%d chars of base64)" % (app, len(b64)))
PY

# ---------------------------------------------------------------------------
# 4) prove it worked
# ---------------------------------------------------------------------------
# Re-read the app and confirm the constant now equals THIS wasm, byte for byte.
# Cheap, and it is the check that would have caught stale engine bytes shipping
# in every package — the same class of failure REVIEW.md SH-1 fixed for
# dos_stub.bin (a build that reported success while leaving the artifact behind).
python3 - "$app" "$here/presskit.wasm" <<'PY'
import base64, os, re, sys
with open(sys.argv[1], encoding="utf-8") as fh:
    html = fh.read()
with open(sys.argv[2], "rb") as fh:
    want = base64.b64encode(fh.read()).decode()
m = re.search(r'const WASM_B64 = "([^"]*)";', html)
if not m:
    sys.exit("error: no WASM_B64 constant in %s after injection" % sys.argv[1])
if m.group(1) != want:
    sys.exit("error: %s embeds %d chars of base64, presskit.wasm needs %d — stale engine bytes"
             % (sys.argv[1], len(m.group(1)), len(want)))
print("verified: %s embeds presskit.wasm (%d bytes)"
      % (sys.argv[1], os.path.getsize(sys.argv[2])))
PY
