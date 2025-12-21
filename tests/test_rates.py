import pytest
from unittest.mock import Mock, patch, AsyncMock
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
