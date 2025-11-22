import unittest
from src.services.recognizer import recognize, Price

class TestRecognizer(unittest.TestCase):
    def test_basic_usd(self):
        # "100 баксов" -> 100 USD
        res = recognize("100 баксов")
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].amount, 100.0)
        self.assertEqual(res[0].currency, "USD")

    def test_k_multiplier_eur(self):
        # "5k eur" -> 5000 EUR
        res = recognize("5k eur")
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].amount, 5000.0)
        self.assertEqual(res[0].currency, "EUR")

    def test_short_rub(self):
        # "цена 2000р" -> 2000 RUB
        res = recognize("цена 2000р")
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].amount, 2000.0)
        self.assertEqual(res[0].currency, "RUB")

    def test_slang_kosar(self):
        # "косарь" -> 1000 RUB
        res = recognize("косарь")
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].amount, 1000.0)
        self.assertEqual(res[0].currency, "RUB")

    def test_slang_with_multiplier_word(self):
        # "5 косарей" -> 5000 RUB
        res = recognize("5 косарей")
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].amount, 5000.0)
        self.assertEqual(res[0].currency, "RUB")

    def test_symbol_first(self):
        # "$100" -> 100 USD
        res = recognize("$100")
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].amount, 100.0)
        self.assertEqual(res[0].currency, "USD")

    def test_multiple(self):
        # "100 usd и 200 eur"
        res = recognize("100 usd и 200 eur")
        self.assertEqual(len(res), 2)
        # Order depends on regex finding order, usually left to right
        self.assertEqual(res[0].amount, 100.0)
        self.assertEqual(res[0].currency, "USD")
        self.assertEqual(res[1].amount, 200.0)
        self.assertEqual(res[1].currency, "EUR")

    def test_crypto_bitok(self):
        # "0.5 битка" -> 0.5 BTC
        res = recognize("0.5 битка")
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].amount, 0.5)
        self.assertEqual(res[0].currency, "BTC")

    def test_crypto_eth(self):
        # "10 эфира" -> 10 ETH
        res = recognize("10 эфира")
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].amount, 10.0)
        self.assertEqual(res[0].currency, "ETH")

if __name__ == '__main__':
    unittest.main()
