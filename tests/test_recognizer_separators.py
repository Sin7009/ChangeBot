import unittest
from src.services.recognizer import CurrencyRecognizer

class TestRecognizerSeparators(unittest.TestCase):
    def test_thousands_separator_comma(self):
        # 1,000 -> 1000.0
        self.assertEqual(CurrencyRecognizer._normalize_amount("1,000"), 1000.0)

    def test_decimal_separator_comma(self):
        # 1,5 -> 1.5
        self.assertEqual(CurrencyRecognizer._normalize_amount("1,5"), 1.5)

    def test_decimal_separator_comma_two_digits(self):
        # 1,50 -> 1.5
        self.assertEqual(CurrencyRecognizer._normalize_amount("1,50"), 1.5)

    def test_decimal_separator_comma_four_digits(self):
        # 1,2345 -> 1.2345
        self.assertEqual(CurrencyRecognizer._normalize_amount("1,2345"), 1.2345)

    def test_thousands_separator_with_decimals(self):
        # 1,000.00 -> 1000.0
        # This checks robustness of logic even if regex usually prevents double separators
        self.assertEqual(CurrencyRecognizer._normalize_amount("1,000.00"), 1000.0)

    def test_thousands_separator_large(self):
        # 100,000 -> 100000.0
        # Note: input string to _normalize_amount usually has only one comma due to regex capture,
        # but the logic should hold for "digits,3digits".
        self.assertEqual(CurrencyRecognizer._normalize_amount("100,000"), 100000.0)

    def test_decimal_point(self):
        # 1.000 -> 1.0
        self.assertEqual(CurrencyRecognizer._normalize_amount("1.000"), 1.0)

    def test_no_separator(self):
        # 1000 -> 1000.0
        self.assertEqual(CurrencyRecognizer._normalize_amount("1000"), 1000.0)

if __name__ == '__main__':
    unittest.main()
