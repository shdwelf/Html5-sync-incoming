# ghidra_decompile_all.py
# Ghidra headless post-script: import your DOS binary then run
#   analyzeHeadless <proj> <name> -import TBFENCE.EXE \
#       -processor x86:LE:16:RealMode -postScript ghidra_decompile_all.py [outdir]
# It writes one <function>.c per function and a combined dump, so you can grep
# the pseudo-C without the GUI.
# @category Analysis.Decompile
import os
import json
from ghidra.app.decompiler import DecompInterface
from ghidra.util.task import ConsoleTaskMonitor

outdir = "ghidra_out"
if len(getScriptArgs()) > 0:
    outdir = getScriptArgs()[0]
os.makedirs(outdir, exist_ok=True)

ifc = DecompInterface()
ifc.openProgram(currentProgram)
mon = ConsoleTaskMonitor()

fm = currentProgram.getFunctionManager()
funcs = fm.getFunctions(True)  # true = forward
index = {}
c_combined = []

for func in funcs:
    name = func.getName()
    addr = func.getEntryPoint()
    results = ifc.decompileFunction(func, 30, mon)
    body = results.getDecompiledFunction().getC() if results.decompileCompleted() else "// decompile failed"
    key = name.replace("::", "_").replace("/", "_")
    with open(os.path.join(outdir, key + ".c"), "w") as f:
        f.write("// %s @ %s\n%s\n" % (name, addr, body))
    c_combined.append("// ===== %s @ %s =====\n%s" % (name, addr, body))
    index[str(addr)] = name

with open(os.path.join(outdir, "_combined.c"), "w") as f:
    f.write("\n\n".join(c_combined))
with open(os.path.join(outdir, "_index.json"), "w") as f:
    json.dump(index, f, indent=2)

print("Decompiled %d functions into %s" % (len(funcs), outdir))
ifc.dispose()
