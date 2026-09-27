"""English syllable estimation for haiku validation.

Two tiers:

* If the optional ``cmudict`` package is importable (``pip install cmudict``),
  words found in the CMU Pronouncing Dictionary are counted from their phoneme
  stress markers — exact for those words; several pronunciations give a
  min/max range.
* Everything else falls back to a rule-based estimator: vowel-group counting
  with the usual corrections (silent ``e``, ``-ed``/``-es`` endings, syllabic
  ``-le``, common vowel splits such as *pi-a-no* / *ra-di-o* / *flu-id*) plus a
  curated exception table for frequent words the rules get wrong.

Every public function returns a ``(low, high)`` range rather than one number,
because English syllable counts are genuinely ambiguous for words such as
*fire*, *hour*, *every* or *evening* — and haiku poets disagree about them.
The haiku detector treats a target count anywhere inside the range as a match.
"""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Dict, List, Tuple

Range = Tuple[int, int]

# --------------------------------------------------------------------------- #
# Optional CMU dictionary
# --------------------------------------------------------------------------- #
try:  # pragma: no cover - depends on the environment
    import cmudict as _cmudict  # type: ignore

    _CMU: Dict[str, List[List[str]]] = _cmudict.dict()
except Exception:  # pragma: no cover
    _CMU = {}


def cmu_available() -> bool:
    """True when the CMU Pronouncing Dictionary is being used for known words."""
    return bool(_CMU)


def backend_name() -> str:
    return "cmudict+rules" if _CMU else "rules"


