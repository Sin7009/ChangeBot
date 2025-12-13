import asyncio
import logging
import time
from typing import Dict, Optional
import yfinance as yf

logger = logging.getLogger(__name__)

class RatesService:
    _instance = None

    # Cache configuration
    CACHE_TTL = 3600  # 1 hour

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.rates = {}
            cls._instance.base_currency = "USD"
            cls._instance.last_updated = 0.0
            cls._instance._lock = asyncio.Lock()
            # No API key needed for yfinance

        return cls._instance

    async def _fetch_rates(self) -> Optional[Dict[str, float]]:
        """
        Fetches rates using yfinance.
        We want all rates relative to USD (USD -> XXX).
        So rate = how many XXX per 1 USD.
        """

        # Map: Currency Code -> (Ticker, Is_Inverse)
        TICKERS_MAP = {
            "RUB": ("RUB=X", False),
            "EUR": ("EUR=X", False),
            "GBP": ("GBP=X", False),
            "CNY": ("CNY=X", False),
            "KZT": ("KZT=X", False),
            "TRY": ("TRY=X", False),
            "JPY": ("JPY=X", False),

            # Crypto
            "BTC": ("BTC-USD", True),
            "ETH": ("ETH-USD", True),
            "TON": ("TON11419-USD", True),
            "USDT": ("USDT-USD", True),
        }

        tickers_list = [t[0] for t in TICKERS_MAP.values()]

        try:
            loop = asyncio.get_running_loop()

            def fetch_sync():
                # Fetch data for 5 days to avoid empty values on weekends/holidays
                data = yf.download(tickers_list, period="5d", group_by='ticker', progress=False)
                return data

            data = await loop.run_in_executor(None, fetch_sync)

            new_rates = {"USD": 1.0}

            for code, (ticker, is_inverse) in TICKERS_MAP.items():
                try:
                    if len(tickers_list) > 1:
                        series = data[ticker]['Close']
                    else:
                        series = data['Close']

                    # Remove NaN and take the last valid value
                    valid_values = series.dropna()
                    
                    if valid_values.empty:
                        logger.warning(f"No valid data found for {ticker}")
                        continue

                    val = valid_values.iloc[-1]

                    rate = float(val)
                    if is_inverse:
                        if rate == 0: continue
                        rate = 1.0 / rate

                    new_rates[code] = rate

                except Exception as e:
                    logger.warning(f"Failed to extract rate for {code} ({ticker}): {e}")
                    continue

            return new_rates

        except Exception as e:
            logger.error(f"Error fetching rates from yfinance: {e}")
            return None

    async def get_rates(self) -> Dict[str, float]:
        """Returns rates, updating from API if cache is stale."""
        now = time.time()
        if not self.rates or (now - self.last_updated > self.CACHE_TTL):
            # Use lock to prevent multiple concurrent API calls (cache stampede)
            async with self._lock:
                # Double-check cache condition after acquiring lock
                now = time.time()
                if not self.rates or (now - self.last_updated > self.CACHE_TTL):
                    logger.info("Updating rates from yfinance...")
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
        Returns 0.0 if conversion fails.
        """
        from_curr = from_curr.upper()
        to_curr = to_curr.upper()

        rates = await self.get_rates()

        if not rates:
            logger.error("No rates available for conversion.")
            return 0.0

        if "USD" not in rates:
            rates["USD"] = 1.0

        rate_from = rates.get(from_curr)
        rate_to = rates.get(to_curr)

        if rate_from is None:
             # Fallback for USD base
             if from_curr == "USD": rate_from = 1.0
             else: 
                 logger.warning(f"Currency {from_curr} not found in rates.")
                 return 0.0

        if rate_to is None:
             if to_curr == "USD": rate_to = 1.0
             else:
                 logger.warning(f"Currency {to_curr} not found in rates.")
                 return 0.0

        if rate_from == 0.0:
            return 0.0

        return amount * (rate_to / rate_from)

rates_service = RatesService()
