import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.database.dal import get_target_currencies, toggle_currency, _settings_cache, CACHE_TTL

@pytest.mark.asyncio
async def test_get_target_currencies_caching():
    # Setup
    chat_id = 12345
    mock_session = AsyncMock()

    # Mock settings object
    mock_settings = MagicMock()
    mock_settings.target_currencies = ["USD", "EUR"]

    # We need to mock get_chat_settings to return this object
    with patch("src.database.dal.get_chat_settings", new_callable=AsyncMock) as mock_get_settings:
        mock_get_settings.return_value = mock_settings

        # Clear cache
        _settings_cache.clear()

        # 1. First call - should hit DB
        currencies = await get_target_currencies(mock_session, chat_id)
        assert currencies == ("USD", "EUR")
        assert mock_get_settings.call_count == 1

        # 2. Second call - should hit cache (no DB)
        currencies_2 = await get_target_currencies(mock_session, chat_id)
        assert currencies_2 == ("USD", "EUR")
        assert mock_get_settings.call_count == 1  # Still 1

        # 3. Cache expiration (simulate)
        import time
        _settings_cache[chat_id] = (time.time() - CACHE_TTL - 1, ("OLD",))

        currencies_3 = await get_target_currencies(mock_session, chat_id)
        assert currencies_3 == ("USD", "EUR")  # Should fetch fresh
        assert mock_get_settings.call_count == 2

@pytest.mark.asyncio
async def test_toggle_currency_updates_cache():
    chat_id = 67890
    mock_session = AsyncMock()

    mock_settings = MagicMock()
    mock_settings.target_currencies = ["USD"]

    # We need to mock get_chat_settings to return this object
    with patch("src.database.dal.get_chat_settings", new_callable=AsyncMock) as mock_get_settings:
        mock_get_settings.return_value = mock_settings

        # Populate cache with future expiration
        import time
        _settings_cache[chat_id] = (time.time() + 1000, ("USD",))

        # Toggle currency
        # toggle_currency calls get_chat_settings internally too
        # AND it modifies the list.
        # We need to ensure toggle_currency sees the object and modifies it.
        # Since mock_settings is returned by get_chat_settings, modification to .target_currencies
        # inside toggle_currency will work on mock_settings.

        await toggle_currency(mock_session, chat_id, "EUR")

        # Check if cache is updated in dal
        cached_time, cached_data = _settings_cache[chat_id]
        assert isinstance(cached_data, tuple)
        assert "EUR" in cached_data
        assert "USD" in cached_data
