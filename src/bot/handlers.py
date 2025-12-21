import asyncio
import io
import logging
from typing import List, Optional

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.filters import Command, CommandStart, CommandObject
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.recognizer import recognize, Price
from src.services.rates import rates_service
from src.services.charts import generate_chart
from src.services.ocr import image_to_text
from src.database.dal import get_chat_settings, toggle_currency
from src.bot.keyboards import settings_keyboard, CURRENCY_FLAGS

logger = logging.getLogger(__name__)

main_router = Router()

def get_flag(currency: str) -> str:
    return CURRENCY_FLAGS.get(currency, "💰")

async def convert_prices(prices: List[Price], session: AsyncSession, chat_id: int) -> Optional[str]:
    """
    Converts a list of recognized prices to the target currencies defined in chat settings.
    Returns a formatted string with the conversions, or None if no targets are set.
    """
    # Fetch settings
    settings = await get_chat_settings(session, chat_id)
    target_currencies = settings.target_currencies

    if not target_currencies:
         return None

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

    return "\n".join(response_lines) if response_lines else None

@main_router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "👋 <b>Привет! Я бот-конвертер валют.</b>\n\n"
        "Просто напиши мне сумму и валюту, и я переведу её.\n\n"
        "<b>Примеры:</b>\n"
        "• <code>100 usd</code>\n"
        "• <code>5к евро</code>\n"
        "• <code>косарь</code>\n\n"
        "⚙️ Настройки: /settings\n"
        "📈 Графики: /chart USD",
        parse_mode="HTML"
    )

@main_router.message(Command("settings"))
async def cmd_settings(message: Message, session: AsyncSession):
    settings = await get_chat_settings(session, message.chat.id)
    keyboard = settings_keyboard(message.chat.id, settings.target_currencies)
    await message.answer("Выберите валюты для конвертации:", reply_markup=keyboard)

@main_router.message(Command("chart"))
async def cmd_chart(message: Message, command: CommandObject):
    """
    Handler for /chart <currency>
    e.g. /chart USD -> chart for USD/RUB
    """
    args = command.args
    if not args:
        await message.answer("Использование: /chart <код_валюты> (например, USD)")
        return

    # Input validation: only allow alphanumeric characters to prevent injection
    currency_raw = args.strip()
    if not currency_raw.isalnum() or len(currency_raw) > 10:
        await message.answer("⚠️ Неверный формат валюты. Используйте код валюты (например, USD, EUR)")
        return
    
    currency = currency_raw.upper()

    # Map common currencies to Yahoo Finance symbols relative to RUB
    # We default to showing X/RUB pairs.
    # Note: Yahoo Finance symbols for currencies are usually "CUR1CUR2=X"
    # e.g. "RUB=X" is actually USD/RUB rate (inverse logic sometimes).
    # "EURRUB=X" is EUR/RUB.
    # "CNYRUB=X" might be available.

    # Let's handle common ones.
    pair_map = {
        "USD": "RUB=X", # This is standard USD/RUB in Yahoo
        "EUR": "EURRUB=X",
        "CNY": "CNYRUB=X",
        "GBP": "GBPRUB=X",
        "KZT": "KZTRUB=X",
        "TRY": "TRYRUB=X",
    }

    # If user asks for RUB, maybe they want RUB/USD?
    if currency == "RUB":
         await message.answer("График рубля к рублю? Это всегда 1. :)")
         return

    ticker = pair_map.get(currency)

    if not ticker:
        # Try generic construction if not in map?
        # e.g. "USDRUB=X"
        ticker = f"{currency}RUB=X"

    status_msg = await message.answer(f"Генерирую график {currency}/RUB...")
    await message.bot.send_chat_action(chat_id=message.chat.id, action="upload_photo")

    # Run synchronous chart generation in a thread or executor if needed,
    # but for simplicity calling direct here (it blocks, but short time).
    # Ideally should use run_in_executor.
    loop = asyncio.get_running_loop()

    try:
        # Run yfinance/matplotlib in executor to avoid blocking event loop
        # Add timeout to prevent hanging
        buf = await asyncio.wait_for(
            loop.run_in_executor(None, generate_chart, ticker),
            timeout=30.0
        )

        if buf:
            await status_msg.delete()
            photo = BufferedInputFile(buf.read(), filename=f"chart_{currency}.png")
            await message.reply_photo(photo, caption=f"График {currency}/RUB за месяц")
        else:
            await status_msg.edit_text("Не удалось получить данные для графика. Возможно, тикер не найден.")
    except asyncio.TimeoutError:
        await status_msg.edit_text("⏱️ Превышено время ожидания. Попробуйте позже.")
    except Exception as e:
        logger.error(f"Error generating chart: {e}", exc_info=True)
        await status_msg.edit_text("❌ Произошла ошибка при генерации графика.")

