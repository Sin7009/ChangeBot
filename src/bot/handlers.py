from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart

from src.services.recognizer import recognize
from src.services.rates import rates_service

main_router = Router()

@main_router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "Привет! Я бот-конвертер валют.\n\n"
        "Просто напиши мне сумму и валюту (например, '100 usd', '5к евро', 'косарь'), "
        "и я переведу её в рубли, доллары и евро."
    )

@main_router.message(F.text)
async def handle_text(message: Message):
    prices = recognize(message.text)

    if not prices:
        return

    response_lines = []

    # Target currencies to display
    targets = [("RUB", "🇷🇺"), ("USD", "🇺🇸"), ("EUR", "🇪🇺")]

    for price in prices:
        # Avoid converting to the same currency if it looks redundant,
        # but the request says "convert each amount to RUB, USD and EUR".
        # Example format: 🇺🇸 100 USD ≈ 🇷🇺 9800 RUB | 🇪🇺 92 EUR

        flag = ""
        if price.currency == "USD": flag = "🇺🇸"
        elif price.currency == "EUR": flag = "🇪🇺"
        elif price.currency == "RUB": flag = "🇷🇺"
        elif price.currency == "GBP": flag = "🇬🇧"
        else: flag = "💰" # Generic

        line_parts = [f"{flag} {price.amount:g} {price.currency} ≈"]

        conversions = []
        for target_code, target_flag in targets:
            # Skip if target is the source?
            # The example "🇺🇸 100 USD ≈ 🇷🇺 9800 RUB | 🇪🇺 92 EUR" implies showing targets that are NOT the source.
            if target_code == price.currency:
                continue

            converted_amount = await rates_service.convert(price.amount, price.currency, target_code)

            # Format: no decimals if huge, 2 decimals if small? ":g" handles some, but typically currency is .2f
            # "9800 RUB" in example suggests int if whole.
            # Let's use flexible formatting.

            formatted_amount = f"{converted_amount:.2f}".rstrip("0").rstrip(".")
            conversions.append(f"{target_flag} {formatted_amount} {target_code}")

        if conversions:
            line_parts.append(" | ".join(conversions))
            response_lines.append(" ".join(line_parts))

    if response_lines:
        await message.reply("\n".join(response_lines))
