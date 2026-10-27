import pytest

from src.services.recognizer import recognize


def _parsed(text, strict_mode=False):
    return [(p.amount, p.currency) for p in recognize(text, strict_mode=strict_mode)]


@pytest.mark.parametrize("text, expected", [
    # Regression: "$2,5-3 млн" was parsed as 2.5 USD
    ('стоимость одного "Искандера" - $2,5-3 млн - результат 1 отверстие',
     [(2_500_000, "USD"), (3_000_000, "USD")]),
    ("$2,5 - $3 млн", [(2_500_000, "USD"), (3_000_000, "USD")]),
    ("$5–7k", [(5_000, "USD"), (7_000, "USD")]),
    ("$100-200", [(100, "USD"), (200, "USD")]),
    ("2,5-3 млн долларов", [(2_500_000, "USD"), (3_000_000, "USD")]),
    ("от 2 до 3 млн рублей", [(2_000_000, "RUB"), (3_000_000, "RUB")]),
    # Regression: the price tag preprocessing read this as 10.15 RUB
    ("10-15 тыс руб", [(10_000, "RUB"), (15_000, "RUB")]),
])
def test_range_shares_multiplier_and_currency(text, expected):
    assert _parsed(text) == expected


def test_prefix_range_in_strict_mode():
    assert _parsed("$2,5-3 млн", strict_mode=True) == [(2_500_000, "USD"), (3_000_000, "USD")]


def test_descending_range_does_not_share_multiplier():
    # "с 900 до 1,2 млрд" is growth, not a range of 900 млрд to 1.2 млрд
    assert _parsed("с 900 до 1,2 млрд рублей") == [(1_200_000_000, "RUB")]


def test_explicit_multipliers_are_kept():
    assert _parsed("выросли с €350 млн до €2 млрд") == [(350_000_000, "EUR"), (2_000_000_000, "EUR")]


def test_price_tag_is_not_a_range():
    # Without a multiplier "250-99 руб" is a price tag, not two prices
    assert len(_parsed("price 250-99 руб")) == 1


@pytest.mark.parametrize("text, expected", [
    ("15 тыс руб", [(15_000, "RUB")]),
    ("900 тыс. руб.", [(900_000, "RUB")]),
    ("$5 тыс", [(5_000, "USD")]),
    ("2 млн. рублей", [(2_000_000, "RUB")]),
    ("10-15 тыс. руб.", [(10_000, "RUB"), (15_000, "RUB")]),
])
def test_abbreviated_multipliers(text, expected):
    assert _parsed(text) == expected
