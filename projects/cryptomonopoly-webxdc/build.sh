#!/usr/bin/env bash
# Package the Cryptomonopoly webxdc app.
#
#   dist/Cryptomonopoly.xdc   — the ONLY deliverable. `.xdc` is the extension the
#                               container spec defines; the duplicate `.webxdc`
#                               copy this script used to emit was byte-identical
#                               and is no longer produced or committed.
#
# The source folder also runs as a static website in any browser (hot-seat mode):
# just open index.html, or serve this directory.
#
# NOTE: webxdc.js is intentionally NOT staged. The spec says the messenger
# provides it and that it "must not be added to your .xdc file". index.html
# still references it so the API is activated at runtime.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
dist="$here/dist"
out="$dist/Cryptomonopoly.xdc"

mkdir -p "$dist"
cd "$here"

stage="$(mktemp -d)"
trap 'rm -rf "$stage"' EXIT

# stage everything the app needs (no build step required)
cp index.html   "$stage/index.html"
cp manifest.toml "$stage/manifest.toml"
cp icon.png     "$stage/icon.png"
mkdir -p "$stage/css" "$stage/js"
cp css/*.css "$stage/css/"
cp js/*.js   "$stage/js/"

# guard: the shim must never end up inside the package
if [ -e "$stage/webxdc.js" ]; then
  echo "error: webxdc.js must not be packaged (provided by the messenger)" >&2
  exit 1
fi

python3 - "$stage" "$out" <<'PY'
import sys, zipfile, os
stage, out = sys.argv[1], sys.argv[2]
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for base, _, files in sorted(os.walk(stage)):
        for f in sorted(files):
            full = os.path.join(base, f)
            arc = os.path.relpath(full, stage).replace(os.sep, "/")
            # deterministic timestamps keep rebuilds byte-for-byte reproducible
            zi = zipfile.ZipInfo(arc, date_time=(1980, 1, 1, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            with open(full, "rb") as fh:
                z.writestr(zi, fh.read())
print("wrote", out, os.path.getsize(out), "bytes")
PY

echo "dist/Cryptomonopoly.xdc ready — validate with: python3 ../../webxdc/webxdc_tool.py validate"
echo "Static web preview: open index.html or serve this folder."