# --------------------------------------------------------------------------- #
# Exception tables
# --------------------------------------------------------------------------- #
# Words where the rules are wrong, or where usage is genuinely split.
# A pair (lo, hi) is a range; a single int is exact.
_EXCEPTIONS_RAW: Dict[str, object] = {
    # short words the vowel-group rule under-counts
    "ago": 2, "any": 2, "ivy": 2, "era": 2, "ion": 2, "leo": 2, "eon": 2,
    "iou": 3, "ohio": 3, "idea": 3, "ideas": 3, "area": 3, "areas": 3,
    # -oe- / -ie- / -ui- / -ia- splits
    "poem": 2, "poems": 2, "poet": 2, "poets": 2, "poetry": 3, "poetic": 3,
    "quiet": 2, "quietly": 3, "quietness": 3, "quieter": 3, "diet": 2,
    "riot": 2, "ruin": 2, "ruins": 2, "ruined": 2, "suicide": 3,
    "science": 2, "sciences": 3, "conscience": 2, "patience": 2,
    "ancient": 2, "ocean": 2, "oceans": 2, "lion": 2, "lions": 2,
    "genius": 2, "someone": 2, "anyone": 3, "people": 2, "peoples": 2,
    "forever": 3, "makeup": 2, "somersault": 3,
    "giant": 2, "giants": 2, "firefly": (2, 3), "fireflies": (2, 3),
    "fireworks": (2, 3), "fireplace": (2, 3), "fireside": (2, 3),
    "create": 2, "created": 3, "creates": 2, "creating": 3, "creation": 3,
    "creative": 3, "creature": 2, "creatures": 2, "react": 2, "reaction": 3,
    "cereal": 3, "linear": 3, "nuclear": 3, "theatre": 3, "theater": 3,
    "isle": 1, "aisle": 1, "isles": 1, "aisles": 1, "genre": 1,
    "tuesday": 2, "wednesday": 2, "february": (3, 4), "january": 4,
    # -ed that is a syllable
    "naked": 2, "wicked": 2, "crooked": 2, "rugged": 2, "ragged": 2,
    "jagged": 2, "sacred": 2, "hatred": 2, "kindred": 2, "wretched": 2,
    "dogged": 2, "learned": (1, 2), "beloved": (2, 3), "aged": (1, 2),
    "blessed": (1, 2), "cursed": (1, 2), "winged": (1, 2), "legged": (1, 2),
    # eye / -ye
    "eye": 1, "eyes": 1, "eyed": 1, "dye": 1, "bye": 1, "rye": 1, "lye": 1,
    # function words
    "the": 1, "they": 1, "you": 1, "your": 1, "youth": 1, "queue": 1,
    "clothes": 1, "aches": 1, "ached": 1,
    # contractions
    "don't": 1, "won't": 1, "can't": 1, "ain't": 1, "shan't": 1,
    "didn't": 2, "isn't": 2, "wasn't": 2, "aren't": (1, 2), "weren't": (1, 2),
    "couldn't": 2, "wouldn't": 2, "shouldn't": 2, "hasn't": 2, "haven't": 2,
    "hadn't": 2, "doesn't": 2, "mustn't": 2, "needn't": 2, "mightn't": 2,
    # -ing after a vowel sound
    "being": 2, "seeing": 2, "fleeing": 2, "freeing": 2, "agreeing": 3,
    "going": 2, "doing": 2, "knowing": 2, "flowing": 2, "growing": 2,
    "glowing": 2, "snowing": 2, "blowing": 2, "showing": 2, "rowing": 2,
    "throwing": 2, "owing": 2, "sowing": 2, "bowing": 2, "skiing": 2,
    # -el / -ewel
    "cruel": 2, "fuel": 2, "duel": 2, "jewel": 2, "vowel": 2, "towel": 2,
    "bowel": 2, "trowel": 2,
    # borrowed words with a spoken final e
    "naive": 2, "cafe": 2, "café": 2, "resume": (2, 3), "recipe": 3,
    "recipes": 3, "apostrophe": 4, "catastrophe": 4, "hyperbole": 4,
    "epitome": 4, "sesame": 3, "karate": 3, "acne": 2, "adobe": 3,
    "anemone": 4, "calliope": 4, "penelope": 4, "simile": 3, "finale": 3,
    "psyche": 2, "vitae": 2, "reggae": 2, "algae": 2, "coyote": 3, "coyotes": 3,
    "chaos": 2, "cocoa": 2, "boa": 2, "stoic": 2, "colonel": 2,
    "iron": 2, "irony": 3, "lawyer": 2, "prayer": (1, 2), "player": 2,
    "layer": 2, "mayor": 2, "buyer": 2, "flyer": 2,
    # -en / -on endings after a vowel group (rule counts them, keep exact)
    "heaven": 2, "seven": 2, "eleven": 3, "given": 2, "even": 2, "oven": 2,
    "raven": 2, "haven": 2, "woven": 2, "driven": 2, "eaten": 2, "beaten": 2,
    "often": 2, "listen": 2, "glisten": 2, "fasten": 2, "hasten": 2,
    "moisten": 2, "soften": 2, "chosen": 2, "frozen": 2, "broken": 2,
    "spoken": 2, "taken": 2, "shaken": 2, "woken": 2, "token": 2, "open": 2,
    "opens": 2, "opened": 2, "happen": 2, "happened": 2, "happens": 2,
    "garden": 2, "burden": 2, "golden": 2, "wooden": 2, "kitchen": 2,
    "chicken": 2, "children": 2, "children's": 2, "stolen": 2, "swollen": 2,
    "fallen": 2, "pollen": 2, "heron": 2, "herons": 2, "lemon": 2,
    "salmon": 2, "women": 2, "linen": 2, "omen": 2, "amen": 2,
    # genuinely split usage — reported as a range
    "chocolate": (2, 3), "camera": (2, 3), "family": (2, 3),
    "every": (2, 3), "everything": (3, 4), "everyone": (3, 4),
    "everywhere": (3, 4), "everybody": (4, 5), "evening": (2, 3),
    "different": (2, 3), "difference": (2, 3), "interesting": (3, 4),
    "interest": (2, 3), "favourite": (2, 3), "favorite": (2, 3),
    "several": (2, 3), "general": (2, 3), "generally": (3, 4),
    "memory": (2, 3), "history": (2, 3), "mystery": (2, 3),
    "victory": (2, 3), "natural": (2, 3), "naturally": (3, 4),
    "separate": (2, 3), "temperature": (3, 4), "comfortable": (3, 4),
    "vegetable": (3, 4), "miserable": (3, 4), "desperate": (2, 3),
    "opera": (2, 3), "average": (2, 3), "jewelry": (2, 3), "jewellery": (3, 4),
    "diamond": (2, 3), "violet": (2, 3), "actually": (3, 4), "usually": (3, 4),
    "basically": (3, 4), "finally": (2, 3), "really": (2, 3),
    "literally": (3, 4), "orange": (1, 2), "oranges": (2, 3),
    "fire": (1, 2), "fires": (1, 2), "hour": (1, 2), "hours": (1, 2),
    "our": (1, 2), "ours": (1, 2), "flour": (1, 2), "sour": (1, 2),
    "tire": (1, 2), "tired": (1, 2), "wire": (1, 2), "wires": (1, 2),
    "hire": (1, 2), "dire": (1, 2), "choir": (1, 2), "liar": (1, 2),
    "lyre": 1, "pyre": (1, 2), "desire": (2, 3), "entire": (2, 3),
    "empire": (2, 3), "inspire": (2, 3), "require": (2, 3), "admire": (2, 3),
    "retire": (2, 3), "expire": (2, 3), "umpire": (2, 3), "vampire": (2, 3),
    "flower": 2, "flowers": 2, "power": 2, "tower": 2, "shower": 2,
    "coward": 2, "toward": (1, 2), "towards": (1, 2),
    "real": (1, 2), "realise": (2, 3), "realize": (2, 3), "reality": (3, 4),
    "ideal": (2, 3), "royal": (1, 2), "loyal": (1, 2), "dial": (1, 2),
    "trial": (1, 2), "vial": (1, 2), "denial": (2, 3),
    "yeah": 1, "hmm": 1, "hm": 1, "shh": 1, "mm": 1,
}

