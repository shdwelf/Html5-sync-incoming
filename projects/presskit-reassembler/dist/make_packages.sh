#!/usr/bin/env bash
# Build the deployable delivery formats of the Press Kit Reassembler:
#   webxdc / xdc   (Delta Chat offline-app package)
#   war            (static web application archive for any servlet container)
# plus staging of java/ and qbasic/ sources.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
root="$(cd "$here/.." && pwd)"
app="$root/presskit-reassembler.html"
icon="$here/gfx/icon.png"
staging="$here/.stage"
rm -rf "$staging"; mkdir -p "$staging"
cd "$here"

# ---------- 1) webxdc / xdc ----------
wx="$staging/webxdc"; mkdir -p "$wx"
cp "$app" "$wx/index.html"
cp "$icon" "$wx/icon.png"
# Only `manifest.toml` exists in the webxdc container spec. This script used to
# also emit manifest.json plus a `cp manifest.json manifest.xml` "classic
# manifest" -- which put JSON inside a file named .xml. Neither file is read by
# any implementation, so both are gone.
cat > "$wx/manifest.toml" <<TOML
# webxdc manifest -- the spec reads `name` and `source_code_url`
# (https://webxdc.org/docs/spec/format.html).
name = "Press Kit Reassembler"
source_code_url = "https://github.com/shdwelf/Html5-sync-incoming/tree/main/projects/presskit-reassembler"
description = "HTML5 + WebAssembly press-kit reassembler -> classic DOS .COM/.DAT output. Original educational retrocomputing tool; reproduces no studio promotional copy."
icon = "icon.png"
TOML
# NOTE: no webxdc.js is staged. The spec is explicit that the messenger provides
# it and that it "must not be added to your .xdc file" -- shipping the old shim
# made every build fail validation. This app is a single-player offline tool
# delivered in a webxdc container; it never calls sendUpdate/setUpdateListener,
# so it needs no API shim at all.

# `.xdc` is the only extension the spec defines; the byte-identical `.webxdc`
# twin this script used to cp out is no longer produced. Entries are sorted and
# timestamps fixed so a rebuild from unchanged sources is byte-identical.
python3 - "$wx" "$here/webxdc/presskit-reassembler.xdc" <<'PY'
import sys, zipfile, os
wx, out = sys.argv[1], sys.argv[2]
os.makedirs(os.path.dirname(out), exist_ok=True)
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for f in sorted(os.listdir(wx)):
        full = os.path.join(wx, f)
        if not os.path.isfile(full):
            continue
        zi = zipfile.ZipInfo(f, date_time=(1980, 1, 1, 0, 0, 0))
        zi.compress_type = zipfile.ZIP_DEFLATED
        zi.external_attr = 0o644 << 16
        with open(full, "rb") as fh:
            z.writestr(zi, fh.read())
print("wrote", out, os.path.getsize(out), "bytes")
PY

# ---------- 2) WAR (static web application) ----------
wa="$staging/war"; mkdir -p "$wa/WEB-INF"
cp "$app" "$wa/index.html"
cp "$icon" "$wa/icon.png"
cat > "$wa/WEB-INF/web.xml" <<XML
<?xml version="1.0" encoding="UTF-8"?>
<web-app xmlns="http://xmlns.jcp.org/xml/ns/javaee"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://xmlns.jcp.org/xml/ns/javaee
                             http://xmlns.jcp.org/xml/ns/javaee/web-app_4_0.xsd"
         version="4.0">
  <display-name>Press Kit Reassembler</display-name>
  <description>Static HTML5 + WASM web application. Drop the .war into any servlet container (Tomcat/Jetty/GlassFish).</description>
  <welcome-file-list><welcome-file>index.html</welcome-file></welcome-file-list>
</web-app>
XML
mkdir -p "$here/war"
# Deterministic, like the .xdc above: sorted entries, fixed timestamps,
# normalised permissions. `z.write()` stamped the current mtime, so every rebuild
# produced different bytes and churned the committed artifact.
python3 - "$wa" "$here/war/presskit-reassembler.war" <<'PY'
import sys, zipfile, os
wa, out = sys.argv[1], sys.argv[2]
entries = []
for base, _, files in os.walk(wa):
    for f in files:
        full = os.path.join(base, f)
        entries.append((os.path.relpath(full, wa).replace(os.sep, "/"), full))
entries.sort()
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for arc, full in entries:
        zi = zipfile.ZipInfo(arc, date_time=(1980, 1, 1, 0, 0, 0))
        zi.compress_type = zipfile.ZIP_DEFLATED
        zi.external_attr = 0o644 << 16
        with open(full, "rb") as fh:
            z.writestr(zi, fh.read())
print("wrote", out, os.path.getsize(out), "bytes")
PY

# ---------- 3) copy ascii intro text for qbasic ----------
mkdir -p "$here/qbasic"
cp "$here/gfx/intro.txt" "$here/qbasic/INTRO.TXT" 2>/dev/null || true

echo
echo "Built packages:"
ls -l "$here/webxdc" "$here/war"
