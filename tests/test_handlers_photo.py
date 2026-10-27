import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.types import Message, Chat, User
from src.bot.handlers import handle_photo

class _PhotoSize:
    def __init__(self, file_id="123", file_unique_id="abc", width=100, height=100, file_size=1000):
        self.file_id = file_id
        self.file_unique_id = file_unique_id
        self.width = width
        self.height = height
        self.file_size = file_size

@pytest.mark.asyncio
async def test_handle_photo_private_chat():
    # Private chat should always parse the photo
    chat = MagicMock(spec=Chat)
    chat.type = "private"
    chat.id = 123
    
    photo = _PhotoSize()
    
    message = MagicMock(spec=Message)
    message.chat = chat
    message.photo = [photo]
    message.caption = None
    message.reply_to_message = None
    message.bot = MagicMock()
    message.bot.get_me = AsyncMock(return_value=MagicMock(username="bot_user", id=999))
    message.bot.download = AsyncMock()
    message.bot.send_chat_action = AsyncMock()
    message.answer = AsyncMock()
    
    session = MagicMock()
    
    # image_to_text is now async, so we use AsyncMock
    mock_ocr = AsyncMock(return_value="text")
    with patch("src.bot.handlers.image_to_text", new=mock_ocr), \
         patch("src.bot.handlers.recognize", return_value=[]) as mock_recognize:
         
        await handle_photo(message, session)
        
        # Verify it went ahead with processing
        mock_ocr.assert_called_once()
        mock_recognize.assert_called_once()
        message.answer.assert_awaited_once_with("🔍 Распознаю текст...")

@pytest.mark.asyncio
async def test_handle_photo_group_chat_no_mention():
    # Group chat without mention or reply should ignore the photo
    chat = MagicMock(spec=Chat)
    chat.type = "group"
    chat.id = 123
    
    photo = _PhotoSize()
    
    message = MagicMock(spec=Message)
    message.chat = chat
    message.photo = [photo]
    message.caption = "Just a caption without mention"
    message.reply_to_message = None
    message.bot = MagicMock()
    message.bot.get_me = AsyncMock(return_value=MagicMock(username="bot_user", id=999))
    message.bot.download = AsyncMock()
    message.bot.send_chat_action = AsyncMock()
    message.answer = AsyncMock()
    
    session = MagicMock()
    
    mock_ocr = AsyncMock(return_value="text")
    with patch("src.bot.handlers.image_to_text", new=mock_ocr), \
         patch("src.bot.handlers.recognize", return_value=[]) as mock_recognize:
         
        await handle_photo(message, session)
        
        # Only the caption is checked for prices; the photo itself is NOT OCR'd
        mock_ocr.assert_not_called()
        mock_recognize.assert_called_once_with("Just a caption without mention")

@pytest.mark.asyncio
async def test_handle_photo_group_chat_with_mention():
    # Group chat with mention should parse the photo
    chat = MagicMock(spec=Chat)
    chat.type = "group"
    chat.id = 123
    
    photo = _PhotoSize()
    
    message = MagicMock(spec=Message)
    message.chat = chat
    message.photo = [photo]
    message.caption = "Привет @bot_user, переведи это"
    message.reply_to_message = None
    message.bot = MagicMock()
    message.bot.get_me = AsyncMock(return_value=MagicMock(username="bot_user", id=999))
    message.bot.download = AsyncMock()
    message.bot.send_chat_action = AsyncMock()
    message.answer = AsyncMock()
    message.reply = AsyncMock()
    
    session = MagicMock()
    
    mock_ocr = AsyncMock(return_value="text")
    with patch("src.bot.handlers.image_to_text", new=mock_ocr), \
         patch("src.bot.handlers.recognize", return_value=[]) as mock_recognize:
         
        await handle_photo(message, session)
        
        # Verify it went ahead with processing: caption has no prices, so the photo is OCR'd
        mock_ocr.assert_called_once()
        mock_recognize.assert_called_with("text", strict_mode=True)

@pytest.mark.asyncio
async def test_handle_photo_group_chat_with_reply():
    # Group chat with reply to bot should parse the photo
    chat = MagicMock(spec=Chat)
    chat.type = "group"
    chat.id = 123
    
    photo = _PhotoSize()
    
    bot_msg = MagicMock(spec=Message)
    bot_msg.from_user = MagicMock(spec=User)
    bot_msg.from_user.id = 999
    
    message = MagicMock(spec=Message)
    message.chat = chat
    message.photo = [photo]
    message.caption = None
    message.reply_to_message = bot_msg
    message.bot = MagicMock()
    message.bot.get_me = AsyncMock(return_value=MagicMock(username="bot_user", id=999))
    message.bot.download = AsyncMock()
    message.bot.send_chat_action = AsyncMock()
    message.answer = MagicMock()
    message.reply = AsyncMock()
    
    session = MagicMock()
    
    mock_ocr = AsyncMock(return_value="text")
    with patch("src.bot.handlers.image_to_text", new=mock_ocr), \
         patch("src.bot.handlers.recognize", return_value=[]) as mock_recognize:
         
        await handle_photo(message, session)
        
        # Verify it went ahead with processing
        mock_ocr.assert_called_once()
        mock_recognize.assert_called_once()


@pytest.mark.asyncio
async def test_handle_photo_private_chat_rates_unavailable():
    # Regression: without rates the bot claimed that no target currencies were selected
    chat = MagicMock(spec=Chat)
    chat.type = "private"
    chat.id = 123

    status_msg = MagicMock()
    status_msg.edit_text = AsyncMock()

    message = MagicMock(spec=Message)
    message.chat = chat
    message.photo = [_PhotoSize()]
    message.caption = None
    message.reply_to_message = None
    message.bot = MagicMock()
    message.bot.download = AsyncMock()
    message.bot.send_chat_action = AsyncMock()
    message.answer = AsyncMock(return_value=status_msg)

    mock_ocr = AsyncMock(return_value="299\n95\nруб.")
    with patch("src.bot.handlers.image_to_text", new=mock_ocr), \
         patch("src.bot.handlers.get_target_currencies", new=AsyncMock(return_value=("RUB", "USD"))), \
         patch("src.bot.handlers.rates_service.get_rates", new=AsyncMock(return_value={})):

        await handle_photo(message, MagicMock())

    status_msg.edit_text.assert_awaited_once_with("Валюты найдены, но курсы сейчас недоступны. Попробуйте позже.")
