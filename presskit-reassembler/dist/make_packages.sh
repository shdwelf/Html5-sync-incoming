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
cat > "$wx/manifest.json" <<JSON
{
  "name": "Press Kit Reassembler",
  "description": "HTML5 + WebAssembly press-kit reassembler. Enter your variables in a form and it reassembles a runnable classic DOS .COM press-kit program plus a .DAT mirror. Original educational retrocomputing tool - reproduces no studio promotional copy.",
  "icon": "icon.png",
  "source_code_url": "https://github.com/shdwelf/Html5-sync-incoming",
  "min_api": 1
}
JSON
# modern + classic manifests for widest app-compat
cp "$wx/manifest.json" "$wx/manifest.xml"
cat > "$wx/manifest.toml" <<TOML
name = "Press Kit Reassembler"
description = "HTML5 + WASM press-kit reassembler -> DOS .COM/.DAT output. Original tool, no studio copy."
type = "webxdc-app"
version = "0.1.0"
icon = "icon.png"
TOML
# tiny webxdc shim so it also opens in a plain browser
cat > "$wx/webxdc.js" <<'JS'
/* minimal webxdc stub for plain-browser preview */
if (typeof window !== "undefined" && !window.webxdc) {
  window.webxdc = { selfAddr: "", selfName: "Local", sendUpdate: ()=>{},
    getAllUpdates: ()=>{}, setUpdateListener: ()=>{}, sendToChat: ()=>{},
    importModule: async (url)=>{ return await import(url); } };
  console.log("webxdc shim active (open in Delta Chat for full webxdc)");
}
JS
python3 - "$wx" "$here/webxdc/presskit-reassembler.webxdc" <<'PY'
import sys, zipfile, os
wx, out = sys.argv[1], sys.argv[2]
os.makedirs(os.path.dirname(out), exist_ok=True)
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for f in os.listdir(wx):
        z.write(os.path.join(wx, f), arcname=f)
print("wrote", out, os.path.getsize(out), "bytes")
PY
cp "$here/webxdc/presskit-reassembler.webxdc" "$here/webxdc/presskit-reassembler.xdc"

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
python3 - "$wa" "$here/war/presskit-reassembler.war" <<'PY'
import sys, zipfile, os
wa, out = sys.argv[1], sys.argv[2]
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for base, _, files in os.walk(wa):
        for f in files:
            full = os.path.join(base, f)
            rel = os.path.relpath(full, wa)
            z.write(full, arcname=rel)
print("wrote", out, os.path.getsize(out), "bytes")
PY

# ---------- 3) copy ascii intro text for qbasic ----------
mkdir -p "$here/qbasic"
cp "$here/gfx/intro.txt" "$here/qbasic/INTRO.TXT" 2>/dev/null || true

echo
echo "Built packages:"
ls -l "$here/webxdc" "$here/war"
