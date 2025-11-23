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

    def test_no_false_positive_gb(self):
        # "16 ГБ" should NOT be recognized as currency
        res = recognize("16 ГБ")
        self.assertEqual(len(res), 0)

    def test_no_false_positive_bit(self):
        # "128 БИТ" should NOT be recognized as currency
        res = recognize("128 БИТ")
        self.assertEqual(len(res), 0)

    def test_no_false_positive_rtx(self):
        # "5060 RTX" should NOT be recognized as currency (GPU model)
        res = recognize("5060 RTX")
        self.assertEqual(len(res), 0)

    def test_no_false_positive_gpu(self):
        # "2280 GPU" should NOT be recognized as currency
        res = recognize("2280 GPU")
        self.assertEqual(len(res), 0)

    def test_no_false_positive_random_3letter(self):
        # Random 3-letter codes should NOT be recognized
        res = recognize("100 ABC")
        self.assertEqual(len(res), 0)
        
        res = recognize("200 XYZ")
        self.assertEqual(len(res), 0)

    def test_mixed_real_and_fake_currencies(self):
        # Real currency should be recognized, fake ones should not
        # "295 RUB и 5060 RTX"
        res = recognize("295 RUB и 5060 RTX")
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].amount, 295.0)
        self.assertEqual(res[0].currency, "RUB")

    def test_gpu_text_with_real_currency(self):
        # Text about GPU with real currency mixed in
        text = "обычный комплект на 32 ГБ догоняет в цене карточку RTX 5060"
        res = recognize(text)
        # Should find nothing as neither "ГБ" nor "RTX" are valid currencies
        self.assertEqual(len(res), 0)

if __name__ == '__main__':
    unittest.main()
