#!/usr/bin/env bash
# Rebuild every webxdc package that lives in this directory (the ones with no
# separate source project). Packages belonging to a source project are built by
# that project's own build script:
#   projects/cryptomonopoly-webxdc/build.sh
#   projects/presskit-reassembler/dist/make_packages.sh
#
# Packing is deterministic (fixed timestamps, sorted entries), so re-running
# this on unchanged sources leaves `git status` clean.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
rc=0

# The validator is the only thing between this repo and another package that
# cannot load, so check the checker before trusting it to gate a build.
python3 "$here/webxdc_tool.py" selftest

# Refuse to package icons that no longer match their generator. `icon.png` is a
# build artifact of gen_icons.py, not hand-placed art; checking it here is what
# keeps it rebuildable (REVIEW.md PY-8 removed a generator whose output had
# drifted from the committed file — never let that happen to an icon too).
if ! python3 "$here/gen_icons.py" --check; then
  echo "error: webxdc/*/icon.png does not match gen_icons.py — run: python3 webxdc/gen_icons.py" >&2
  exit 1
fi

for app in cyberchef shamir radar-scope; do
  echo "== $app =="
  python3 "$here/webxdc_tool.py" pack "$here/$app" "$here/$app/dist/$app.xdc" || rc=1
done
echo
python3 "$here/webxdc_tool.py" validate "$here/.." || rc=1
exit $rc
