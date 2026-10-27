import asyncio
import json

import pandas as pd
import pytest
from unittest.mock import AsyncMock, patch
from src.services.rates import RatesService


@pytest.mark.asyncio
async def test_rates_service_singleton():
    """Test that RatesService is a singleton"""
    service1 = RatesService()
    service2 = RatesService()
    assert service1 is service2


@pytest.mark.asyncio
async def test_convert_same_currency():
    """Test conversion between same currency returns original amount"""
    service = RatesService()
    # Mock rates to avoid actual API calls
    service.rates = {"USD": 1.0, "EUR": 0.85, "RUB": 90.0}
    service.last_updated = 9999999999  # Far future to avoid cache expiry
    
    result = await service.convert(100, "USD", "USD")
    assert result == 100.0


@pytest.mark.asyncio
async def test_convert_to_missing_currency():
    """Test conversion to unknown currency returns 0.0"""
    service = RatesService()
    service.rates = {"USD": 1.0, "EUR": 0.85}
    service.last_updated = 9999999999
    
    result = await service.convert(100, "USD", "FAKE")
    assert result == 0.0


@pytest.mark.asyncio
async def test_convert_from_missing_currency():
    """Test conversion from unknown currency returns 0.0"""
    service = RatesService()
    service.rates = {"USD": 1.0, "EUR": 0.85}
    service.last_updated = 9999999999
    
    result = await service.convert(100, "FAKE", "USD")
    assert result == 0.0


@pytest.mark.asyncio
async def test_convert_with_zero_rate():
    """Test that zero rate in source currency returns 0.0"""
    service = RatesService()
    service.rates = {"USD": 1.0, "EUR": 0.85, "ZERO": 0.0}
    service.last_updated = 9999999999
    
    result = await service.convert(100, "ZERO", "USD")
    assert result == 0.0


@pytest.mark.asyncio
async def test_convert_basic_calculation():
    """Test basic currency conversion calculation"""
    service = RatesService()
    # Set up rates: 1 USD = 90 RUB, 1 USD = 0.85 EUR
    service.rates = {"USD": 1.0, "RUB": 90.0, "EUR": 0.85}
    service.last_updated = 9999999999
    
    # Convert 100 USD to RUB: 100 * (90 / 1) = 9000
    result = await service.convert(100, "USD", "RUB")
    assert result == 9000.0
    
    # Convert 100 EUR to USD: 100 * (1.0 / 0.85) ≈ 117.647
    result = await service.convert(100, "EUR", "USD")
    assert abs(result - 117.647) < 0.01


@pytest.mark.asyncio 
async def test_convert_handles_no_rates():
    """Test that convert handles the case when no rates are available"""
    service = RatesService()
    service.rates = {}
    service.last_updated = 0  # Expired cache
    
    # Mock _fetch_rates to return None (API failure)
    with patch.object(service, '_fetch_rates', return_value=None):
        result = await service.convert(100, "USD", "EUR")
        assert result == 0.0


@pytest.mark.asyncio
async def test_convert_with_realistic_transfer_question_amount():
    """Regression: 25k RUB -> USD conversion should produce non-zero rounded value."""
    service = RatesService()
    service.rates = {"USD": 1.0, "RUB": 71.19, "EUR": 0.8626}
    service.last_updated = 9999999999

    result = await service.convert(25000, "RUB", "USD")
    assert result > 0
    assert abs(result - 351.173) < 0.01


@pytest.fixture
def fresh_service():
    service = RatesService()
    service.rates = {"USD": 1.0, "RUB": 80.0, "EUR": 0.86}
    service.last_updated = 0  # Expired cache
    service._last_attempt = 0.0
    service._consecutive_failures = 0
    service._background_updates = False
    service.cache_path = None
    yield service
    service._consecutive_failures = 0
    service._background_updates = False
    service.cache_path = None


