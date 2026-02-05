from typing import Sequence
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Centralized flags mapping for UI consistency
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
    "TRY": "🇹🇷",  # Included for completeness if added to supported list
}

def get_currency_label(currency: str) -> str:
    """Returns the currency code prefixed with its flag/icon."""
    flag = CURRENCY_FLAGS.get(currency, "💰")
    return f"{flag} {currency}"

def settings_keyboard(chat_id: int, current_currencies: Sequence[str]) -> InlineKeyboardMarkup:
    # Supported currencies to toggle
    SUPPORTED_CURRENCIES = list(CURRENCY_FLAGS.keys())

    builder = InlineKeyboardBuilder()

    for currency in SUPPORTED_CURRENCIES:
        is_active = currency in current_currencies
        # Get flag + code
        label = get_currency_label(currency)

        # Add checkmark/cross
        status_icon = "✅" if is_active else "❌"
        text = f"{status_icon} {label}"

        callback_data = f"toggle_{currency}"

        builder.button(text=text, callback_data=callback_data)

    builder.adjust(2) # 2 columns

    builder.row(InlineKeyboardButton(text="Закрыть", callback_data="close_settings"))

    return builder.as_markup()

def chart_quick_pick_keyboard() -> InlineKeyboardMarkup:
    """Returns a keyboard with popular currencies for quick chart selection."""
    # Popular currencies for quick access
    POPULAR = ["USD", "EUR", "CNY", "BTC", "ETH", "TON"]

    builder = InlineKeyboardBuilder()

    for currency in POPULAR:
        flag = CURRENCY_FLAGS.get(currency, "💰")
        text = f"{flag} {currency}"
        callback_data = f"chart_pick_{currency}"
        builder.button(text=text, callback_data=callback_data)

    builder.adjust(3) # 3 columns

    return builder.as_markup()
