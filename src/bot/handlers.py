from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandStart
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.recognizer import recognize
from src.services.rates import rates_service
from src.database.dal import get_chat_settings, toggle_currency
from src.bot.keyboards import settings_keyboard

main_router = Router()

# Helper for flags
CURRENCY_FLAGS = {
    "USD": "🇺🇸",
    "EUR": "🇪🇺",
    "RUB": "🇷🇺",
    "GBP": "🇬🇧",
    "CNY": "🇨🇳",
    "KZT": "🇰🇿",
}

def get_flag(currency: str) -> str:
    return CURRENCY_FLAGS.get(currency, "💰")

@main_router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "Привет! Я бот-конвертер валют.\n\n"
        "Просто напиши мне сумму и валюту (например, '100 usd', '5к евро', 'косарь'), "
        "и я переведу её.\n\n"
        "Настройки валют: /settings"
    )

@main_router.message(Command("settings"))
async def cmd_settings(message: Message, session: AsyncSession):
    settings = await get_chat_settings(session, message.chat.id)
    keyboard = settings_keyboard(message.chat.id, settings.target_currencies)
    await message.answer("Выберите валюты для конвертации:", reply_markup=keyboard)

@main_router.callback_query(F.data.startswith("toggle_"))
async def on_toggle_currency(callback: CallbackQuery, session: AsyncSession):
    currency = callback.data.split("_")[1]
    new_currencies = await toggle_currency(session, callback.message.chat.id, currency)

    keyboard = settings_keyboard(callback.message.chat.id, new_currencies)

    # Check if message text or markup is different to avoid API error if nothing changed?
    # Actually toggle always changes state.
    await callback.message.edit_reply_markup(reply_markup=keyboard)
    await callback.answer(f"{currency} переключен")

@main_router.callback_query(F.data == "close_settings")
async def on_close_settings(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer()

@main_router.message(F.text)
async def handle_text(message: Message, session: AsyncSession):
    prices = recognize(message.text)

    if not prices:
        return

    # Fetch settings
    settings = await get_chat_settings(session, message.chat.id)
    target_currencies = settings.target_currencies

    # If no target currencies selected, maybe warn or default?
    # Logic implies "convert ONLY to chosen". If none, maybe nothing happens or user sees nothing.
    # Let's assume user wants at least something. If list empty, maybe fallback or just show nothing.
    # The prompt says "convert only to chosen currencies".

    if not target_currencies:
         # Optional: await message.reply("Выберите валюты в /settings")
         return

    response_lines = []

    for price in prices:
        flag = get_flag(price.currency)

        line_parts = [f"{flag} {price.amount:g} {price.currency} ≈"]

        conversions = []
        for target_code in target_currencies:
            if target_code == price.currency:
                continue

            target_flag = get_flag(target_code)
            converted_amount = await rates_service.convert(price.amount, price.currency, target_code)

            formatted_amount = f"{converted_amount:.2f}".rstrip("0").rstrip(".")
            conversions.append(f"{target_flag} {formatted_amount} {target_code}")

        if conversions:
            line_parts.append(" | ".join(conversions))
            response_lines.append(" ".join(line_parts))

    if response_lines:
        await message.reply("\n".join(response_lines))
