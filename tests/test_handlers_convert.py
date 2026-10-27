import pytest
from unittest.mock import AsyncMock, patch

from src.bot.handlers import convert_prices
from src.services.recognizer import Price


async def _convert(prices, targets, rates):
    with patch("src.bot.handlers.get_target_currencies", new=AsyncMock(return_value=targets)), \
         patch("src.bot.handlers.rates_service.get_rates", new=AsyncMock(return_value=rates)):
        return await convert_prices(prices, AsyncMock(), 123)


@pytest.mark.asyncio
async def test_convert_prices_basic():
    result = await _convert([Price(228, "RUB")], ["RUB", "USD", "EUR"], {"USD": 1.0, "RUB": 80.0, "EUR": 0.86})

    assert result == "🇷🇺 228 RUB\n  🇺🇸 2.85 USD\n  🇪🇺 2.45 EUR"


@pytest.mark.asyncio
async def test_convert_prices_skips_missing_source_rate():
    """Regression: without a RUB rate the bot replied "228 RUB -> 0 USD, 0 EUR"."""
    result = await _convert([Price(228, "RUB")], ["RUB", "USD", "EUR"], {"USD": 1.0})

    assert result is None


@pytest.mark.asyncio
async def test_convert_prices_skips_missing_target_rate():
    result = await _convert([Price(100, "USD")], ["RUB", "EUR"], {"USD": 1.0, "RUB": 80.0})

    assert result == "🇺🇸 100 USD\n  🇷🇺 8000 RUB"


@pytest.mark.asyncio
async def test_convert_prices_large_amount_not_in_scientific_notation():
    result = await _convert([Price(350_000_000, "EUR")], ["EUR", "USD"], {"USD": 1.0, "EUR": 0.875})

    assert result == "🇪🇺 350000000 EUR\n  🇺🇸 400000000 USD"
