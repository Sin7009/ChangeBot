import pytest
from unittest.mock import AsyncMock, patch

from src.bot.handlers import handle_text


class _Chat:
    def __init__(self, chat_id=123):
        self.id = chat_id


class _Message:
    def __init__(self, text: str):
        self.text = text
        self.chat = _Chat()
        self.reply = AsyncMock()


@pytest.mark.asyncio
async def test_handle_text_offer_advice_when_no_direct_price_parse():
    message = _Message(
        'Стоит или не стоит соглашаться на такое предложение. '
        'Starting July 1 price increase from $249.99 USD to $749.99 USD. Buy now.'
    )
    session = AsyncMock()

    with patch('src.bot.handlers.recognize', return_value=[]):
        await handle_text(message, session)

    message.reply.assert_awaited_once()
    sent_call = message.reply.await_args
    assert sent_call is not None
    sent = sent_call.args[0]
    assert '249.99 USD' in sent
    assert '749.99 USD' in sent


@pytest.mark.asyncio
async def test_handle_text_offer_advice_not_sent_for_irrelevant_text():
    message = _Message('Привет, как дела?')
    session = AsyncMock()

    with patch('src.bot.handlers.recognize', return_value=[]):
        await handle_text(message, session)

    message.reply.assert_not_called()
