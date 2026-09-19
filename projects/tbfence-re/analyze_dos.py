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
        if a in ("-h", "--help"):
            print(__doc__)
            sys.exit(0)
        elif a == "-m":
            if i + 1 >= len(argv):
                sys.exit("analyze_dos.py: -m needs a value")
            try:
                minlen = int(argv[i + 1])
            except ValueError:
                sys.exit(f"analyze_dos.py: -m needs an integer, got {argv[i + 1]!r}")
            i += 1
        elif a == "-s":
            strings_only = True
        elif a.startswith("-"):
            # A trailing bare `-` used to be swallowed silently, so a typo like
            # `-string` reported nothing wrong and produced normal output.
            sys.exit(f"analyze_dos.py: unknown option {a!r} (try --help)")
        else:
            files.append(a)
        i += 1
    return files, minlen, strings_only

def read_file(path):
    with open(path, "rb") as f:
        return f.read()

def is_mz(data):
    return len(data) >= 2 and data[:2] == b"MZ"

def load_size(mz):
    """Load-module size in bytes from (cp_pages, cblp_lastpage).

    Per the MZ format, cblp == 0 means the last page is FULL, not empty. The
    old inline expression `cp*512-512+cblp` was right for cblp != 0 but reported
    every image whose size is an exact multiple of 512 as 512 bytes short.
    """
    cp, cblp = mz["cp_pages"], mz["cblp_lastpage"]
    return cp * 512 if cblp == 0 else (cp - 1) * 512 + cblp


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

# e_lfanew: DWORD at 0x3C giving the file offset of the new-format header.
E_LFANEW = 0x3C
NEW_EXTS = (b"NE", b"LE", b"LX", b"PE", b"W3")


def file_ext(data):
    """Return the new-format signature (NE/LE/LX/PE/W3) or 'MZ'/'raw'.

    This used to probe a fixed list of offsets (0x40, 0x80, 0x100, ...) and take
    the first 2-byte match, which is wrong in both directions: a real header at
    an unlisted offset was missed, and any 'NE'/'PE' byte pair inside the DOS
    stub was reported as the header. The offset is stored in the header itself,
    at e_lfanew (0x3C) -- read it instead of guessing.

    The old body also opened with a dead `ne = mz[0x40-0x40:][:2]` (an
    always-equal-to-`data[:2]` slice of the MZ magic) and took a parameter named
    `mz` that callers passed the whole file into.
    """
    if len(data) < 0x40:
        return "raw"
    if data[:2] != b"MZ":
        return "raw"
    (lfanew,) = struct.unpack("<I", data[E_LFANEW:E_LFANEW + 4])
    if lfanew and lfanew + 2 <= len(data):
        sig = data[lfanew:lfanew + 2]
        if sig in NEW_EXTS:
            return sig.decode("latin1", "replace")
    # Some DOS-era tools leave e_lfanew zero but still append a new header at a
    # paragraph boundary right after the stub. Fall back to scanning only the
    # stub region, and say so, rather than trusting a fixed offset blindly.
    hdr_end = min(len(data), 0x400)
    for probe in range(0x40, hdr_end - 1, 0x10):
        if data[probe:probe + 2] in NEW_EXTS:
            return data[probe:probe + 2].decode("latin1", "replace") + "?"
    return "MZ"

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
                print(f"module : {mz['cp_pages']} x 512B pages, last-page {mz['cblp_lastpage']}B -> load ~{load_size(mz)}B")
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
