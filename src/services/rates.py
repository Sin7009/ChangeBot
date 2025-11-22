import asyncio
import logging
import time
from typing import Dict, Optional
import aiohttp

from src.config import settings

logger = logging.getLogger(__name__)

class RatesService:
    _instance = None

    # Cache configuration
    CACHE_TTL = 3600  # 1 hour

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.rates = {}
            cls._instance.base_currency = "USD" # OER free plan base is USD
            cls._instance.last_updated = 0.0
            cls._instance.api_key = settings.OER_API_KEY.get_secret_value()
        return cls._instance

    async def _fetch_rates(self) -> Optional[Dict[str, float]]:
        """Fetches rates from OpenExchangeRates API."""
        url = f"https://openexchangerates.org/api/latest.json?app_id={self.api_key}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        logger.error(f"Failed to fetch rates: {response.status} {await response.text()}")
                        return None

                    data = await response.json()
                    # OER returns { "rates": { "EUR": 0.85, ... }, "base": "USD" ... }
                    return data.get("rates")
        except Exception as e:
            logger.error(f"Error fetching rates: {e}")
            return None

    async def get_rates(self) -> Dict[str, float]:
        """Returns rates, updating from API if cache is stale."""
        now = time.time()
        if not self.rates or (now - self.last_updated > self.CACHE_TTL):
            logger.info("Updating rates from API...")
            new_rates = await self._fetch_rates()
            if new_rates:
                self.rates = new_rates
                self.last_updated = now
            else:
                logger.warning("Using stale rates due to API failure.")

        return self.rates

    async def convert(self, amount: float, from_curr: str, to_curr: str) -> float:
        """
        Converts amount from `from_curr` to `to_curr`.
        Returns 0.0 if conversion fails (e.g. unknown currency).
        """
        from_curr = from_curr.upper()
        to_curr = to_curr.upper()

        rates = await self.get_rates()

        if not rates:
            logger.error("No rates available for conversion.")
            return 0.0

        # Add base currency to rates if not present (usually USD is base and value 1.0)
        # OER free tier base is USD.
        if "USD" not in rates:
            rates["USD"] = 1.0

        # Validation
        if from_curr not in rates and from_curr != "USD":
             logger.warning(f"Currency {from_curr} not found in rates.")
             return 0.0
        if to_curr not in rates and to_curr != "USD":
             logger.warning(f"Currency {to_curr} not found in rates.")
             return 0.0

        # Logic: Convert from -> Base -> To
        # Rate is "How many [Currency] per 1 USD"
        # e.g. USD=1, EUR=0.85.
        # 100 EUR -> USD? 100 / 0.85 = 117.64 USD
        # 100 USD -> EUR? 100 * 0.85 = 85 EUR

        # Formula: Amount * (Rate_To / Rate_From)

        rate_from = rates.get(from_curr, 1.0 if from_curr == "USD" else 0.0)
        rate_to = rates.get(to_curr, 1.0 if to_curr == "USD" else 0.0)

        if rate_from == 0.0:
            return 0.0

        return amount * (rate_to / rate_from)

rates_service = RatesService()