@pytest.mark.asyncio
async def test_fetch_yahoo_rates_returns_none_when_all_downloads_fail(fresh_service):
    """Regression: yfinance logs SSLError instead of raising and returns no data."""
    with patch("src.services.rates.yf.download", return_value=pd.DataFrame()):
        assert await fresh_service._fetch_yahoo_rates() is None


@pytest.mark.asyncio
async def test_failed_update_keeps_cached_rates_and_backs_off(fresh_service):
    """Regression: a failed update used to replace the cache with {"USD": 1.0}, so 228 RUB -> 0 USD."""
    with patch("src.services.rates.yf.download", return_value=pd.DataFrame()) as mock_download, \
         patch.object(fresh_service, "_fetch_cbr_rates", new=AsyncMock(return_value=None)), \
         patch.object(fresh_service, "_fetch_coingecko_rates", new=AsyncMock(return_value=None)):
        rates = await fresh_service.get_rates()
        assert rates["RUB"] == 80.0
        assert await fresh_service.convert(228, "RUB", "USD") == pytest.approx(2.85)

        # No retry on every message while in backoff
        assert mock_download.call_count == 1


@pytest.mark.asyncio
async def test_partial_update_keeps_missing_rates(fresh_service):
    with patch.object(fresh_service, "_fetch_rates", new=AsyncMock(return_value={"USD": 1.0, "EUR": 0.9})):
        rates = await fresh_service.get_rates()

    assert rates == {"USD": 1.0, "RUB": 80.0, "EUR": 0.9}
    assert fresh_service._consecutive_failures == 0


CBR_RESPONSE = {
    "Date": "2026-10-28T11:30:00+03:00",
    "Valute": {
        "USD": {"Nominal": 1, "Value": 80.0},
        "EUR": {"Nominal": 1, "Value": 92.0},
        "KZT": {"Nominal": 100, "Value": 16.0},
    },
}


def test_parse_cbr_rates_relative_to_usd():
    rates = RatesService._parse_cbr_rates(CBR_RESPONSE)

    assert rates["USD"] == 1.0
    assert rates["RUB"] == 80.0
    assert rates["EUR"] == pytest.approx(80.0 / 92.0)
    # 16 RUB per 100 KZT -> 500 KZT per USD
    assert rates["KZT"] == pytest.approx(500.0)


@pytest.mark.asyncio
async def test_fetch_rates_falls_back_to_cbr_when_yahoo_fails(fresh_service):
    """Regression: Yahoo is unreachable from the server, so after a restart there were no rates at all."""
    cbr = RatesService._parse_cbr_rates(CBR_RESPONSE)
    with patch.object(fresh_service, "_fetch_cbr_rates", new=AsyncMock(return_value=cbr)), \
         patch.object(fresh_service, "_fetch_coingecko_rates", new=AsyncMock(return_value=None)), \
         patch.object(fresh_service, "_fetch_yahoo_rates", new=AsyncMock(return_value=None)):
        rates = await fresh_service._fetch_rates()

    assert rates == cbr


@pytest.mark.asyncio
async def test_fetch_rates_prefers_yahoo_over_cbr(fresh_service):
    cbr = RatesService._parse_cbr_rates(CBR_RESPONSE)
    yahoo = {"USD": 1.0, "RUB": 81.5, "BTC": 1 / 100_000}
    with patch.object(fresh_service, "_fetch_cbr_rates", new=AsyncMock(return_value=cbr)), \
         patch.object(fresh_service, "_fetch_coingecko_rates", new=AsyncMock(return_value=None)), \
         patch.object(fresh_service, "_fetch_yahoo_rates", new=AsyncMock(return_value=yahoo)):
        rates = await fresh_service._fetch_rates()

    assert rates["RUB"] == 81.5
    assert rates["EUR"] == cbr["EUR"]
    assert rates["BTC"] == yahoo["BTC"]


