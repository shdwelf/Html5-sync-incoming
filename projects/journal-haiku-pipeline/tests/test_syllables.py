import unittest

import journal_pipeline.syllables as S


class RuleEngineTests(unittest.TestCase):
    """Exercise the rule-based tier directly (CMU may or may not be installed)."""

    def setUp(self):
        self._cmu = S._CMU
        S._CMU = {}
        S.count_word.cache_clear()

    def tearDown(self):
        S._CMU = self._cmu
        S.count_word.cache_clear()

    def check(self, table):
        misses = []
        for word, expected in table.items():
            exp = (expected, expected) if isinstance(expected, int) else expected
            got = S.count_word(word)
            if got != exp:
                misses.append((word, got, exp))
        self.assertEqual(misses, [])

    def test_basic_vowel_groups_and_silent_e(self):
        self.check({"an": 1, "old": 1, "silent": 2, "pond": 1, "time": 1, "whole": 1, "table": 2,
                    "little": 2, "acre": 2, "care": 1, "eve": 1, "ago": 2, "any": 2, "the": 1})

    def test_ed_and_es_endings(self):
        self.check({"jumped": 1, "walked": 1, "wanted": 2, "needed": 2, "played": 1, "carried": 2,
                    "settled": 2, "called": 1, "makes": 1, "boxes": 2, "wishes": 2, "places": 2,
                    "tables": 2, "smiles": 1, "candles": 2, "waves": 1, "goes": 1, "clothes": 1})

    def test_suffixes_and_compounds(self):
        self.check({"lonely": 2, "hopeless": 2, "careful": 2, "movement": 2, "completely": 3,
                    "something": 2, "sometimes": 2, "lifetime": 2, "somebody": 3, "safety": 2,
                    "foresee": 2, "carefree": 2, "statewide": 2, "housework": 2, "somewhere": 2,
                    "widened": 2, "widening": 3, "hopefully": 3, "forever": 3, "forest": 2, "nineteen": 2})

    def test_vowel_splits(self):
        self.check({"piano": 3, "giant": 2, "special": 2, "radio": 3, "nation": 2, "million": 2,
                    "video": 3, "pigeon": 2, "actual": 3, "language": 2, "fuel": 2, "guest": 1,
                    "blue": 1, "fluid": 2, "fruit": 1, "quiet": 2, "medium": 3, "museum": 3,
                    "continuous": 4, "heroic": 3, "voice": 1, "society": 4, "happier": 3, "priest": 1,
                    "flying": 2, "playing": 2, "prism": 2, "rhythm": 2, "behaviour": 3})

    def test_exceptions_and_ambiguous(self):
        self.check({"poem": 2, "idea": 3, "ocean": 2, "science": 2, "people": 2, "eyes": 1,
                    "fire": (1, 2), "every": (2, 3), "evening": (2, 3), "hour": (1, 2),
                    "didn't": 2, "don't": 1, "father's": 2, "I'm": 1, "we're": 1})

    def test_numbers(self):
        self.assertEqual(S.number_syllables("14"), (2, 2))
        self.assertEqual(S.number_syllables("7"), (2, 2))
        self.assertEqual(S.number_syllables("1999"), (5, 5))
        self.assertEqual(S.number_syllables("2005"), (4, 4))
        self.assertEqual(S.number_syllables("2023"), (5, 6))
        self.assertEqual(S.count_word("3rd"), (1, 1))
        self.assertEqual(S.count_word("1990s"), (4, 4))
        self.assertEqual(S.count_word("twenty-three"), (3, 3))

    def test_punctuation_only_token_counts_zero(self):
        self.assertEqual(S.count_word("—"), (0, 0))
        self.assertEqual(S.count_word("..."), (0, 0))


class LineTests(unittest.TestCase):
    def test_count_line_and_explain(self):
        (lo, hi), words = S.count_line("An old silent pond")
        self.assertEqual((lo, hi), (5, 5))
        self.assertEqual([w for w, _ in words], ["An", "old", "silent", "pond"])
        self.assertEqual(S.explain_line("An old silent pond"), "An(1) old(1) silent(2) pond(1) = 5")

    def test_tokenize_handles_dashes_and_curly_quotes(self):
        self.assertEqual(S.tokenize("frost—late spring; ‘kettle’"), ["frost", "late", "spring", "kettle"])

    def test_classic_haiku(self):
        for line, target in (("An old silent pond", 5), ("A frog jumps into the pond", 7),
                             ("Splash! Silence again.", 5)):
            (lo, hi), _ = S.count_line(line)
            self.assertTrue(lo <= target <= hi, (line, lo, hi))


if __name__ == "__main__":
    unittest.main()
