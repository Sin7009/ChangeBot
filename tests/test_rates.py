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
    yield service
    service._consecutive_failures = 0


@pytest.mark.asyncio
async def test_fetch_rates_returns_none_when_all_downloads_fail(fresh_service):
    """Regression: yfinance logs SSLError instead of raising and returns no data."""
    with patch("src.services.rates.yf.download", return_value=pd.DataFrame()):
        assert await fresh_service._fetch_rates() is None


@pytest.mark.asyncio
async def test_failed_update_keeps_cached_rates_and_backs_off(fresh_service):
    """Regression: a failed update used to replace the cache with {"USD": 1.0}, so 228 RUB -> 0 USD."""
    with patch("src.services.rates.yf.download", return_value=pd.DataFrame()) as mock_download:
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
