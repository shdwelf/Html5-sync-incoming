# Boxentriq deep dive — resources, tool catalog, and the 26 recipes added to CyberChef Kitchen

Session branch: `arena/01a0d9c0-html5-sync-incoming` · researched 2026-09-25 ·
source: [boxentriq.com/resources](https://www.boxentriq.com/resources) and the
site's tool indexes (continuation of the earlier boxentriq research).

## 1. What was investigated

| Page | Status | What it gave us |
|---|---|---|
| `/resources` | full text captured | The "Resources for Puzzle Solvers" guide: discussion forums (r/cipher, r/codes, r/puzzles, Puzzling SE), CTFs (CTFtime, OverTheWire), armchair treasure hunts (Masquerade, The Secret, Golden Owl, TreasureHuntCache, r/ArmchairTreasure), (in)famous puzzles (Cicada 3301, 11B-X-1371, Kryptos, Voynich, Zodiac), plus links to the tool site |
| `/` (home) | full text captured | Site reorganisation into 11 categories: Alphabets, Analysis, Audio, Ciphers, Encodings, Hashing, Imaging, Math, Steganography, Text & Word Tools, Guides — each with a scope description |
| `/ciphers` | **full tool index captured** (49 tools) | The complete cipher recipe list |
| `/encodings` | **full tool index captured** (36 entries) | The complete encoding recipe list |
| `/alphabets`, `/text-tools`, `/steganography`, `/math`, etc. | index pages unreachable (fetch proxy failure) | Category scope taken from the home page descriptions; known members cross-checked against the app's existing ops (Braille/Morse/semaphore/tap-code/dancing-men all already present as `gcw*`/`morse` ops) |
| `/guides/cicada-3301-first-puzzle-walkthrough` | unreachable | The Liber Primus numeric core was implemented from the well-documented 2012 solution chain instead (see §4, `totient`) |

The two fully captured indexes are the recipe-bearing pages — everything else on
the site is reference tables (alphabet charts), file-analysis utilities
(barcode/QR scanners, EXIF, spectrograms, X.509), or wordplay helpers.

## 2. Gap analysis — Boxentriq ciphers (49) vs the kitchen

Already present in `webxdc/cyberchef/` before this change:
A1Z26, ADFGVX, AES, Affine, Atbash, Baconian, Beaufort, Bifid, Blowfish,
Book cipher, Caesar, Columnar transposition, Dancing Men, DES/3DES, Enigma,
Four-Square, Gronsfeld, Nihilist, One-Time Pad (as `xor`), Playfair, Porta,
Rail Fence, RC4, ROT13, ROT47, RSA, Scytale, Trifid, Vigenère (+ autokey as
`gcwVigenereAutokey`), XOR.

**Added this session (18 cipher recipes):**

| Recipe id | Boxentriq tool | Implementation |
|---|---|---|
| `adfgx` | ADFGX | keyed 5×5 square (I/J merged, X pad) + 5-column columnar with transposition key |
| `vigenereAutokey` | Vigenère Autokey | plaintext- and ciphertext-feedback autokey |
| `beaufortAutokey` | Beaufort Autokey | same, on Beaufort arithmetic |
| `doubleTransposition` | Double Transposition | two columnar rounds, separate keys |
| `grandpre` | Grandpré | N×N grid numbered 1..N², last digit repeated ⌊n/10⌋+1 times (K→00, T→000, Y→555 at 5×5) |
| `keyedCaesar` | Keyed Caesar | keyword-built monoalphabetic alphabet |
| `homophonic` | Numeric Homophonic | classic distribution A=1,2,3 … Z=51, round-robin or random homophone pick |
| `pigpen` | Pigpen | 13 keyed-pair glyph slots (plain 3×3 + 4 cross variants), keyword shuffles pairs |
| `rotN` | ROT-N | any integer shift, optional digit rotation |
| `rot5` / `rot18` | ROT5 / ROT18 | fixed digit / combined rotations |
| `routeTransposition` | Route Transposition | R×C grid, custom cell route or presets (rows/cols/diagonals/spiral) |
| `variantBeaufort` | Variant Beaufort | c=(P−K) / p=(C+K) — the documented "Vigenère decryption" equivalence |
| `cryptogram` | Cryptogram / Substitution | keyword or custom alphabet + frequency auto-solve vs E T A O I N S H R D L U M W F G Y P B V K C J X Q Z |
| `totient` | Cicada 3301 Totient | the Liber Primus chain: letters ↔ A1Z26 ↔ n-th prime ↔ φ (φ(p)=p−1) ↔ ordinal, four leg-selecting modes |
| `gematriaPrimus` | Gematria Primus | numeric core of the Liber Primus text with the prime/φ chain displayed per letter |

**Deferred (2):** AMSCO, Morbit, Pollux are real ciphers, but their exact
key-grid conventions (which row/column feeds which code letter, group sizes)
could not be verified offline during this session — the live tool pages were
unreachable. Rather than ship a guessed spec, they are left as documented
follow-ups: re-open `boxentriq.com/ciphers/amsco-cipher`, `/morbit-cipher`,
`/pollux-cipher` and add one `addOp` each following the house style.

## 3. Gap analysis — Boxentriq encodings (36) vs the kitchen

Already present: A1Z26, ASCII, Base32/64, Baudot (`gcwBaudot`), Hex,
Letters↔Numbers, Tap Code (`gcwTapCode`), Unicode/UTF-8, Phone Keypad
multi-tap (`gcwPhoneKeypad`), plus the existing stego/pixel ops.

**Added this session (8 encoding recipes):**

| Recipe id | Boxentriq tool | Implementation |
|---|---|---|
| `base58` | Base58 | Bitcoin alphabet (no 0/O/I/l) |
| `base62` | Base62 | three alphabet orders |
| `base85` | Base85 | Adobe ASCII85: 4 bytes ↔ 5 chars `!..u`, y/z short-group padding, optional `<~ … >` |
| `base100` | Base100 | byte ↔ one emoji from a fixed 256-glyph table (U+1F600–1F64F, U+1F300–1F393, U+2600–262B) |
| `bigIntText` | Text ↔ Big Integer | UTF-8 bytes ↔ big-endian decimal/hex integer |
| `geekCode` | Geek Code | `{K+}` expansion/compression with the standard legend |
| `pigLatin` | Pig Latin | cluster + "ay" / vowel + "yay", dictionary-assisted decode |
| `midiParse` | MIDI File Decoder | SMF header + per-track timeline (tempo, time sig, notes, CC) from hex |

**Deferred (1):** Nak-Nak duckspeak — the hex-digit→word table could not be
verified against the spec offline; same follow-up as §2.

**Out of scope for a single-file text kitchen (6):** Barcode Scanner,
QR Code Scanner, Pixel Values Extractor, Certificate Decoder (need image
decoders / X.509 stacks), Audio Spectrogram (needs audio processing),
Pattern-to-Letters (too generic to spec without the tool page).

## 4. From the other Boxentriq categories (2 extra recipes)

- `anagram` (Text & Word Tools) — anagram finder over a built-in list of
  2,601 common English words + two-word check mode.
- `primesFactor` (Math) — deterministic Miller–Rabin primality (base set
  valid to 3.3×10²⁴, probabilistic beyond) and full factorisation: trial
  division up to a configurable limit + Brent-accelerated Pollard ρ with
  batched GCD. Verified on a 26-digit semiprime (13-digit factors) and
  2¹²⁸−1.

## 5. Resulting package

- `webxdc/cyberchef/index.html`: **441 unique recipes** (415 before, +26 new,
  −0; the old "416 recipes" header was already off by one — the IC-gate ops
  are registered in a loop, which the old count missed).
- New "Boxentriq" category in the ops list, plus three recipe packs under
  **Recipe Pack → load**: *Cipher Classics*, *Cicada 3301*, *Encodings & Tools*.
- `dist/cyberchef.xdc` rebuilt with `webxdc/build-all.sh`; `webxdc_tool.py
  validate` passes 5/5.

## 6. Defects fixed along the way

1. **Duplicate op id `sha256`** — a stray "Crypto"-category registration
   (WebCrypto) shadowed the canonical "Hash"-category op; the duplicate call
   was removed (kept the Hash-category one that matches the other hash ops).
2. **Stale header count** — the "416 recipes" subtitle did not match the real
   registered count; now shows the verified 441.

## 7. Verification

The 26 new ops were written as a self-contained block and exercised before
splicing, then re-verified inside the assembled page:

- 44-test round-trip / known-answer suite (`/tmp/test_boxentriq.js` during
  development): all 44 pass — every cipher/encoding round-trips, known values
  checked (Grandpré K→00/T→000, ROT18 "Hello 12345"→"Uryyb 67890", ADFGX
  ciphertext alphabet, ASCII85 short-group padding, variant Beaufort =
  Vigenère decryption, totient A→2/B→3/C→5 and Z→101, MIDI timeline of a
  hand-built .mid, 26-digit semiprime factorisation with product check).
- Full page boot in a DOM-stubbed VM: the assembled `index.html` script runs
  to completion, registers 441 ops with 441 unique ids, renders the new
  category, and loads the Boxentriq packs (6 ops per classic pack).

## 8. Open follow-ups (next session)

1. Verify + implement **AMSCO, Morbit, Pollux, Nak-Nak** from the live tool pages.
2. Optionally extend `pigpen` with the classic 26-glyph chart (the 4×4 X-grid
   glyph set) once the chart source is re-fetched.
3. The three Boxentriq packs could also be referenced from
   `cryptoWikiIndex`/`tinyIntros` helper texts if those are maintained.