@main_router.callback_query(F.data.startswith("toggle_"))
async def on_toggle_currency(callback: CallbackQuery, session: AsyncSession):
    currency = callback.data.split("_")[1]

    # UX Improvement: Prevent disabling the last currency to avoid "broken" state
    settings = await get_chat_settings(session, callback.message.chat.id)
    current_currencies = settings.target_currencies

    if currency in current_currencies and len(current_currencies) == 1:
        await callback.answer("⚠️ Нельзя отключить последнюю валюту!", show_alert=True)
        return

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

    response = await convert_prices(prices, session, message.chat.id)
    if response:
        await message.reply(response)

@main_router.message(F.photo)
async def handle_photo(message: Message, session: AsyncSession):
    """
    Handles photo messages. Downloads the photo, performs OCR to extract text,
    and then runs currency recognition in strict mode (requiring symbols).
    """
    is_private = message.chat.type == "private"
    status_msg = None

    if is_private:
        status_msg = await message.answer("🔍 Распознаю текст...")
        # Show 'typing' action to indicate background processing
        await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")

    try:
        # Get the largest photo (last in list)
        photo = message.photo[-1]
        
        # Validate photo size (max 20MB to prevent abuse)
        MAX_PHOTO_SIZE = 20 * 1024 * 1024  # 20MB
        if photo.file_size and photo.file_size > MAX_PHOTO_SIZE:
            if is_private and status_msg:
                await status_msg.edit_text("⚠️ Изображение слишком большое (макс. 20MB)")
            return

        # Download photo with timeout
        file_io = io.BytesIO()
        try:
            await asyncio.wait_for(
                message.bot.download(photo, destination=file_io),
                timeout=30.0
            )
        except asyncio.TimeoutError:
            if is_private and status_msg:
                await status_msg.edit_text("⏱️ Превышено время загрузки изображения")
            return
            
        image_bytes = file_io.getvalue()

        # Run OCR in executor with timeout
        loop = asyncio.get_running_loop()
        try:
            text = await asyncio.wait_for(
                loop.run_in_executor(None, image_to_text, image_bytes),
                timeout=30.0
            )
        except asyncio.TimeoutError:
            if is_private and status_msg:
                await status_msg.edit_text("⏱️ Превышено время распознавания текста")
            return

        if not text:
            if is_private and status_msg:
                await status_msg.edit_text("Не удалось распознать текст.")
            return

        # Use strict mode for photos: require currency symbols
        prices = recognize(text, strict_mode=True)
        if not prices:
            if is_private and status_msg:
                await status_msg.edit_text("Не нашел валют на изображении.")
            return

        response = await convert_prices(prices, session, message.chat.id)

        if response:
            if is_private and status_msg:
                await status_msg.edit_text(response)
            else:
                await message.reply(response)
        else:
            if is_private and status_msg:
                await status_msg.edit_text("Валюты найдены, но не выбраны целевые валюты в настройках.")

    except Exception as e:
        logger.error(f"Error handling photo: {e}", exc_info=True)
        if is_private and status_msg:
            await status_msg.edit_text("Произошла ошибка при обработке изображения. Пожалуйста, попробуйте позже.")
        # In groups, stay silent on error