EXCEPTIONS: Dict[str, Range] = {
    w: ((v, v) if isinstance(v, int) else (int(v[0]), int(v[1])))  # type: ignore[index]
    for w, v in _EXCEPTIONS_RAW.items()
}

# --------------------------------------------------------------------------- #
# Numbers
# --------------------------------------------------------------------------- #
_ONES = {0: 2, 1: 1, 2: 1, 3: 1, 4: 1, 5: 1, 6: 1, 7: 2, 8: 1, 9: 1}
_TEENS = {10: 1, 11: 3, 12: 1, 13: 2, 14: 2, 15: 2, 16: 2, 17: 3, 18: 2, 19: 2}
_TENS = {2: 2, 3: 2, 4: 2, 5: 2, 6: 2, 7: 3, 8: 2, 9: 2}


def _two_digit(n: int) -> int:
    if n < 10:
        return _ONES[n]
    if n < 20:
        return _TEENS[n]
    tens, ones = divmod(n, 10)
    return _TENS[tens] + (_ONES[ones] if ones else 0)


def _three_digit(n: int) -> int:
    h, rest = divmod(n, 100)
    out = (_ONES[h] + 2) if h else 0  # "hundred" = 2 syllables
    if rest:
        out += _two_digit(rest)
    return out


def number_syllables(text: str) -> Range:
    """Approximate spoken syllables of a numeral (``"14"`` -> ``(2, 2)``).

    Four-digit numbers give a range covering both readings
    (``2023`` -> "twenty twenty-three" = 5, "two thousand twenty-three" = 6).
    Anything longer is read digit by digit.
    """
    digits = re.sub(r"[^\d]", "", text)
    if not digits:
        return (1, 1)
    if len(digits) <= 2:
        n = _two_digit(int(digits))
        return (n, n)
    if len(digits) == 3:
        n = _three_digit(int(digits))
        return (n, n)
    if len(digits) == 4:
        value = int(digits)
        hi, lo = divmod(value, 100)
        year_style = _two_digit(hi) + (_two_digit(lo) if lo else 2)       # "nineteen ninety" / "nineteen hundred"
        th, rest = divmod(value, 1000)
        long_style = _ONES[th] + 2 + (_three_digit(rest) if rest else 0)  # "two thousand (and) five"
        if 1000 <= value < 2000:
            return (year_style, year_style)
        if 2000 <= value < 2010:
            return (long_style, long_style)
        return (min(year_style, long_style), max(year_style, long_style))
    n = sum(_ONES[int(d)] for d in digits)
    return (n, n)


# --------------------------------------------------------------------------- #
# Rule-based estimator
# --------------------------------------------------------------------------- #
_VOWELS = set("aeiou")


def _vowel_groups(word: str) -> int:
    """Count vowel groups; ``y`` is a consonant when it precedes a vowel."""
    count = 0
    prev = False
    n = len(word)
    for i, ch in enumerate(word):
        if ch in _VOWELS:
            is_v = True
        elif ch == "y":
            is_v = not (i + 1 < n and word[i + 1] in _VOWELS)
        else:
            is_v = False
        if is_v and not prev:
            count += 1
        prev = is_v
    return count


