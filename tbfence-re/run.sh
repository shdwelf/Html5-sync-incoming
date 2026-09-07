#!/usr/bin/env bash
# run.sh — one-command analysis pipeline for the TbFence (ThunderBYTE Fence) DOS
# binaries. Run from anywhere:
#
#     ./run.sh                 # analyze every .exe/.com found in this folder
#     ./run.sh TBFENCE.EXE ... # analyze specific files
#     GHIDRA_HOME=/opt/ghidra ./run.sh
#
# Pipeline, per input:
#   1) orient  : python3 analyze_dos.py  -> analysis/<file>.survey.txt
#   2) disasm+ : Ghidra headless (x86 real-mode) -> analysis/ghidra/<file>/
#                (decompiled pseudo-C via ghidra_decompile_all.py)
#
# The script degrades gracefully: it always does step 1, and only runs Ghidra
# if (a) a binary was supplied/found and (b) a Ghidra install is located. If no
# binaries are present it prints exactly where to get them.
set -uo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$here"

ANALYZER="$here/analyze_dos.py"
POSTSCRIPT="$here/ghidra_decompile_all.py"
OUT="$here/analysis"
ARCH="x86:LE:16:RealMode"   # DOS MZ executables are 16-bit real mode

# ---------------------------------------------------------------------------
# 0) inputs
# ---------------------------------------------------------------------------
if [ "$#" -gt 0 ]; then
  INPUTS=("$@")
else
  # default set = the real distribution; ignore the kit's own *.py files
  INPUTS=()
  for want in TBFENCE.EXE GATEWAY.EXE TBFKEY.EXE; do
    [ -f "$want" ] && INPUTS+=("$want")
  done
  # fall back to any DOS binary present
  if [ "${#INPUTS[@]}" -eq 0 ]; then
    shopt -s nullglob
    for f in *.exe *.EXE *.com *.COM; do INPUTS+=("$f"); done
    shopt -u nullglob
  fi
fi

# ---------------------------------------------------------------------------
# 1) locate Ghidra (optional but recommended)
# ---------------------------------------------------------------------------
find_ghidra() {
  # 1. env var
  if [ -n "${GHIDRA_HOME:-}" ] && [ -x "$GHIDRA_HOME/support/analyzeHeadless" ]; then
    echo "$GHIDRA_HOME/support/analyzeHeadless"; return
  fi
  # 2. PATH
  if command -v analyzeHeadless >/dev/null 2>&1; then
    command -v analyzeHeadless; return
  fi
  # 3. common install roots
  for c in "$HOME/ghidra"* "/opt/ghidra"* "/usr/local/ghidra"* /usr/share/ghidra*; do
    [ -x "$c/support/analyzeHeadless" ] && { echo "$c/support/analyzeHeadless"; return; }
  done
  return 1
}
GHIDRA_BIN="$(find_ghidra || true)"

# ---------------------------------------------------------------------------
# 2) no binaries? -> show the user how to get them, still exit clean
# ---------------------------------------------------------------------------
if [ "${#INPUTS[@]}" -eq 0 ]; then
  cat <<'EOF'

  No TbFence binaries were found in tbfence-re/.

  Drop the originals here, then re-run ./run.sh. They are small and freely
  obtainable from the PC-SIG / PSL-archive distribution:
    http://annex.retroarchive.org/cdrom/psl-v3n4/UTILS/DOS/SECURITY/TBFENCE/TBFENCE.EXE
    http://annex.retroarchive.org/cdrom/psl-v3n4/UTILS/DOS/SECURITY/TBFENCE/TBFKEY.EXE
    http://annex.retroarchive.org/cdrom/psl-v3n4/UTILS/DOS/SECURITY/TBFENCE/GATEWAY.EXE
  (or extract them from the Internet Archive item 'spidla-sz' CD image.)

  Note: this sandbox can only transfer from GitHub hosts, so the archive
  download itself must happen on your machine.
EOF
  exit 0
fi

mkdir -p "$OUT"

if [ -z "$GHIDRA_BIN" ]; then
  echo "ℹ️  Ghidra not found — running the static survey only."
  echo "   Set GHIDRA_HOME to your install to enable decompilation, e.g.:"
  echo "   GHIDRA_HOME=/opt/ghidra ./run.sh"
fi

# ---------------------------------------------------------------------------
# 3) per-file pipeline
# ---------------------------------------------------------------------------
for bin in "${INPUTS[@]}"; do
  [ -f "$bin" ] || { echo "skip (missing): $bin"; continue; }
  name="$(basename "$bin")"
  base="${name%.*}"
  echo "──────────────────────────────────────────────────────────────"
  echo "▸ $bin  ($(wc -c < "$bin") bytes)"

  # -- step 1: static survey ------------------------------------------
  survey="$OUT/${base}.survey.txt"
  python3 "$ANALYZER" "$bin" > "$survey"
  echo "   survey   -> $survey"
  head -20 "$survey"

  # -- step 2: Ghidra headless decompile ------------------------------
  if [ -n "$GHIDRA_BIN" ]; then
    gproj="$(mktemp -d)"
    gdir="$OUT/ghidra/${base}"
    rm -rf "$gdir"; mkdir -p "$gdir"
    echo "   ghidra   -> analyzing $bin (this can take a few minutes the first time)..."
    if "$GHIDRA_BIN" "$gproj" "TbFence_${base}" \
          -import "$bin" \
          -processor "$ARCH" \
          -scriptPath "$here" \
          -postScript ghidra_decompile_all.py "$gdir" > "$OUT/ghidra/${base}.log" 2>&1; then
      echo "   ghidra   -> done. pseudo-C in $gdir (see _combined.c)"
    else
      echo "   ghidra   -> FAILED (see $OUT/ghidra/${base}.log)."
      echo "              Ghidra's MZ import sometimes needs a JDK; the survey above still stands."
    fi
    rm -rf "$gproj"
  fi
done

echo "──────────────────────────────────────────────────────────────"
echo "Done. Open $OUT/ for results."
