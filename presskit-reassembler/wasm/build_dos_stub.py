#!/usr/bin/env python3
"""
build_dos_stub.py -- Assemble the static 16-bit x86 runtime skeleton for the
Press Kit Reassembler.

The output is a *parameter-independent* DOS code skeleton.  All variable data
(title, prompts, password, encrypted body sections, input buffer) is reached
through a fixed "runtime control block" (RCB) of pointer words that sits
immediately after the code.  The HTML5 app writes the real data addresses into
the RCB at runtime, so this skeleton never changes no matter what text the
user types in the form.

  Code layout (single-segment .COM, entry at 0x100):
    [0, L)          code skeleton            (this file's bytes)
    [L, L+16)       RCB : 8 pointer words    (filled in by the HTML5 app)
    [L+16, ...)     data strings             (appended by the HTML5 app)

Requires the Python `keystone-engine` package:
    pip install keystone-engine   (add --break-system-packages if needed)
"""
from keystone import Ks, KS_ARCH_X86, KS_MODE_16

# Word index within the RCB used by the skeleton code (0-based pointer slots).
RCB_TITLE, RCB_PROMPT, RCB_GRANTED, RCB_DENIED, RCB_PASS, RCB_BUF, RCB_BODY1, RCB_BODY2 = range(8)

STUB = f"""
    mov  ax, 0003h
    int  10h                 ; 80x25 colour text mode
    mov  bp, %RCB%           ; DS==SS in .COM, so bp-relative == our data base

    ; ---- print title ----
    mov  dx, [bp+{2*RCB_TITLE}]
    mov  ah, 09h
    int  21h

    ; ---- print prompt ----
    mov  dx, [bp+{2*RCB_PROMPT}]
    mov  ah, 09h
    int  21h

    ; ---- buffered input (INT 21h AH=0Ah), buffer at RCB_BUF ----
    mov  dx, [bp+{2*RCB_BUF}]
    mov  ah, 0Ah
    int  21h

    ; ---- case-insensitive compare of typed text vs stored password ----
    mov  si, [bp+{2*RCB_BUF}]
    add  si, 2               ; typed chars start after [max, len]
    mov  di, [bp+{2*RCB_PASS}]
cmp_loop:
    mov  bl, [di]
    cmp  bl, 0x24            ; '$' = end of stored password -> all matched
    je   granted
    mov  al, [si]
    cmp  al, 0x0D            ; Enter pressed before password done -> fail
    je   denied
    cmp  al, 'A'
    jb   cmp_skip
    cmp  al, 'Z'
    ja   cmp_skip
    or   al, 0x20            ; force lowercase
cmp_skip:
    cmp  al, bl
    jne  denied
    inc  si
    inc  di
    jmp  cmp_loop

granted:
    mov  dx, [bp+{2*RCB_GRANTED}]
    mov  ah, 09h
    int  21h

    ; ---- XOR-decrypt body 1 in place, then print ----
    mov  si, [bp+{2*RCB_BODY1}]
dec1:
    mov  al, [si]
    cmp  al, 0x24
    je   dec1_done
    xor  al, 0x5A            ; runtime key
    mov  [si], al
    inc  si
    jmp  dec1
dec1_done:
    mov  dx, [bp+{2*RCB_BODY1}]
    mov  ah, 09h
    int  21h

    ; ---- optional body 2 (only if its RCB pointer is non-zero) ----
    mov  si, [bp+{2*RCB_BODY2}]
    cmp  word ptr [bp+{2*RCB_BODY2}], 0
    je   waitkey
dec2:
    mov  al, [si]
    cmp  al, 0x24
    je   dec2_done
    xor  al, 0x5A
    mov  [si], al
    inc  si
    jmp  dec2
dec2_done:
    mov  dx, [bp+{2*RCB_BODY2}]
    mov  ah, 09h
    int  21h

waitkey:
    mov  ah, 0
    int  16h                ; wait for a key
    mov  ah, 4Ch
    mov  al, 0
    int  21h

denied:
    mov  dx, [bp+{2*RCB_DENIED}]
    mov  ah, 09h
    int  21h
    mov  ah, 4Ch
    mov  al, 1
    int  21h
"""


def assemble(source: str) -> bytes:
    # Keystone x86 can be picky about trailing "; comment" tokens; strip them
    # (comments are only informational in this generated skeleton).
    clean = "\n".join(line.split(";")[0].rstrip() for line in source.splitlines())
    ks = Ks(KS_ARCH_X86, KS_MODE_16)
    enc, _count = ks.asm(clean)
    return bytes(enc)


def build() -> bytes:
    # Pass 1 with a placeholder RCB address to learn the exact code length.
    once = assemble(STUB.replace("%RCB%", "0x0000"))
    rcb_addr = 0x100 + len(once)          # .COM: file byte o lives at 0x100+o
    code = assemble(STUB.replace("%RCB%", hex(rcb_addr)))
    assert len(code) == len(once), "code length changed between passes"
    return code


if __name__ == "__main__":
    code = build()
    rcb = 0x100 + len(code)
    print(f"code length   : {len(code)} bytes")
    print(f"RCB base (bp) : 0x{rcb:04X}")
    print(f"byte array    : [{', '.join('0x%02x' % b for b in code)}]")
    with open("dos_stub.bin", "wb") as f:
        f.write(code)
    print("wrote dos_stub.bin")
