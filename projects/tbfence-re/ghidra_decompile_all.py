# ghidra_decompile_all.py
# Ghidra headless post-script: import your DOS binary then run
#   analyzeHeadless <proj> <name> -import TBFENCE.EXE \
#       -processor x86:LE:16:RealMode -postScript ghidra_decompile_all.py [outdir]
# It writes one <function>.c per function and a combined dump, so you can grep
# the pseudo-C without the GUI.
#
# Runs under Ghidra's Jython 2.7, so: no f-strings, and never `print(a, b)` —
# that is a tuple dump in Python 2, and every print here is single-argument.
# It cannot be executed outside Ghidra, so it is syntax-checked here and no more;
# `run.sh` is the invocation that produced the notes in ANALYSIS.md.
# @category Analysis.Decompile
import os
import re
import json
from ghidra.app.decompiler import DecompInterface
from ghidra.util.task import ConsoleTaskMonitor

outdir = "ghidra_out"
args = getScriptArgs()
if args and len(args) > 0:
    outdir = args[0]
os.makedirs(outdir, exist_ok=True)

ifc = DecompInterface()
ifc.openProgram(currentProgram)
mon = ConsoleTaskMonitor()

SAFE = re.compile(r"[^A-Za-z0-9._-]+")


def slug(name, addr):
    """Filesystem-safe, collision-free name for one function.

    Used to be `name.replace("::","_").replace("/","_")` only. Two problems:
    DOS-era imports and thunks share names constantly (FUN_0000:1234 appears
    once per segment, and Ghidra gives every unnamed function the same shape of
    name), and the loop wrote `key + ".c"` unconditionally — so the *last*
    function of a given name silently won and every other decompilation was
    thrown away. Address in the filename makes the write one-to-one; the
    sanitiser now also covers characters a naive `::`/`/` swap misses (spaces,
    `<>`, `:` on the entry-point suffix)."""
    base = SAFE.sub("_", str(name))[:120]
    return "%s__%s" % (base, str(addr))


fm = currentProgram.getFunctionManager()
funcs = list(fm.getFunctions(True))  # true = forward; materialised so len() is honest
index = {}
c_combined = []
failed = 0

for func in funcs:
    name = func.getName()
    addr = func.getEntryPoint()
    results = ifc.decompileFunction(func, 30, mon)
    if results is not None and results.decompileCompleted():
        df = results.getDecompiledFunction()
        body = df.getC() if df is not None else None
    else:
        body = None
    if not body:
        failed += 1
        body = "// decompile failed for %s @ %s\n" % (name, addr)
    with open(os.path.join(outdir, slug(name, addr) + ".c"), "w") as f:
        f.write("// %s @ %s\n%s\n" % (name, addr, body))
    c_combined.append("// ===== %s @ %s =====\n%s" % (name, addr, body))
    index[str(addr)] = name

with open(os.path.join(outdir, "_combined.c"), "w") as f:
    f.write("\n\n".join(c_combined))
with open(os.path.join(outdir, "_index.json"), "w") as f:
    json.dump(index, f, indent=2)

# `len(funcs)` here used to be `len(getFunctions())` on a live FunctionIterator,
# which is unreliable once the loop has drained it (some Ghidra versions raise,
# some report 0), so the script's own success line could print a number that was
# never the count. `funcs` is a real list now, so this is exact. Single-argument
# `print` throughout: Jython 2.7 turns `print(a, b)` into a tuple dump.
print("Decompiled %d/%d functions into %s (%d failed)" % (len(funcs) - failed, len(funcs), outdir, failed))
ifc.dispose()
