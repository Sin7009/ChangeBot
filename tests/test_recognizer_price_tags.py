from src.services.recognizer import recognize


def _parsed(text):
    return [(p.amount, p.currency) for p in recognize(text, strict_mode=True)]


def test_old_and_new_price_stacked_before_currencies():
    # Regression: OCR of a price tag "500⁰⁰ руб. → 299⁹⁵ руб." gave only 500 RUB
    text = (
        "Великобритания\nНазвание Вашего\nПродукта\nОписание Вашего продукта\n"
        "299\n95\n500\npy6.\npy6.\n1234567890\nЦена за 1 шт."
    )
    assert _parsed(text) == [(299.95, "RUB"), (500.0, "RUB")]


def test_stacked_prices_with_kopecks_for_both():
    assert _parsed("500\n00\n299\n95\nруб.\nруб.") == [(500.0, "RUB"), (299.95, "RUB")]


def test_barcode_is_not_a_price():
    assert _parsed("1234567890\n299\n95\nруб.") == [(299.95, "RUB")]


def test_lone_short_number_is_not_a_price():
    assert _parsed("12\nруб.") == []
