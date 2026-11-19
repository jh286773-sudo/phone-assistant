import unittest
from core.translation import is_persian, translate

class TranslationTests(unittest.TestCase):
    def test_persian_detection(self):
        self.assertTrue(is_persian("سلام"))
        self.assertFalse(is_persian("hello"))

    def test_empty_input_rejected_before_network(self):
        with self.assertRaises(ValueError):
            translate("", "en")

    def test_bad_language_rejected_before_network(self):
        with self.assertRaises(ValueError):
            translate("hello", "english")
