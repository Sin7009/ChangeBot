import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.types import Message, Chat

from src.bot.handlers import handle_caption, handle_photo


def _group_message(caption: str) -> MagicMock:
    chat = MagicMock(spec=Chat)
    chat.type = "supergroup"
    chat.id = 123

    message = MagicMock(spec=Message)
    message.chat = chat
    message.caption = caption
    message.reply_to_message = None
    message.bot = MagicMock()
    message.bot.get_me = AsyncMock(return_value=MagicMock(username="bot_user", id=999))
    message.reply = AsyncMock()
    return message


def _patch_rates():
    return (
        patch("src.bot.handlers.get_target_currencies", new=AsyncMock(return_value=["RUB", "USD"])),
        patch("src.bot.handlers.rates_service.get_rates", new=AsyncMock(return_value={"USD": 1.0, "RUB": 80.0})),
    )


@pytest.mark.asyncio
async def test_handle_photo_group_chat_caption_with_prices():
    # Forwarded channel post: prices in the caption are converted without a mention and without OCR
    message = _group_message("Петербуржец отсудил 900 тысяч рублей за увольнение из-за опозданий")
    message.photo = [MagicMock(file_size=1000)]

    mock_ocr = AsyncMock(return_value="text")
    targets, rates = _patch_rates()
    with patch("src.bot.handlers.image_to_text", new=mock_ocr), targets, rates:
        await handle_photo(message, MagicMock())

    mock_ocr.assert_not_called()
    message.reply.assert_awaited_once()
    sent = message.reply.await_args.args[0]
    assert "900000 RUB" in sent
    assert "11250 USD" in sent


@pytest.mark.asyncio
async def test_handle_caption_of_video():
    message = _group_message("Продажи выросли до €2 млрд, а билет стоит 500 ₽")

    targets, rates = _patch_rates()
    with targets, rates:
        await handle_caption(message, MagicMock())

    message.reply.assert_awaited_once()
    sent = message.reply.await_args.args[0]
    assert "500 RUB" in sent
    assert "6.25 USD" in sent
