# decode_cmb.py — C.Y.P.H.E.R. "Operation Wildlife" .CMB decoder

A small tool that decodes the word/animal lists stored in the `.CMB` database
files of the 1991 DOS educational game **The Secret Codes of C.Y.P.H.E.R.:
Operation Wildlife** (Tanager Software).

## The encoding it reverses
Inspecting the real `MAMMAL1/2/3.CMB` files shows names are stored as plain
lowercase letters where the **final letter of each name has bit 7 (0x80) set**,
and that high bit doubles as the word delimiter — so names are packed back to
back with no separator:

```
bytes   : 65 67 72 65 f4  6d 61 6c 6c 61 72 e4  63 6f 6e 64 6f f2 ...
as ascii: e  g  r  e  .   m  a  l  l  a  r  .   c  o  n  d  o  .
decode  : (0xf4&0x7f)='t'  (0xe4&0x7f)='d'      (0xf2&0x7f)='r'
          "egret"          "mallard"            "condor"
```

## Usage
```bash
python3 decode_cmb.py MAMMAL1.CMB                 # all decoded alphabetic tokens
python3 decode_cmb.py --minlen 4 MAMMAL1.CMB      # only words >= 4 letters
python3 decode_cmb.py --max 40 MAMMAL1.CMB        # first 40 tokens
python3 decode_cmb.py --unique MAMMAL1.CMB        # sorted, de-duplicated
```

## Notes
- `MAMMAL1.CMB` yields the cleanest result: bird names (`egret, mallard,
  condor, falcon, puffin, ... kingfisher, nuthatch`) then constellation names
  (`Ursa Major, Scorpius, Andromeda, Pegasus, Perseus, Aquarius, Gemini ...`).
- `MAMMAL2.CMB` and `MAMMAL3.CMB` also embed binary graphics/compressed data,
  so their decoded streams include short spurious tokens — prefer `--minlen 4`
  and eyeball for real dictionary words.
- The tool is data-agnostic and only depends on the standard library.