@pytest.mark.asyncio
async def test_fetch_rates_returns_none_when_all_sources_fail(fresh_service):
    with patch.object(fresh_service, "_fetch_cbr_rates", new=AsyncMock(return_value=None)), \
         patch.object(fresh_service, "_fetch_coingecko_rates", new=AsyncMock(return_value=None)), \
         patch.object(fresh_service, "_fetch_yahoo_rates", new=AsyncMock(return_value=None)):
        assert await fresh_service._fetch_rates() is None


@pytest.mark.asyncio
async def test_update_saves_cache_and_load_restores_it(fresh_service, tmp_path):
    path = tmp_path / "rates_cache.json"
    fresh_service.load_cache(str(path))  # No file yet: nothing changes

    assert fresh_service.rates["RUB"] == 80.0

    with patch.object(fresh_service, "_fetch_rates", new=AsyncMock(return_value={"USD": 1.0, "RUB": 81.0})):
        await fresh_service.get_rates()

    saved = json.loads(path.read_text())
    assert saved["rates"]["RUB"] == 81.0
    assert saved["updated_at"] == fresh_service.last_updated

    # A restart starts from the saved rates
    fresh_service.rates = {}
    fresh_service.load_cache(str(path))
    assert fresh_service.rates["RUB"] == 81.0


def test_load_cache_ignores_broken_file(fresh_service, tmp_path):
    path = tmp_path / "rates_cache.json"
    path.write_text("{not json")

    fresh_service.load_cache(str(path))

    assert fresh_service.rates["RUB"] == 80.0


@pytest.mark.asyncio
async def test_get_rates_does_not_fetch_while_background_updates_run(fresh_service):
    """Stale rates are served at once: the background task refreshes them."""
    fresh_service._background_updates = True
    with patch.object(fresh_service, "_fetch_rates", new=AsyncMock()) as mock_fetch:
        rates = await fresh_service.get_rates()

    assert rates["RUB"] == 80.0
    mock_fetch.assert_not_called()


@pytest.mark.asyncio
async def test_get_rates_fetches_without_any_rates_even_with_background_updates(fresh_service):
    fresh_service._background_updates = True
    fresh_service.rates = {}
    with patch.object(fresh_service, "_fetch_rates", new=AsyncMock(return_value={"USD": 1.0, "RUB": 81.0})):
        rates = await fresh_service.get_rates()

    assert rates["RUB"] == 81.0


@pytest.mark.asyncio
async def test_run_updates_survives_a_failed_update(fresh_service):
    update = AsyncMock(side_effect=[RuntimeError("boom"), None])
    sleep = AsyncMock(side_effect=[None, asyncio.CancelledError()])
    with patch.object(fresh_service, "_update", new=update), \
         patch("src.services.rates.asyncio.sleep", new=sleep):
        with pytest.raises(asyncio.CancelledError):
            await fresh_service.run_updates()

    assert update.await_count == 2
    sleep.assert_awaited_with(fresh_service.UPDATE_INTERVAL)
    assert fresh_service._background_updates is False


def test_parse_coingecko_rates():
    rates = RatesService._parse_coingecko_rates({
        "bitcoin": {"usd": 80_000},
        "the-open-network": {"usd": 1.25},
        "ethereum": {},  # Missing price is skipped
    })

    assert rates == {"BTC": 1 / 80_000, "TON": 0.8}


@pytest.mark.asyncio
async def test_fetch_rates_takes_crypto_from_coingecko_when_yahoo_fails(fresh_service):
    """Regression: with Yahoo blocked there were no crypto rates at all."""
    cbr = RatesService._parse_cbr_rates(CBR_RESPONSE)
    crypto = {"BTC": 1 / 80_000, "TON": 0.8}
    with patch.object(fresh_service, "_fetch_cbr_rates", new=AsyncMock(return_value=cbr)), \
         patch.object(fresh_service, "_fetch_coingecko_rates", new=AsyncMock(return_value=crypto)), \
         patch.object(fresh_service, "_fetch_yahoo_rates", new=AsyncMock(return_value=None)):
        rates = await fresh_service._fetch_rates()

    assert rates["BTC"] == 1 / 80_000
    assert rates["RUB"] == 80.0
