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
            # No API key needed for yfinance

        return cls._instance

    async def _fetch_rates(self) -> Optional[Dict[str, float]]:
        """
        Fetches rates using yfinance.
        We want all rates relative to USD (USD -> XXX).
        So rate = how many XXX per 1 USD.

        Tickers strategy:
        Fiat pairs are usually quoted as BaseQuote=X.
        e.g. RUB=X means "USD/RUB" (How many RUB per USD). Value ~ 90.
        e.g. EUR=X means "USD/EUR" (How many EUR per USD). Value ~ 0.9.

        Crypto pairs are usually Quote-Base.
        e.g. BTC-USD means "BTC/USD" (How many USD per BTC). Value ~ 60000.
        To get "How many BTC per 1 USD", we invert it (1/60000).
        """

        # Map: Currency Code -> (Ticker, Is_Inverse)
        # Is_Inverse=False: Ticker value is "XXX per USD" (Direct rate)
        # Is_Inverse=True: Ticker value is "USD per XXX" (We need 1/value)

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
            "TON": ("TON11419-USD", True), # TON Coin ticker on Yahoo
            "USDT": ("USDT-USD", True),
        }

        tickers_list = [t[0] for t in TICKERS_MAP.values()]

        try:
            # We use a loop runner because yfinance is synchronous
            loop = asyncio.get_running_loop()

            def fetch_sync():
                # period="1d" gets recent data. We look at the last 'Close'.
                # group_by='ticker' ensures we get a MultiIndex if multiple tickers
                data = yf.download(tickers_list, period="1d", group_by='ticker', progress=False)
                return data

            data = await loop.run_in_executor(None, fetch_sync)

            new_rates = {"USD": 1.0}

            for code, (ticker, is_inverse) in TICKERS_MAP.items():
                try:
                    # Dataframe structure depends on number of tickers.
                    # If multiple, columns are (Ticker, PriceType).
                    # Accessing data[ticker]['Close'] gives a Series.
                    # We take the last value.

                    if len(tickers_list) > 1:
                        series = data[ticker]['Close']
                    else:
                        series = data['Close'] # Should not happen with multiple tickers

                    val = series.iloc[-1]

                    # Check for NaN
                    import math
                    if math.isnan(val):
                        logger.warning(f"NaN value for {ticker}")
                        continue

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

        # Add base currency if missing (USD=1.0 is set in _fetch_rates but just in case)
        if "USD" not in rates:
            rates["USD"] = 1.0

        # Logic: Convert from -> Base(USD) -> To
        # Rate is "How many [Currency] per 1 USD"

        rate_from = rates.get(from_curr)
        rate_to = rates.get(to_curr)

        if rate_from is None:
             logger.warning(f"Currency {from_curr} not found in rates.")
             # Fallback: if from is USD, rate is 1.0
             if from_curr == "USD": rate_from = 1.0
             else: return 0.0

        if rate_to is None:
             logger.warning(f"Currency {to_curr} not found in rates.")
             if to_curr == "USD": rate_to = 1.0
             else: return 0.0

        if rate_from == 0.0:
            return 0.0

        # Amount * (Rate_To / Rate_From)
        return amount * (rate_to / rate_from)

rates_service = RatesService()
