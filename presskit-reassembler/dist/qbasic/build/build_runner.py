#!/usr/bin/env python3
"""Build dist/qbasic/qbasic-runner.html from the template, injecting the WASM
engine and the DOS code skeleton that are already embedded (and verified) in the
main presskit-reassembler.html, so there is no risk of transcription error."""
import os, re

root = os.path.dirname(os.path.abspath(__file__))
main_html = os.path.join(root, "..", "..", "..", "presskit-reassembler.html")
tpl = os.path.join(root, "runner.template.html")
out = os.path.join(root, "..", "qbasic-runner.html")

h = open(main_html, encoding="utf-8").read()

wasm = re.search(r'const WASM_B64 = "([^"]*)"', h).group(1)
code = re.search(r'const CODE = (\[[^\n]*\]);', h).group(1)

t = open(tpl, encoding="utf-8").read()
t = t.replace("@@WASM@@", wasm).replace("@@CODE@@", code)
open(out, "w", encoding="utf-8").write(t)
print("wrote", out, os.path.getsize(out), "bytes")
