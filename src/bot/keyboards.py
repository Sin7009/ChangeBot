from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def settings_keyboard(chat_id: int, current_currencies: list[str]) -> InlineKeyboardMarkup:
    # Supported currencies to toggle
    # We can expand this list later.
    SUPPORTED_CURRENCIES = [
        "USD", "EUR", "RUB", "GBP", "CNY", "KZT",
        "BTC", "ETH", "TON", "USDT"
    ]

    builder = InlineKeyboardBuilder()

    for currency in SUPPORTED_CURRENCIES:
        is_active = currency in current_currencies
        text = f"✅ {currency}" if is_active else f"❌ {currency}"
        callback_data = f"toggle_{currency}"

        builder.button(text=text, callback_data=callback_data)

    builder.adjust(2)  # 2 columns

    builder.row(InlineKeyboardButton(text="Закрыть", callback_data="close_settings"))

    return builder.as_markup()
