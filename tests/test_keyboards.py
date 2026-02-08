from src.bot.keyboards import chart_quick_pick_keyboard, settings_keyboard

def test_chart_quick_pick_keyboard():
    markup = chart_quick_pick_keyboard()
    assert markup.inline_keyboard

    # Flatten buttons
    buttons = [btn for row in markup.inline_keyboard for btn in row]

    # Check for major currencies
    # We expect flags too, but checking code is safer
    assert any("USD" in btn.text and "chart_pick_USD" == btn.callback_data for btn in buttons)
    assert any("EUR" in btn.text and "chart_pick_EUR" == btn.callback_data for btn in buttons)
    assert any("BTC" in btn.text and "chart_pick_BTC" == btn.callback_data for btn in buttons)

    # Check total count (should be at least 3)
    assert len(buttons) >= 3

def test_settings_keyboard():
    active = ("USD", "RUB")
    markup = settings_keyboard(123, active)

    buttons = [btn for row in markup.inline_keyboard for btn in row]

    # Check toggle logic
    usd_btn = next(btn for btn in buttons if btn.callback_data == "toggle_USD")
    assert "✅" in usd_btn.text

    # EUR is not in active list, so should have X
    # Note: depends on if EUR is in SUPPORTED_CURRENCIES in keyboards.py
    # Assuming EUR is supported (it is in CURRENCY_FLAGS)
    eur_btn = next(btn for btn in buttons if btn.callback_data == "toggle_EUR")
    assert "❌" in eur_btn.text
