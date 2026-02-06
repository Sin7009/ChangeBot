from src.bot.keyboards import chart_quick_pick_keyboard, CURRENCY_FLAGS

def test_chart_quick_pick_keyboard():
    markup = chart_quick_pick_keyboard()
    assert markup.inline_keyboard is not None

    # We expect 6 buttons: USD, EUR, CNY, BTC, ETH, TON
    # Distributed in 2 rows of 3

    all_buttons = [btn for row in markup.inline_keyboard for btn in row]
    assert len(all_buttons) == 6

    currencies = ["USD", "EUR", "CNY", "BTC", "ETH", "TON"]
    for btn, curr in zip(all_buttons, currencies):
        expected_text = f"{CURRENCY_FLAGS[curr]} {curr}".strip()
        assert btn.text == expected_text
        assert btn.callback_data == f"chart_pick_{curr}"
