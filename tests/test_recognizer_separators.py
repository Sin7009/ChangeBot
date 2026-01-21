
from src.services.recognizer import recognize, CurrencyRecognizer

def test_thousands_separator_comma():
    # "1,000 USD" -> 1000 USD
    res = recognize("1,000 USD")
    assert len(res) == 1
    assert res[0].amount == 1000.0
    assert res[0].currency == "USD"

def test_decimal_separator_comma():
    # "1,5 USD" -> 1.5 USD
    res = recognize("1,5 USD")
    assert len(res) == 1
    assert res[0].amount == 1.5
    assert res[0].currency == "USD"

def test_decimal_separator_dot():
    # "1.5 USD" -> 1.5 USD
    res = recognize("1.5 USD")
    assert len(res) == 1
    assert res[0].amount == 1.5
    assert res[0].currency == "USD"

def test_thousands_separator_comma_euro():
    # "1,234 EUR" -> 1234 EUR
    res = recognize("1,234 EUR")
    assert len(res) == 1
    assert res[0].amount == 1234.0
    assert res[0].currency == "EUR"

def test_large_number_comma():
    # "10,000 USD" -> 10000 USD
    res = recognize("10,000 USD")
    assert len(res) == 1
    assert res[0].amount == 10000.0

def test_ambiguous_thousands_like_decimal():
    # "1,23 USD" -> 1.23 USD (not thousands because only 2 digits)
    res = recognize("1,23 USD")
    assert len(res) == 1
    assert res[0].amount == 1.23

def test_ambiguous_thousands_like_decimal_4digits():
    # "1,2345 USD" -> 1.2345 USD (not thousands because 4 digits)
    res = recognize("1,2345 USD")
    assert len(res) == 1
    assert res[0].amount == 1.2345

def test_internal_normalize_robustness():
    # Test cases that verify robustness of _normalize_amount even for inputs
    # that might strictly be filtered by current regex (regression testing)
    assert CurrencyRecognizer._normalize_amount("1,000.00") == 1000.0
    assert CurrencyRecognizer._normalize_amount("1,234.56") == 1234.56
    assert CurrencyRecognizer._normalize_amount("1,000") == 1000.0
    assert CurrencyRecognizer._normalize_amount("1,5") == 1.5
