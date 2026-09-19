#!/usr/bin/env python3
"""decode_cmb.py — decode the animal/word lists inside a C.Y.P.H.E.R.
"Operation Wildlife" .CMB database file.

How the encoding works (found by inspecting the real MAMMAL1/2/3.CMB files):
  * Names (eg "egret", "mallard") are stored as plain lowercase letters.
  * Each name's FINAL letter has bit 7 (0x80) OR'd into it, and that high bit
    is what marks the end of the name — so names are packed back-to-back with
    no separator byte:
        egre 0xF4 | mallar 0xE4 | condo 0xF2 | ...
        (0xF4 & 0x7F) = 't'  -> "egret"
        (0xE4 & 0x7F) = 'd'  -> "mallard"
        (0xF2 & 0x7F) = 'r'  -> "condor"

The .CMB files also embed binary data (graphics etc.), so the decoder walks the
byte stream, reconstructs only clean alphabetic words, and reports both the raw
tokens and the decoded names.

Usage:
    python3 decode_cmb.py MAMMAL1.CMB [MAMMAL2.CMB ...]
    python3 decode_cmb.py --unique MAMMAL1.CMB   # sorted de-duplicated names
    python3 decode_cmb.py --max 40 MAMMAL1.CMB   # first 40 tokens only
"""
import sys
import re
import signal

# Allow a clean `... | head` without a BrokenPipeError traceback. SIGPIPE only
# exists on POSIX -- referencing it unconditionally made the tool raise
# AttributeError at import time on Windows, before it could do anything.
if hasattr(signal, "SIGPIPE"):
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)

def decode_tokens(data):
    """Yield decoded name tokens found in a .CMB byte stream."""
    word = []
    i = 0
    n = len(data)
    while i < n:
        b = data[i]
        if 0x61 <= b <= 0x7A or 0x41 <= b <= 0x5A:
            # plain ASCII letter -> part of the current name
            word.append(chr(b))
        elif b >= 0x80:
            low = b & 0x7F
            # if clearing bit7 yields a letter, it's this name's final letter
            if (0x61 <= low <= 0x7A) or (0x41 <= low <= 0x5A):
                word.append(chr(low))
            # either way the high bit ends this name
            if word:
                yield "".join(word)
                word = []
        else:
            # any other byte (digit, punctuation, binary) ends the name
            if word:
                yield "".join(word)
                word = []
        i += 1
    if word:
        yield "".join(word)

def looks_like_name(tok, min_len=3):
    """A plausible animal/word: >=min_len letters, only alphabetic."""
    return len(tok) >= min_len and re.fullmatch(r"[A-Za-z]+", tok)

def take_int(argv, i, flag):
    """Read the integer argument for `flag`, or exit with a usable message.

    `--max` / `--minlen` used to do `int(argv[i])` with no bounds or type check,
    so a trailing flag gave IndexError and a non-numeric one gave a ValueError
    traceback instead of an error message.
    """
    if i + 1 >= len(argv):
        sys.exit(f"decode_cmb.py: {flag} needs a value")
    try:
        return int(argv[i + 1]), i + 1
    except ValueError:
        sys.exit(f"decode_cmb.py: {flag} needs an integer, got {argv[i + 1]!r}")


def main(argv):
    min_len = 3
    unique = False
    max_show = None
    files = []
    i = 1
    while i < len(argv):
        a = argv[i]
        if a in ("-h", "--help"):
            print(__doc__)
            return 0
        elif a == "--unique":
            unique = True
        elif a == "--max":
            max_show, i = take_int(argv, i, "--max")
        elif a == "--minlen":
            min_len, i = take_int(argv, i, "--minlen")
        elif a.startswith("-"):
            # Silently swallowing unknown flags meant `--uniq` (a typo) did
            # nothing at all and still exited 0.
            sys.exit(f"decode_cmb.py: unknown option {a!r} (try --help)")
        else:
            files.append(a)
        i += 1

    if not files:
        print(__doc__, file=sys.stderr)
        return 2

    rc = 0
    for path in files:
        try:
            with open(path, "rb") as fh:      # was an unclosed open()
                data = fh.read()
        except OSError as e:
            print(f"decode_cmb.py: cannot read {path}: {e}", file=sys.stderr)
            rc = 1
            continue
        tokens = list(decode_tokens(data))
        names = [t for t in tokens if looks_like_name(t) and len(t) >= min_len]
        print(f"==== {path}  ({len(data)} bytes) ====")
        print(f"decoded alphabetic tokens (>= {min_len} chars): {len(names)}")
        shown = sorted(set(names)) if unique else names
        if max_show:
            shown = shown[:max_show]
        for w in shown:
            print("  " + w)
    return rc

if __name__ == "__main__":
    sys.exit(main(sys.argv))
