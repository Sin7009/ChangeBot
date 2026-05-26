from src.services.recognizer import recognize


def test_recognize_prevents_long_strings():
    """Test that recognize handles extremely long input gracefully"""
    # Create a very long string
    long_text = "test " * 10000 + "100 USD"
    
    # Should still work but not crash
    results = recognize(long_text)
    assert len(results) >= 1
    assert results[0].currency == "USD"
    assert results[0].amount == 100.0


def test_recognize_with_special_characters():
    """Test that recognize handles special characters without crashing"""
    text = "Price: $100 <script>alert('xss')</script>"
    results = recognize(text)
    
    assert len(results) >= 1
    assert results[0].currency == "USD"
    assert results[0].amount == 100.0


def test_recognize_empty_string():
    """Test that recognize handles empty string"""
    results = recognize("")
    assert len(results) == 0


def test_recognize_only_whitespace():
    """Test that recognize handles only whitespace"""
    results = recognize("   \n\t   ")
    assert len(results) == 0


def test_recognize_very_large_number():
    """Test recognition of very large amounts"""
    text = "999999999999 USD"
    results = recognize(text)
    
    assert len(results) == 1
    assert results[0].amount == 999999999999.0
    assert results[0].currency == "USD"


def test_recognize_very_small_decimal():
    """Test recognition of very small decimal amounts"""
    text = "0.00001 BTC"
    results = recognize(text)
    
    assert len(results) == 1
    assert abs(results[0].amount - 0.00001) < 0.000001
    assert results[0].currency == "BTC"


def test_strict_mode_rejects_text_currencies():
    """Test that strict mode only accepts symbols"""
    text = "100 USD"
    
    # Normal mode should find it
    results = recognize(text, strict_mode=False)
    assert len(results) == 1
    
    # Strict mode should reject it (no symbol)
    results_strict = recognize(text, strict_mode=True)
    assert len(results_strict) == 0


def test_strict_mode_accepts_symbols():
    """Test that strict mode accepts currency symbols"""
    text = "$100"
    
    results = recognize(text, strict_mode=True)
    assert len(results) == 1
    assert results[0].amount == 100.0
    assert results[0].currency == "USD"


def test_multiple_currencies_in_sentence():
    """Test extracting multiple currencies from complex sentence"""
    text = "I spent $50 USD on lunch and 30€ on coffee, plus 1000₽ for transport"
    results = recognize(text)
    
    # Should find at least 3 currency amounts
    assert len(results) >= 3
    
    # Check we found USD, EUR, RUB
    currencies_found = {r.currency for r in results}
    assert "USD" in currencies_found
    assert "EUR" in currencies_found
    assert "RUB" in currencies_found

def test_overlapping_false_positive():
    """
    Test that '100 rub 200' is parsed as ONLY '100 rub' and not '100 rub' AND '200 rub'.
    This was a false positive where the second number was matched by a pattern looking for currency-first,
    using the SAME currency token that had already been consumed by the first match.
    """
    # "100 rub 200" -> 100 RUB. "200" should be ignored as it has no currency.
    res = recognize("100 rub 200")
    assert len(res) == 1
    assert res[0].amount == 100.0
    assert res[0].currency == "RUB"


def test_overlapping_valid_sequence():
    """
    Test that '100 rub 200 usd' is parsed correctly as two prices.
    """
    res = recognize("100 rub 200 usd")
    assert len(res) == 2
    assert res[0].amount == 100.0
    assert res[0].currency == "RUB"
    assert res[1].amount == 200.0
    assert res[1].currency == "USD"


def test_reverse_order_sequence():
    """
    Test that 'rub 100 usd 200' is parsed correctly.
    """
    res = recognize("rub 100 usd 200")
    assert len(res) == 2
    # rub 100 -> 100 RUB
    # usd 200 -> 200 USD
    assert res[0].amount == 100.0
    assert res[0].currency == "RUB"
    assert res[1].amount == 200.0
    assert res[1].currency == "USD"


def test_transfer_question_infers_rub_amount_from_context():
    """If user asks transfer-to-dollar question without source currency, infer RUB source."""
    text = "если я переведу 25000 на свою карту в Армении (она в баксах) сколько я получу денег?"
    res = recognize(text)

    assert len(res) == 1
    assert res[0].amount == 25000.0
    assert res[0].currency == "RUB"


def test_transfer_question_without_target_currency_hint_not_inferred():
    """Do not infer bare numbers for transfer questions without explicit target-currency hint."""
    text = "если я переведу 25000 на свою карту, сколько я получу денег?"
    res = recognize(text)

    assert len(res) == 0


def test_does_not_parse_count_phrase_as_rubles():
    """Do not parse phrases like '2 раза' as '2 RUB'."""
    text = "Если что, они его 2 раза на РЕН-ТВ приглашали"
    res = recognize(text)

    assert len(res) == 0


def test_does_not_parse_symbol_when_stuck_to_word_tail():
    """Do not parse malformed token like '100$abc' as currency."""
    text = "Тестовый хвост 100$abc"
    res = recognize(text)

    assert len(res) == 0


def test_does_not_parse_symbol_when_stuck_to_word_head():
    """Do not parse malformed token like 'abc$100' as currency."""
    text = "Префикс abc$100 для проверки"
    res = recognize(text)

    assert len(res) == 0


def test_does_not_parse_weight_ton_as_ton_crypto():
    """Do not parse physical weight 'тон' as TON cryptocurrency."""
    text = "Купили 2 тон цемента"
    res = recognize(text)

    assert len(res) == 0


def test_transfer_inference_requires_finance_context_words():
    """Do not infer RUB for generic 'переведу ... в баксах' text outside money-transfer context."""
    text = "переведу 25000 комментариев в баксах в таблице"
    res = recognize(text)

    assert len(res) == 0
