# TbFence (ThunderBYTE Fence) — DOS reverse-engineering kit

A first-pass static-analysis kit for the classic DOS disk-encryption utility
**TbFence**, distributed on the PC-SIG Library / "Softwarová záchrana" CDs.
This kit was built after pulling the distribution's real batch files and
metadata from the archives. It does NOT ship the copyrighted binaries — you
obtain those yourself (see *Get the files*), drop them in this folder, and run
the included analyzer. It will then drive Ghidra headlessly if you want the
full disassembly + pseudo-C.

## One-command pipeline
```bash
cd tbfence-re
./run.sh                 # analyzes every .exe/.com in this folder
./run.sh TBFENCE.EXE GATEWAY.EXE   # or specific files
GHIDRA_HOME=/opt/ghidra ./run.sh   # enable the Ghidra decompile stage
```
`run.sh`:
1. runs `analyze_dos.py` on each binary → `analysis/<file>.survey.txt`, then
2. if Ghidra is found, imports each binary at **`x86:LE:16:RealMode`** and runs
   the headless post-script → decompiled pseudo-C under `analysis/ghidra/<file>/`.

It degrades gracefully — no binaries prints the exact URLs to fetch them (exit 0);
no Ghidra runs the survey only with a hint to set `GHIDRA_HOME`.

## What TbFence is (ground truth from the real files)

From `FILE_ID.DIZ` (fetched from the archive):

> **TbFence** — system security — is a single- or multi-PC file and data
> security system. It works in the background to encrypt data copied to a
> floppy.

It is a **transparent floppy-disk encryption TSR** from the ESaSS **ThunderBYTE**
family (same lineage as the TbAV anti-virus line). Everything written to a
"fenced" diskette is encrypted on the fly; reads are decrypted transparently.
An un-fenced (foreign) diskette is refused.

`CONVERT.BAT` (fetched from the archive) shows the real command surface of the
main tool:

```bat
tbfence query   a:     rem returns exit codes (2 = not a TbFence disk, ...)
tbscan  a: nomem batch log ll=0      rem ThunderBYTE virus scan first
tbfence encrypt a:     rem convert the diskette to TbFence format
```

So `TBFENCE.EXE` is **not** purely an installer — it is a multi-command utility:
an interactive menu when run with no arguments, plus `query <drive>` and
`encrypt <drive>` sub-commands with documented `errorlevel`/exit-code contract
(`0 ok, 2 not-fenced, 10 read err, 11 write err, 255 no-TbFence/not-loaded`).

## Distribution file manifest (from the archive listing, 12 files, 1994)

| File | Size | Role (from docs/batch) |
|------|------|------------------------|
| `TBFENCE.EXE` | 12,248 B | Main tool: install menu + `query`/`encrypt`/`convert` commands (entry point to reverse) |
| `TBFENCE.SYS` | 192 B | Tiny CONFIG.SYS line-driver/config for the TSR |
| `TBFKEY.EXE` | 1,586 B | Key/password helper (gateway key handling) |
| `GATEWAY.EXE` | 45,072 B | Administrator "gateway" station tool (largest component) |
| `CONVERT.BAT` | 2,358 B | Sample scan-then-convert workflow (fetched, text) |
| `INSTALL.BAT` | 3,263 B | Installer shell — validates, copies, launches menu (fetched, text) |
| `LICENSE.DOC` / `TBFENCE.DOC` / `AGENTS.DOC` | | Manuals (TBFENCE.DOC = 28 KB manual) |
| `REGISTER.FRM` / `REGISTER.HFL` / `FILE_ID.DIZ` | | Shareware registration/descriptor |

## Get the files (fetch the distribution yourself)

From the archive the batch files came from:

