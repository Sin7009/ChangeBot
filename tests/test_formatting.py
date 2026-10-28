import pytest

from src.bot.formatting import format_amount


@pytest.mark.parametrize("amount, expected", [
    (9000.0, "9000"),
    (2.85, "2.85"),
    (11167.6447, "11167.64"),
    # Regression: large amounts were shown as "3.5e+08"
    (350_000_000.0, "350000000"),
    (0.5, "0.5"),
    (0.0124, "0.0124"),
    # Regression: 228 RUB in BTC was shown as "0"
    (0.00002832, "0.0000283"),
    (0.001, "0.001"),
    (0.0, "0"),
])
def test_format_amount(amount, expected):
    assert format_amount(amount) == expected
