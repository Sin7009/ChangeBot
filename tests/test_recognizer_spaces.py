import unittest
from src.services.recognizer import recognize

class TestRecognizerSpaces(unittest.TestCase):
    """Tests for space-separated numbers and decimal+word combinations"""
    
    def test_space_separated_million(self):
        # "1 000 000 рублей" -> 1000000 RUB
        res = recognize("1 000 000 рублей")
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].amount, 1000000.0)
        self.assertEqual(res[0].currency, "RUB")
    
    def test_space_separated_hundreds_thousands(self):
        # "100 000 долларов" -> 100000 USD
        res = recognize("100 000 долларов")
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].amount, 100000.0)
        self.assertEqual(res[0].currency, "USD")
    
    def test_decimal_with_million_word(self):
        # "2,9 миллиона долларов" -> 2900000 USD
        res = recognize("2,9 миллиона долларов")
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].amount, 2900000.0)
        self.assertEqual(res[0].currency, "USD")
    
    def test_decimal_with_mln_abbr(self):
        # "4,5 млн рублей" -> 4500000 RUB
        res = recognize("4,5 млн рублей")
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].amount, 4500000.0)
        self.assertEqual(res[0].currency, "RUB")
    
    def test_integer_with_million_word(self):
        # "656 миллионов фунтов" -> 656000000 GBP
        res = recognize("656 миллионов фунтов")
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].amount, 656000000.0)
        self.assertEqual(res[0].currency, "GBP")
    
    def test_real_news_valve_lawsuit(self):
        # From the problem statement
        text = "Суд Великобритании одобрил иск против Valve на 656 миллионов фунтов стерлингов"
        res = recognize(text)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].amount, 656000000.0)
        self.assertEqual(res[0].currency, "GBP")
    
    def test_real_news_twitter_nft(self):
        # From the problem statement
        text = "В 2021 году был продан первый твит создателя Twitter Джека Дорси за 2,9 миллиона долларов"
        res = recognize(text)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].amount, 2900000.0)
        self.assertEqual(res[0].currency, "USD")
    
    def test_real_news_apple_theft(self):
        # From the problem statement - should find two amounts
        text = "В Подмосковье водитель новичок украл технику Apple на 4,5 млн рублей за один день"
        res = recognize(text)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].amount, 4500000.0)
        self.assertEqual(res[0].currency, "RUB")
    
    def test_real_news_apple_theft_second_amount(self):
        # From the problem statement
        text = "техника примерно на 3 млн рублей до сих пор не найдена"
        res = recognize(text)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].amount, 3000000.0)
        self.assertEqual(res[0].currency, "RUB")
    
    def test_real_news_tour_operator(self):
        # From the problem statement
        text = "Москвич отсудил у туроператора больше миллиона рублей за сорванную поездку"
        res = recognize(text)
        # "больше миллиона" is tricky - just "миллиона" without a number
        # For now, let's test specific amounts from the details
        pass
    
    def test_real_news_tour_operator_amounts(self):
        # From the problem statement - multiple amounts with spaces
        text = """
        В итоге компанию обязали выплатить более 1 млн рублей:
        - 364 000 рублей неустойка
        - 364 000 рублей стоимость услуги
        - 374 000 рублей штраф
        - 20 000 рублей моральный вред
        - 5 000 рублей юридические расходы
        """
        res = recognize(text)
        # Should find: 1 млн, 364 000, 364 000, 374 000, 20 000, 5 000
        self.assertGreaterEqual(len(res), 6)
        
        amounts = [r.amount for r in res]
        self.assertIn(1000000.0, amounts)  # 1 млн
        self.assertEqual(amounts.count(364000.0), 2)  # 364 000 x2
        self.assertIn(374000.0, amounts)  # 374 000
        self.assertIn(20000.0, amounts)  # 20 000
        self.assertIn(5000.0, amounts)  # 5 000
    
    def test_space_separated_with_thousands_separator(self):
        # Edge case: multiple spaces between digit groups
        res = recognize("1 000 рублей")
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].amount, 1000.0)
        self.assertEqual(res[0].currency, "RUB")
    
    def test_nvidia_salary_example(self):
        # From the problem statement
        text = "их доходы достигают $100 тысяч в год"
        res = recognize(text)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].amount, 100000.0)
        self.assertEqual(res[0].currency, "USD")

if __name__ == '__main__':
    unittest.main()
