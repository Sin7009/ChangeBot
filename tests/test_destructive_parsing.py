import pytest
from src.services.recognizer import CurrencyRecognizer

def test_comma_separated_thousands_handling():
    """
    Test that '1,000 USD' is interpreted as 1000.0 (thousands separator),
    not 1.0 (decimal separator).

    This targets the naive string replacement in _normalize_amount
    which blindly replaces commas with dots.
    """
    text = "Price is 1,000 USD"
    results = CurrencyRecognizer.parse(text)

    # We expect at least one result
    assert len(results) > 0, "Should recognize currency"

    # We expect the amount to be 1000.0
    # Current logic likely returns 1.0 because '1,000' -> '1.000' -> 1.0
    price = results[0]
    assert price.amount == 1000.0, f"Expected 1000.0 for '1,000', got {price.amount}"

def test_comma_as_decimal_separator():
    """
    Test that '1,5 USD' is interpreted as 1.5 (European decimal notation)
    """
    text = "Price is 1,5 USD"
    results = CurrencyRecognizer.parse(text)
    
    assert len(results) > 0, "Should recognize currency"
    assert results[0].amount == 1.5, f"Expected 1.5 for '1,5', got {results[0].amount}"

def test_large_comma_separated_amount():
    """
    Test larger amounts with comma thousands separator like '10,000 EUR'
    """
    text = "Total: 10,000 EUR"
    results = CurrencyRecognizer.parse(text)
    
    assert len(results) > 0, "Should recognize currency"
    assert results[0].amount == 10000.0, f"Expected 10000.0, got {results[0].amount}"