_SYLLABIC_LE_RE = re.compile(r"[^aeiouy](?:le|re)$")                 # ta-ble, a-cre
_SILENT_E_SUFFIX = re.compile(
    r"[^aeiouy]e(?:ly|less|ness|ful|ment|some|wise|wards?|ty"
    r"|thing|times?|body|land|side|place|works?|light|line|boat|style|keeper|maker|made|ship)$"
)                                                                    # lone-ly, some-thing, safe-ty
# Germanic compound formers whose final silent e survives inside a compound
# ("fore-see", "care-free", "house-work").  Only stems that do not double as
# Latin roots (no "gene-", "mode-", "mine-": ge-net-ic, mod-er-ate, min-er-al).
_COMPOUND_PREFIX = re.compile(
    r"^(?:fore|some|life|fire|home|care|state|space|time|wide|like|love|hope|safe|side"
    r"|whole|white|house|horse|stone|wine|bone|line|lake|race|note|game|name|shape|smoke"
    r"|type|base|case|date|gate|live|lone|make|mile|nose|page|pipe|rule|sale|tale|tide"
    r"|tone|tube|tune|vote|wake|wire|wise|wife|snake|grape|lime|nine|five)"
    r"(?=([^aeiouy][a-z]{2,})$)"
)
_INFLECTION_REMAINDER = re.compile(r"^[a-z]?(?:ed|ing|ings|er|ers|est|ly|ty|ry|ness|less|ful|ment|some|s|d)$")
_ED_ENDING = re.compile(r"[^aeioutd]ed$")                            # jumped (not wanted)
_LED_KEEP = re.compile(r"[^aeiouyl]led$")                            # set-tled (not called)
_ES_ENDING = re.compile(r"[^aeiouszxcg]es$")                         # takes (not boxes, places)
_ES_KEEP = re.compile(r"(?:ch|sh)es$|[^aeiouyl]les$")                # wishes, ta-bles

_ADD_RULES = (
    re.compile(r"(?<![ctsg])ia"),            # pi-a-no, di-a-ry     (not spe-cial, Rus-sia)
    re.compile(r"(?<![cgstxhnl])io"),        # ra-di-o, vi-o-lin    (not na-tion, mil-lion)
    re.compile(r"(?<![gp])eo"),              # vid-e-o, ne-on       (not pi-geon)
    re.compile(r"(?<![gq])ua"),              # ac-tu-al             (not lan-guage)
    re.compile(r"(?<![gq])ue(?=[lnt])"),     # flu-ent, du-et       (not guest, blue)
    re.compile(r"(?<![qg])ui(?=[dn]|ty|tion)"),  # flu-id, ru-in, gen-u-ine, tu-i-tion (not fruit, quit)
    re.compile(r"iu"),                       # me-di-um, ra-di-us
    re.compile(r"uou"),                      # con-tin-u-ous
    re.compile(r"eu(?=m)"),                  # mu-se-um
    re.compile(r"oi(?=c(?!e))"),             # he-ro-ic             (not voice)
    re.compile(r"ie(?=ty?$)"),               # so-ci-e-ty, Ju-li-et
    re.compile(r"[^aeiou]ie(?:r|st)$"),      # hap-pi-er, hap-pi-est (see _IER_EXCEPTIONS)
    re.compile(r"[^aeiouy]ying$"),           # fly-ing              (not play-ing)
    re.compile(r"(?:sm|thm)$"),              # pris-m, rhyth-m, tour-is-m
)
_SUB_RULES = (
    re.compile(r"viou?r$"),                  # be-hav-iour, sav-ior (undo the io rule)
    re.compile(r"liar$"),                    # fa-mil-iar           (undo the ia rule)
)
_IER_EXCEPTIONS = {
    "soldier", "glacier", "cashier", "premier", "frontier", "brigadier", "chandelier",
    "financier", "pier", "tier", "bier", "priest",
}