```
http://annex.retroarchive.org/cdrom/psl-v3n4/UTILS/DOS/SECURITY/TBFENCE/TBFENCE.EXE
http://annex.retroarchive.org/cdrom/psl-v3n4/UTILS/DOS/SECURITY/TBFENCE/TBFENCE.SYS
http://annex.retroarchive.org/cdrom/psl-v3n4/UTILS/DOS/SECURITY/TBFENCE/TBFKEY.EXE
http://annex.retroarchive.org/cdrom/psl-v3n4/UTILS/DOS/SECURITY/TBFENCE/GATEWAY.EXE
```

The full CD (with the same tree) is on the Internet Archive item
`spidla-sz` ("Softwarová záchrana", Špidla, 1997) — the original files live
inside the CD image under `UTILS/DOS/SECURITY/TBFENCE`.

> **Note for this sandbox:** outbound network here only reaches GitHub-hosted
> hosts and package registries; archive.org and the retroarchive annex drop
> non-allowlisted transfers, so I could not pull the raw `.EXE` bytes into this
> environment to run the disassembly live. Everything else (listing, batch
> files, file IDs, and the tool's documented behaviour) was fetched and is real.

## How to reverse it

### Step 0 — orient (no tools needed)
```bash
python3 analyze_dos.py TBFENCE.EXE          # header, ext, entry CS:IP, strings
python3 analyze_dos.py -s -m 5 GATEWAY.EXE  # string survey of the big file
```
`TBFENCE.EXE` is a **12 KB DOS MZ executable** — small enough that Ghidra will
auto-analyse it almost instantly. `TBFKEY.EXE` (1.5 KB) is an even friendlier
warm-up target; `GATEWAY.EXE` (45 KB) is the meaty one.

### Step 1 — import into Ghidra (headless)
```bash
# needs the OS 'java' + Ghidra. Adjust the path to your Ghidra install.
GHIDRA_HOME=/opt/ghidra   # or wherever you unpacked it
$GHIDRA_HOME/support/analyzeHeadless /tmp/tbfproj Tbf -import TBFENCE.EXE \
    -processor x86:LE:16:RealMode -postScript $(pwd)/ghidra_decompile_all.py
```
Notes for a 16-bit DOS binary in Ghidra:
- Set the language to **x86:LE:16:RealMode** (Ghidra may auto-detect MZ, but
  real-mode DOS needs it explicit).
- The MZ loader will parse the relocation table automatically; the DOS entry
  `CS:IP` becomes the program entry.
- Follow the `query`/`encrypt` command strings and their exit-code returns —
  these mark the interesting control flow.

### Step 2 — what to look for (anchors)
1. **The `query a:` / `encrypt a:` / `convert` command dispatch** — a string +
   a jump table; following it reveals the whole command contract.
2. **The encryption routine** — where a sector buffer is XORed / permuted by a
   key. Look for loops over 512-byte buffers and key material in the data
   segment. (Educational: modern takeaway is that on-the-fly transparent
   crypto needs the key reachable in RAM, so a determined local attacker can
   always recover it — exactly why TbFence says it "deters, not stops".)
3. **The diskette "foreign/un-fenced" rejection** — a marker/id byte or
   signature it reads from the boot/root to decide whether a diskette is fenced.
4. **Exit-code returns** used by `CONVERT.BAT` (2,10,11,255).

### Step 3 — decompile
`ghidra_decompile_all.py` (in this folder) exports every function as pseudo-C.
For a faithful re-check of bytecode you'd instead decompile with CFR/Fernflower
— but that's for Java; for DOS x86, Ghidra's own decompiler is the right tool.

## Files in this kit
- `run.sh` — the whole analyze + Ghidra pipeline in one command (see above).
- `analyze_dos.py` — MZ/.COM header + string survey tool (run on the fetched EXEs).
- `ghidra_decompile_all.py` — Ghidra headless post-script that decompiles all functions to C.
- `README.md` — this dossier.

## Integrity
This is **your own reverse-engineering study** of a 1994 shareware utility that
you legally obtain from the PC-SIG/archive distribution. The kit ships no
binaries and no third-party code. Decompiling software you possess for
interoperability/security research is a routine, legal activity in most
jurisdictions (and 1994 shareware's EULA is long dead).
