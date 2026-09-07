#!/usr/bin/env bash
# Package the Cryptomonopoly WebXDC app:
#   dist/Cryptomonopoly.xdc        (Delta Chat webxdc package — a zip)
# plus a copy with the .webxdc extension for hosts that look for it.
# The same folder also runs as a static website in any browser (hot-seat mode).
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
dist="$here/dist"
app="$here/index.html"

mkdir -p "$dist"
cd "$here"

stage="$(mktemp -d)"
trap 'rm -rf "$stage"' EXIT

# stage everything the app needs (no build step required)
cp index.html "$stage/index.html"
cp manifest.toml "$stage/manifest.toml"
cp icon.png "$stage/icon.png"
mkdir -p "$stage/css" "$stage/js"
cp css/*.css "$stage/css/"
cp js/*.js "$stage/js/"

python3 - "$stage" "$dist/Cryptomonopoly.xdc" <<'PY'
import sys, zipfile, os
stage, out = sys.argv[1], sys.argv[2]
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for base, _, files in os.walk(stage):
        for f in files:
            full = os.path.join(base, f)
            arc = os.path.relpath(full, stage)
            z.write(full, arcname=arc)
print("wrote", out, os.path.getsize(out), "bytes")
PY

cp "$dist/Cryptomonopoly.xdc" "$dist/Cryptomonopoly.webxdc"
echo "Also available (static web preview): open index.html or serve this folder."
echo "dist/Cryptomonopoly.xdc ready."