def _rule_count(word: str) -> int:
    w = word
    if not any(c in "aeiouy" for c in w):
        return 1
    count = _vowel_groups(w)

    # silent final e ("time", "whole") but not syllabic consonant+le/re ("table", "acre")
    if w.endswith("e") and not w.endswith("ee") and len(w) > 2 and w[-2] not in "aeiouy":
        if not _SYLLABIC_LE_RE.search(w):
            count -= 1
    suffix_hit = bool(_SILENT_E_SUFFIX.search(w))
    if suffix_hit:                            # lone-ly, hope-less, move-ment
        count -= 1
    else:                                     # fore-see, house-work, state-wide
        m = _COMPOUND_PREFIX.match(w)
        if m and not _INFLECTION_REMAINDER.match(m.group(1)):
            count -= 1
    if _ED_ENDING.search(w) and not _LED_KEEP.search(w):
        count -= 1
    if _ES_ENDING.search(w) and not _ES_KEEP.search(w):
        count -= 1
    for rx in _ADD_RULES:
        count += len(rx.findall(w))
    for rx in _SUB_RULES:
        count -= len(rx.findall(w))
    if w in _IER_EXCEPTIONS:
        count -= 1
    return max(1, count)


_CONTRACTIONS = ("'s", "s'", "'ll", "'ve", "'re", "'d", "'m")


@lru_cache(maxsize=None)
def count_word(word: str) -> Range:
    """Syllable range for a single word token (``(0, 0)`` for pure punctuation)."""
    w = word.lower().strip()
    w = w.replace("\u2019", "'").replace("\u2018", "'").replace("\u02bc", "'")
    w = w.strip("'\"“”‘’.,;:!?()[]{}<>«»—–-_*/\\|~`^#@&+=")
    if not w:
        return (0, 0)

    if any(ch.isdigit() for ch in w):
        if re.fullmatch(r"[\d,.']+", w):
            return number_syllables(w)
        digits = re.sub(r"[^\d]", "", w)               # "3rd", "1990s"
        letters = re.sub(r"[\d,.']", "", w)
        dl, dh = number_syllables(digits)
        if letters in ("st", "nd", "rd", "th", "s"):
            return (dl, dh)
        ll, lh = count_word(letters) if letters else (0, 0)
        return (dl + ll, dh + lh)

    if "-" in w:                                        # hyphenated compounds
        lo = hi = 0
        for part in w.split("-"):
            a, b = count_word(part)
            lo, hi = lo + a, hi + b
        return (max(lo, 1), max(hi, 1))

    if w in EXCEPTIONS:
        return EXCEPTIONS[w]

    base = w
    extra = 0
    if base.endswith("n't") and len(base) > 3:          # generic "-n't": one extra syllable
        base, extra = base[:-3], 1
    else:
        for suf in _CONTRACTIONS:
            if base.endswith(suf) and len(base) > len(suf) + 1:
                base = base[: -len(suf)]
                break
    base = base.replace("'", "")
    if not base:
        return (1, 1)
    if base in EXCEPTIONS:
        lo, hi = EXCEPTIONS[base]
        return (lo + extra, hi + extra)

    if _CMU and base in _CMU:
        counts = sorted({sum(1 for ph in pron if ph[-1].isdigit()) for pron in _CMU[base]})
        if counts and counts[0] > 0:
            return (counts[0] + extra, counts[-1] + extra)

    n = _rule_count(base) + extra
    return (n, n)


_TOKEN_RE = re.compile(r"[A-Za-z0-9\u00C0-\u024F'\u2019\u2018-]+")


def tokenize(line: str) -> List[str]:
    """Word tokens of a line (letters, digits, internal apostrophes/hyphens)."""
    toks = []
    cleaned = line.replace("\u2014", " ").replace("\u2013", " ")
    for m in _TOKEN_RE.finditer(cleaned):
        t = m.group(0).strip("'-\u2019\u2018")
        if t:
            toks.append(t)
    return toks


def count_line(line: str) -> Tuple[Range, List[Tuple[str, Range]]]:
    """Syllable range of a whole line plus the per-word breakdown."""
    words: List[Tuple[str, Range]] = []
    lo = hi = 0
    for tok in tokenize(line):
        r = count_word(tok)
        words.append((tok, r))
        lo += r[0]
        hi += r[1]
    return (lo, hi), words


def explain_line(line: str) -> str:
    """Human-readable breakdown, e.g. ``An(1) old(1) silent(2) pond(1) = 5``."""
    (lo, hi), words = count_line(line)
    parts = []
    for tok, (a, b) in words:
        parts.append(f"{tok}({a})" if a == b else f"{tok}({a}-{b})")
    total = str(lo) if lo == hi else f"{lo}-{hi}"
    return " ".join(parts) + f" = {total}"
