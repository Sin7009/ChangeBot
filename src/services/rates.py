import asyncio
import json
import logging
import os
import time
from typing import Any, Dict, Optional
import aiohttp
import yfinance as yf

logger = logging.getLogger(__name__)

class RatesService:
    _instance = None

    # Cache configuration
    CACHE_TTL = 3600  # 1 hour
    # Background updates keep the cache fresh, so replies never wait for the APIs
    UPDATE_INTERVAL = 900  # 15 minutes
    # Short enough not to stall a reply when Yahoo is unreachable: CBR rates cover fiat then
    FETCH_TIMEOUT = 10  # seconds timeout for yfinance calls

    # Official Central Bank of Russia rates (JSON mirror of cbr.ru/scripts/XML_daily.asp)
    CBR_URL = "https://www.cbr-xml-daily.ru/daily_json.js"
    CBR_TIMEOUT = 10  # seconds

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.rates = {}
            cls._instance.base_currency = "USD"
            cls._instance.last_updated = 0.0
            cls._instance._last_attempt = 0.0
            cls._instance._lock = asyncio.Lock()
            cls._instance._consecutive_failures = 0
            cls._instance._background_updates = False
            cls._instance.cache_path = None
            # No API key needed for yfinance

        return cls._instance

    async def _fetch_rates(self) -> Optional[Dict[str, float]]:
        """
        Fetches rates relative to USD from Yahoo Finance (market rates, crypto) and CBR.
        Yahoo is often unreachable from Russian networks, so CBR rates fill in the fiat
        currencies it fails to return.

        Returns:
            Dict of currency rates or None if neither source returned any
        """
        cbr_rates, yahoo_rates = await asyncio.gather(self._fetch_cbr_rates(), self._fetch_yahoo_rates())

        new_rates = {**(cbr_rates or {}), **(yahoo_rates or {})}
        if len(new_rates) <= 1:  # Nothing but the USD base
            return None

        return new_rates

    async def _fetch_cbr_rates(self) -> Optional[Dict[str, float]]:
        """Fetches official CBR rates. Returns None on failure."""
        try:
            timeout = aiohttp.ClientTimeout(total=self.CBR_TIMEOUT)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(self.CBR_URL) as response:
                    response.raise_for_status()
                    # Served as application/javascript
                    data = await response.json(content_type=None)

            return self._parse_cbr_rates(data)

        except Exception as e:
            logger.error(f"Error fetching rates from CBR: {e}")
            return None

    @staticmethod
    def _parse_cbr_rates(data: Dict[str, Any]) -> Dict[str, float]:
        """
        Converts CBR quotes (RUB per `Nominal` units, e.g. 17.85 RUB per 100 KZT)
        into rates relative to USD.
        """
        rub_per_unit = {
            code: quote["Value"] / quote["Nominal"]
            for code, quote in data["Valute"].items()
        }
        rub_per_usd = rub_per_unit["USD"]

        rates = {code: rub_per_usd / rub for code, rub in rub_per_unit.items()}
        rates["USD"] = 1.0
        rates["RUB"] = rub_per_usd
        return rates

    async def _fetch_yahoo_rates(self) -> Optional[Dict[str, float]]:
        """
        Fetches rates using yfinance with timeout and error handling.
        We want all rates relative to USD (USD -> XXX).
        So rate = how many XXX per 1 USD.
        
        Returns:
            Dict of currency rates or None on failure
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

            # Add timeout to prevent hanging on slow API responses
            try:
                data = await asyncio.wait_for(
                    loop.run_in_executor(None, fetch_sync),
                    timeout=self.FETCH_TIMEOUT
                )
            except asyncio.TimeoutError:
                logger.error(f"Timeout ({self.FETCH_TIMEOUT}s) fetching rates from yfinance")
                return None

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
                        if rate == 0: 
                            logger.warning(f"Zero rate for {ticker}, skipping")
                            continue
                        rate = 1.0 / rate

                    new_rates[code] = rate

                except Exception as e:
                    logger.warning(f"Failed to extract rate for {code} ({ticker}): {e}")
                    continue

            # yfinance logs download errors (e.g. SSLError) instead of raising,
            # so an outage shows up as a result with nothing but the USD base.
            if len(new_rates) == 1:
                logger.error("No rates fetched from yfinance")
                return None

            return new_rates

        except asyncio.TimeoutError:
            # Already handled above
            return None
        except Exception as e:
            logger.error(f"Error fetching rates from yfinance: {e}", exc_info=True)
            return None

    def _needs_update(self, now: float) -> bool:
        # After a failed update wait before retrying: otherwise every message would
        # pay the full fetch time while the API is down. Stale rates are served meanwhile.
        if self._consecutive_failures:
            backoff_time = min(3600, 60 * (2 ** (self._consecutive_failures - 1)))
            if now - self._last_attempt < backoff_time:
                return False

        return not self.rates or (now - self.last_updated > self.CACHE_TTL)

    async def _update(self) -> None:
        """Fetches rates into the cache. The caller must hold the lock."""
        now = time.time()
        logger.info("Updating rates...")
        new_rates = await self._fetch_rates()
        self._last_attempt = now
        if new_rates:
            # Merge so currencies missing from a partial response keep their last known rate
            self.rates = {**self.rates, **new_rates}
            self.last_updated = now
            self._consecutive_failures = 0
            self._save_cache()
        else:
            self._consecutive_failures += 1
            logger.warning("Using stale rates due to API failure.")

    async def run_updates(self) -> None:
        """Refreshes rates every UPDATE_INTERVAL until cancelled."""
        self._background_updates = True
        try:
            while True:
                try:
                    async with self._lock:
                        await self._update()
                except Exception as e:
                    logger.error(f"Background rates update failed: {e}", exc_info=True)

                await asyncio.sleep(self.UPDATE_INTERVAL)
        finally:
            self._background_updates = False

    def load_cache(self, path: str) -> None:
        """Restores rates saved by a previous run and saves new ones to `path` from now on."""
        self.cache_path = path
        try:
            with open(path, encoding="utf-8") as f:
                cached = json.load(f)
            self.rates = cached["rates"]
            self.last_updated = cached["updated_at"]
            logger.info(f"Loaded {len(self.rates)} cached rates from {path}")
        except FileNotFoundError:
            pass
        except Exception as e:
            logger.warning(f"Failed to load cached rates from {path}: {e}")

    def _save_cache(self) -> None:
        if not self.cache_path:
            return

        try:
            tmp_path = f"{self.cache_path}.tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump({"rates": self.rates, "updated_at": self.last_updated}, f)
            # Atomic, so a crash mid-write never leaves a broken cache
            os.replace(tmp_path, self.cache_path)
        except Exception as e:
            logger.warning(f"Failed to save rates to {self.cache_path}: {e}")

    async def get_rates(self) -> Dict[str, float]:
        """
        Returns rates, updating from API if cache is stale.
        
        Implements exponential backoff if consecutive failures occur to avoid
        hammering a failing API.
        
        Returns:
            Dict of currency rates (may be stale if API is down)
        """
        # Background updates refresh the cache: a reply waits only if there are no rates yet
        if self._background_updates and self.rates:
            return self.rates

        if self._needs_update(time.time()):
            # Use lock to prevent multiple concurrent API calls (cache stampede)
            async with self._lock:
                # Double-check cache condition after acquiring lock
                if self._needs_update(time.time()):
                    await self._update()

        return self.rates

    def calculate_conversion(self, amount: float, from_curr: str, to_curr: str, rates: Dict[str, float]) -> float:
        """
        Synchronous conversion logic using provided rates.
        Returns 0.0 if conversion fails.
        """
        from_curr = from_curr.upper()
        to_curr = to_curr.upper()

        # USD is base, ensure it exists conceptually
        rate_from = rates.get(from_curr)
        if rate_from is None and from_curr == "USD":
            rate_from = 1.0

        rate_to = rates.get(to_curr)
        if rate_to is None and to_curr == "USD":
            rate_to = 1.0

        if rate_from is None:
            logger.warning(f"Currency {from_curr} not found in rates.")
            return 0.0

        if rate_to is None:
            logger.warning(f"Currency {to_curr} not found in rates.")
            return 0.0

        if rate_from == 0.0:
            return 0.0

        return amount * (rate_to / rate_from)

    async def convert(self, amount: float, from_curr: str, to_curr: str) -> float:
        """
        Converts amount from `from_curr` to `to_curr`.
        Returns 0.0 if conversion fails.
        """
        rates = await self.get_rates()

        if not rates:
            logger.error("No rates available for conversion.")
            return 0.0

        return self.calculate_conversion(amount, from_curr, to_curr, rates)

rates_service = RatesService()
