import unittest
from src.services.recognizer import recognize

class TestRecognizerSeparators(unittest.TestCase):
    def test_thousands_separator_comma(self):
        # "1,000 USD" -> 1000.0 USD
        res = recognize("1,000 USD")
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].amount, 1000.0)

    def test_thousands_separator_comma_large(self):
        # "10,000 USD" -> 10000.0 USD
        res = recognize("10,000 USD")
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].amount, 10000.0)

    def test_decimal_separator_comma(self):
        # "1,5 USD" -> 1.5 USD
        res = recognize("1,5 USD")
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].amount, 1.5)

    def test_decimal_separator_comma_two_digits(self):
        # "1,50 USD" -> 1.5 USD
        res = recognize("1,50 USD")
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].amount, 1.5)

    def test_decimal_separator_comma_many_digits(self):
        # "1,2345 USD" -> 1.2345 USD
        res = recognize("1,2345 USD")
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].amount, 1.2345)

    def test_ambiguous_thousands_like(self):
        # "1,234 USD" -> 1234.0 USD
        res = recognize("1,234 USD")
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].amount, 1234.0)

    def test_ambiguous_thousands_like_with_digits_before(self):
        # "10,500 USD" -> 10500.0 USD
        res = recognize("10,500 USD")
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].amount, 10500.0)

    def test_decimal_separator_dot(self):
        # "1.5 USD" -> 1.5 USD
        res = recognize("1.5 USD")
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].amount, 1.5)

    def test_decimal_separator_dot_thousands_like(self):
        # "1.234 USD" -> 1.234 USD
        res = recognize("1.234 USD")
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].amount, 1.234)

    def test_no_separator(self):
        # "1000 USD" -> 1000.0 USD
        res = recognize("1000 USD")
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].amount, 1000.0)

    def test_separator_logic_edge_case(self):
        # "0,123 USD"
        res = recognize("0,123 USD")
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].amount, 123.0)

    def test_mixed_separators_limitation(self):
        # "1,234.56 USD"
        # Due to regex limitations in CurrencyRecognizer, this matches "234.56"
        # and ignores "1,". This test confirms that my optimization doesn't crash
        # and maintains existing (albeit limited) behavior.
        res = recognize("1,234.56 USD")
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].amount, 234.56)

if __name__ == '__main__':
    unittest.main()
