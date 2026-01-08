
from src.services.recognizer import CurrencyRecognizer

class TestRecognizerOptimization:
    def test_normalize_amount_without_comma(self):
        # Should be fast path
        assert CurrencyRecognizer._normalize_amount("100") == 100.0
        assert CurrencyRecognizer._normalize_amount("100.5") == 100.5

    def test_normalize_amount_with_comma_thousands(self):
        # Should use regex
        assert CurrencyRecognizer._normalize_amount("1,000") == 1000.0
        assert CurrencyRecognizer._normalize_amount("10,000") == 10000.0

    def test_normalize_amount_with_comma_decimal(self):
        # Should use regex
        assert CurrencyRecognizer._normalize_amount("1,5") == 1.5
        assert CurrencyRecognizer._normalize_amount("0,5") == 0.5

    def test_complex_parsing_still_works(self):
        # Integration test ensures parsing still works correctly
        # Using valid currencies: USD, EUR, RUB (implied by context or code)
        results = CurrencyRecognizer.parse("100 usd and 1,000 eur and 1,5 rub")
        assert len(results) == 3
        # 100 usd
        assert results[0].amount == 100.0
        assert results[0].currency == "USD"
        # 1,000 eur -> 1000.0
        assert results[1].amount == 1000.0
        assert results[1].currency == "EUR"
        # 1,5 rub -> 1.5
        assert results[2].amount == 1.5
        assert results[2].currency == "RUB"
