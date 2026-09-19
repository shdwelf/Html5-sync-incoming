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
for app in cyberchef shamir radar-scope; do
  echo "== $app =="
  python3 "$here/webxdc_tool.py" pack "$here/$app" "$here/$app/dist/$app.xdc" || rc=1
done
echo
python3 "$here/webxdc_tool.py" validate "$here/.." || rc=1
exit $rc
