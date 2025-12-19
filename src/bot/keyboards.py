from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Centralized flags/icons for currencies
CURRENCY_FLAGS = {
    "USD": "🇺🇸",
    "EUR": "🇪🇺",
    "RUB": "🇷🇺",
    "GBP": "🇬🇧",
    "CNY": "🇨🇳",
    "KZT": "🇰🇿",
    "BTC": "₿",
    "ETH": "Ξ",
    "TON": "💎",
    "USDT": "₮",
    "TRY": "🇹🇷",
}

def settings_keyboard(chat_id: int, current_currencies: list[str]) -> InlineKeyboardMarkup:
    # Supported currencies to toggle
    SUPPORTED_CURRENCIES = [
        "USD", "EUR", "RUB", "GBP", "CNY", "KZT",
        "BTC", "ETH", "TON", "USDT"
    ]

    builder = InlineKeyboardBuilder()

    for currency in SUPPORTED_CURRENCIES:
        is_active = currency in current_currencies
        flag = CURRENCY_FLAGS.get(currency, "💰")
        text = f"✅ {flag} {currency}" if is_active else f"❌ {flag} {currency}"
        callback_data = f"toggle_{currency}"

        builder.button(text=text, callback_data=callback_data)

    builder.adjust(2) # 2 columns

    builder.row(InlineKeyboardButton(text="Закрыть", callback_data="close_settings"))

    return builder.as_markup()
