#!/usr/bin/env bash
# Build a runnable .jar for the Press Kit Reassembler.
# Requires a JDK (javac + jar). No Maven/Gradle needed.
#
#   ./build.sh                 # -> presskit-reassembler.jar
#   java -jar presskit-reassembler.jar 8080
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
root="$(cd "$here/../.." && pwd)"
app="$root/presskit-reassembler.html"
icon="$here/../gfx/icon.png"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

# stage resources + sources
mkdir -p "$tmp/src" "$tmp/res/static"
cp "$here/PressKitServer.java" "$tmp/src/"
cp "$app" "$tmp/res/static/index.html"
cp "$icon" "$tmp/res/static/icon.png"

# compile
javac -d "$tmp/classes" "$tmp/src/PressKitServer.java"

# jar with classpath resources at the right place
(
  cd "$tmp/classes"
  cp -r "$tmp/res/static" .
  printf 'Main-Class: PressKitServer\n' > MANIFEST.MF
  jar cfm "$here/presskit-reassembler.jar" MANIFEST.MF PressKitServer*.class static
)
echo "wrote $here/presskit-reassembler.jar"
echo "run:  java -jar presskit-reassembler.jar 8080"
