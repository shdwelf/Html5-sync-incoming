#!/usr/bin/env python3
"""analyze_dos.py — lightweight static analysis for DOS-era executables.

Designed for reverse-engineering classic DOS security/shareware binaries such as
the PC-SIG "TbFence" (ThunderBYTE Fence) distribution. It is a *first-pass*
orienting tool (the thing you run before/alongside a full disassembler). It will:

  * Detect DOS MZ .EXE vs plain .COM.
  * Parse the MZ/EXE header (relocation table, load module size, header size).
  * Report NE (16-bit) vs LE (linear) vs PE extension markers where present.
  * Dump printable ASCII and Pascal-style length-prefixed strings with file
    offsets (offset is where you jump to in a hex editor / Ghidra Import).

Usage:
    python3 analyze_dos.py FILE [FILE ...]
    python3 analyze_dos.py TBFENCE.EXE
    python3 analyze_dos.py -s TBFENCE.EXE     # strings only
    python3 analyze_dos.py -m 12 TBFENCE.EXE  # min string length
"""
import sys
import struct

def parse_args(argv):
    minlen = 4
    strings_only = False
    files = []
    i = 1
    while i < len(argv):
        a = argv[i]
        if a == "-m":
            i += 1; minlen = int(argv[i])
        elif a == "-s":
            strings_only = True
        elif a.startswith("-"):
            pass
        else:
            files.append(a)
        i += 1
    return files, minlen, strings_only

def read_file(path):
    with open(path, "rb") as f:
        return f.read()

def is_mz(data):
    return len(data) >= 2 and data[:2] == b"MZ"

def parse_mz(data):
    """Return dict of the DOS MZ header fields we care about."""
    if len(data) < 0x40:
        return None
    (e_magic, e_cblp, e_cp, e_crlc, e_cparhdr, e_minalloc, e_maxalloc,
     e_ss, e_sp, e_csum, e_ip, e_cs, e_lfarlc, e_ovno) = struct.unpack("<HHHHHHHHHHHHHH", data[:28])
    return {
        "cblp_lastpage": e_cblp,
        "cp_pages": e_cp,          # module size in 512-byte pages
        "crlc_reloc": e_crlc,      # count of relocation table entries
        "cparhdr": e_cparhdr,      # header size in 16-byte paragraphs
        "minalloc": e_minalloc,
        "maxalloc": e_maxalloc,
        "ss": e_ss, "sp": e_sp,    # initial stack
        "csum": e_csum,
        "ip": e_ip, "cs": e_cs,    # entry point CS:IP
        "lfarlc": e_lfarlc,        # file offset of relocation table
        "ovno": e_ovno,
    }

def file_ext(mz):
    if len(mz) < 0x40:
        return "raw"
    ne = mz[0x40-0x40:][:2]
    # The NE/LE/PE signature lives right after the MZ stub, at the position
    # given by e_lfanew for PE, or immediately for NE/LE headers following the
    # stub. For NE/LE the header begins at the first paragraph boundary after
    # the DOS header+stub — a reliable heuristic is to look for 'NE'/'LE'/'PE'
    # within the header area.
    for probe in (0x40, 0x80, 0x100, 0x180, 0x200, 0x400):
        if mz[probe:probe+2] in (b"NE", b"LE", b"PE", b"LX", b"W3"):
            return mz[probe:probe+2].decode("latin1", "replace")
    return "MZ"

def guess_com(data):
    """Plain .COM files start with no MZ header and execute at offset 0x100."""
    return not is_mz(data)

def printable(s):
    return all(32 <= b < 127 or b in (9,) for b in s)

def ascii_strings(data, minlen):
    out = []
    cur = []
    start = 0
    for i, b in enumerate(data):
        if 32 <= b < 127:
            if not cur:
                start = i
            cur.append(b)
        else:
            if len(cur) >= minlen:
                out.append((start, bytes(cur).decode("latin1")))
            cur = []
    if len(cur) >= minlen:
        out.append((start, bytes(cur).decode("latin1")))
    return out

def pascal_strings(data, minlen):
    """DOS Borland/Pascal & many menus prefix short strings with a length byte."""
    out = []
    i = 0
    while i < len(data) - 1:
        ln = data[i]
        if 1 <= ln <= 100 and i + 1 + ln <= len(data):
            blob = data[i+1:i+1+ln]
            if printable(blob) and ln >= minlen and all(b != 0 for b in blob):
                out.append((i, blob.decode("latin1")))
                i += 1 + ln
                continue
        i += 1
    return out

def main():
    files, minlen, strings_only = parse_args(sys.argv)
    if not files:
        print(__doc__)
        sys.exit(2)
    for path in files:
        data = read_file(path)
        print("=" * 72)
        print(f"FILE: {path}   ({len(data)} bytes)")
        if is_mz(data):
            mz = parse_mz(data)
            if strings_only:
                print("-- strings only --")
                for off, s in ascii_strings(data, minlen):
                    print(f"  0x{off:06x}: {s}")
                continue
            print("type   : DOS MZ executable (16-bit x86)   ext:", file_ext(data))
            if mz:
                print(f"module : {mz['cp_pages']} x 512B pages, last-page {mz['cblp_lastpage']}B -> load ~{mz['cp_pages']*512-512+mz['cblp_lastpage']}B")
                print(f"header : {mz['cparhdr']} paragraphs ({mz['cparhdr']*16} bytes)")
                print(f"reloc  : {mz['crlc_reloc']} entries at file offset 0x{mz['lfarlc']:x}")
                print(f"min/max alloc: {mz['minalloc']}/{mz['maxalloc']} paragraphs")
                print(f"entry  : CS:IP = {mz['cs']:04x}:{mz['ip']:04x}   stack SS:SP = {mz['ss']:04x}:{mz['sp']:04x}")
                print(f"checksum: 0x{mz['csum']:04x} (non-zero means an overlay/tool set it)")
                print(f"overlay number: {mz['ovno']}")
        else:
            print("type   : plain DOS .COM (or raw data) — executes at CS:0100")
            if not data:
                print("  (empty file)")
        print("-- ASCII strings --")
        for off, s in ascii_strings(data, minlen):
            print(f"  0x{off:06x}: {s}")
        p = pascal_strings(data, minlen)
        if p and not strings_only:
            print("-- Pascal/length-prefixed strings (first 40) --")
            for off, s in p[:40]:
                print(f"  0x{off:06x}: [{len(s):>2}] {s}")

if __name__ == "__main__":
    main()
