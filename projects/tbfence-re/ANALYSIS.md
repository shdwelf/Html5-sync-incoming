# TbFence 4.00 — analysis findings (real binary)

This documents a first-pass static analysis of the actual **TbFence 4.00**
distribution (dated 1995-08-01, "Thunderbyte B.V.") run through the kit here.
The shareware binaries themselves are kept out of git (see `.gitignore`); the
analysis used `analyze_dos.py` (surveys in `analysis/*.survey.txt`) plus the
bundled documentation.

## Distribution set (13 files)
`AGENTS.DOC`, `ANTI-VIR.DAT`, `CONVERT.BAT`, `GATEWAY.EXE`, `INSTALL.BAT`,
`LICENSE.DOC`, `PRICE.LST`, `REGISTER.FRM`, `TBFENCE.DOC`, `TBFENCE.EXE`,
`TBFENCE.SYS`, `TBFKEY.EXE`, `WHATSNEW.400`.

## MZ header survey (real values)
| File | Bytes | Type | Entry | Reloc |
|------|-------|------|-------|-------|
| `TBFENCE.EXE` | 12,748 | DOS MZ, 0 reloc | CS:IP `0000:05E2`, SS:SP `0D0E:0400` | 0 |
| `TBFKEY.EXE`  | 1,586 | DOS MZ | CS:IP `0000:0000`, checksum `0xFE24` | 0 |
| `GATEWAY.EXE` | 45,072 | DOS MZ, header 2,656 B | (657 reloc entries) | 657 |

## Key findings
1. **It is the ThunderBYTE line, not standalone.** Strings in `GATEWAY.EXE`
   identify it as *"GateWay Diskette Authorization System - Version 1.00 for
   TBAV & TbFence"*, (c) 1992-93 ESaSS B.V. and DataSecura A/S, "Programmed by
   Frank Haugnes at DataSecura A/S". TbFence ships together with the
   ThunderBYTE Anti-Virus tooling.
2. **`TBFENCE.EXE` is a TSR + command tool.** Boot strings show the resident
   decryption driver ("Loading TbFence...", "This is not a TbFence machine!",
   "Security check failed! System might be infected!") and its command line
   drives the `query` / `encrypt` / `decrypt` operations that `CONVERT.BAT`
   and `GATEWAY.EXE` shell out to.
3. **`GATEWAY.EXE` orchestrates both products** via DOS calls, visible as plain
   strings: `TbScan.Exe A: nomem batch log ll=0`, `TbFence.Exe encrypt A:`,
   `decrypt A:`, `TBAV.Exe`. Its menu is Authorize/DeAuthorize drive A/B +
   administration. It refuses to authorize virus-likely diskettes (TbScan).
4. **Compiler fingerprint:** `GATEWAY.EXE` carries Borland/Turbo Pascal runtime
   strings (`TPWINDOW/TPSCREEN conflict`, `CRT/TPCRT conflict`, `No Error`,
   `File Not Found`) → built with Borland Pascal (Turbo Vision / Windows units).
5. **Anti-tamper / self-encryption:** large regions of `TBFENCE.EXE` and
   `TBFKEY.EXE` decode as non-printable, non-ASCII bytes between the readable
   boot strings. This is consistent with runtime-decrypted code+string blobs
   (ThunderBYTE self-checking/encryption to deter tampering and viruses).
6. **The crypto is intentionally weak (per the manual).** "The encryption
   scheme" section states TbFence is *"a transparent filter against
   unauthorized diskette transport,"* **not** strong encryption: by default it
   encrypts only the **system areas** of a diskette; full encryption requires a
   password starting with `*`, and even then the manual warns it is *"not the
   same degree of protection as a DES based encryption algorithm."* Modern
   takeaway: transparent on-disk filters keep the key reachable in the driver,
   so a local attacker can always recover the scheme.
7. **`ANTI-VIR.DAT`** is ThunderBYTE's checksum/cleaning/validation file
   ("Do NOT remove") — TbFence verifies the system against it ("Security check
   failed!").
8. **Documented exit codes** (only `encrypt`/`decrypt`/`query` supply one):
   `query` → 1 not encrypted, 2 encrypted, 3 encrypted but another password,
   10 disk read error; etc. These are what `CONVERT.BAT`/`GATEWAY.EXE` branch on.

## Next step (not run in-sandbox)
Full disassembly + decompiled pseudo-C via the headless Ghidra stage in
`run.sh` (`-processor x86:LE:16:RealMode`). Ghidra isn't installed in this
sandbox and its download is large, so the live decompile step wasn't executed
here; the strings + entry points above already give the analyst the exact
anchors to open in Ghidra (follow `query`/`encrypt`/`decrypt` command dispatch,
the 512-byte filter loop, and the "not a TbFence machine" security check).
