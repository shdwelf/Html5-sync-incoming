# Press Kit Reassembler (HTML5 + WASM)

An **original**, self-contained HTML5 tool that reassembles a variable-driven classic
DOS "electronic press kit" program. You type the content in a form; an embedded
**WebAssembly** engine encrypts the payloads; the app assembles a downloadable,
single-segment 16-bit DOS `.COM` (plus a plaintext `.DAT` resource mirror).

It is a faithful *engineering recreation* of how 1990s DOS press-kit floppies
stored their content (password gate + runtime XOR-decrypt of a text resource),
**not** a copy of any studio's promotional material. Default text is original
placeholder copy.

## What it produces
- `presskit.com` — a runnable DOS program:
  `title → prompt → check access code → "ACCESS GRANTED" → XOR-decrypt & print body 1
  → optionally print body 2 (hidden quote) → wait key → exit 0`, or
  `"*** ACCESS DENIED ***" → exit 1`.
- `presskit.dat` — plaintext mirror of the same sections (resource style).
- `.hex` log, an on-screen hex/ASCII dump, a WASM cipher lab (XOR / ROT13 / Caesar),
  and a WASM round-trip verification.

Run `presskit.com` in DOSBox or js-dos and type the access code.

## Files
```
presskit-reassembler.html   the app (self-contained: embeds wasm + code skeleton)
wasm/presskit.wat           WebAssembly cipher/CRC engine source
wasm/dos_stub.bin           assembled 16-bit runtime skeleton (build artifact)
wasm/build_dos_stub.py      assembles dos_stub.bin with Keystone (16-bit)
wasm/build.sh               compile .wat -> .wasm and refresh the base64 constant
```

## Rebuild the WebAssembly engine
```bash
pip install keystone-engine          # only for the DOS stub build
cd presskit-reassembler/wasm
./build.sh                           # wat2wasm (npm pkg `wabt`) -> injects base64 into the HTML
```

## How the DOS runtime stays "static" while the text varies
A fixed 151-byte skeleton reaches **all** variable data through an 8-word
"runtime control block" (RCB) immediately after the code; the HTML app writes real
`.COM` addresses into the RCB. The two `xor al,imm` decryptor immediates are the
only code bytes that change (to the chosen XOR key). Verified by disassembly
(Capstone) and by executing the output under a small DOS-semantics interpreter.

## Boundaries
An original educational retrocomputing tool. Reproduces no studio's promotional
copy and is not affiliated with or endorsed by any film studio or brand.
