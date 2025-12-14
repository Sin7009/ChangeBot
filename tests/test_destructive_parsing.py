import pytest
from src.services.recognizer import CurrencyRecognizer

@pytest.mark.xfail(reason="Bug: _normalize_amount blindly replaces commas with dots, interpreting 1,000 as 1.0")
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
