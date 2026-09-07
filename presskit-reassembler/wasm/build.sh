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

# 2. (Re)assemble the static 16-bit DOS runtime skeleton (optional)
if command -v python3 >/dev/null 2>&1; then
  python3 "$here/build_dos_stub.py" >/dev/null 2>&1 \
    && echo "rebuilt dos_stub.bin" || echo "note: dos_stub.bin not rebuilt (keystone missing?)"
fi

# 3. Inject the fresh base64 into the app's WASM_B64 constant
b64="$(base64 -w0 "$here/presskit.wasm")"
python3 - "$app" "$b64" <<'PY'
import sys
app, b64 = sys.argv[1], sys.argv[2]
s = open(app).read()
import re
s = re.sub(r'(const WASM_B64 = ")[^"]*(";)', lambda m: m.group(1)+b64+m.group(2), s, count=1)
open(app, "w").write(s)
print("refreshed WASM_B64 in", app)
PY
