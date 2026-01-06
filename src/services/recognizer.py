import re
from dataclasses import dataclass
from typing import List, Dict, Optional, Set

@dataclass
class Price:
    amount: float
    currency: str

class CurrencyRecognizer:
    # Valid currency codes - whitelist to prevent false positives
    VALID_CURRENCIES = {
        # Fiat currencies
        "USD", "EUR", "RUB", "GBP", "CNY", "KZT", "TRY", "JPY",
        # Crypto
        "BTC", "ETH", "TON", "USDT"
    }

    # Symbols that are considered "signs" for strict mode
    SYMBOLS: Set[str] = {"$", "€", "£", "¥", "₽", "₸", "₿"}
    
    # Slang mapping
    SLANG_MAP: Dict[str, str] = {
        # USD
        "бакс": "USD", "баксов": "USD", "баксы": "USD", "dollar": "USD", "$": "USD",
        "доллар": "USD", "доллара": "USD", "долларов": "USD", "доллары": "USD",
        
        # EUR
        "евро": "EUR", "euro": "EUR", "€": "EUR",
        
        # RUB
        "руб": "RUB", "рубль": "RUB", "рублей": "RUB", "р": "RUB", "ruble": "RUB", "₽": "RUB",
        
        # GBP
        "фунт": "GBP", "pound": "GBP", "£": "GBP", "фунтов": "GBP", "фунта": "GBP",
        
        # KZT
        "тенге": "KZT", "тг": "KZT", "₸": "KZT",
        
        # CNY
        "юань": "CNY", "юаней": "CNY", "юаня": "CNY", "cny": "CNY", "¥": "CNY",
        
        # Crypto
        "биток": "BTC", "битка": "BTC", "битков": "BTC", "btc": "BTC", "bitcoin": "BTC", "₿": "BTC",
        "эфир": "ETH", "эфира": "ETH", "эфиров": "ETH", "eth": "ETH", "ethereum": "ETH",
        "ton": "TON", "тон": "TON",
        "usdt": "USDT", "tether": "USDT"
    }

    # OPTIMIZATION: Pre-populate SLANG_MAP with valid currencies (lowercase) to avoid
    # redundant length/alpha checks and upper() calls in _validate_currency_code.
    # This makes validation an O(1) dict lookup for all valid codes.
    for currency in VALID_CURRENCIES:
        if currency.lower() not in SLANG_MAP:
            SLANG_MAP[currency.lower()] = currency

    # Multiplier mapping
    MULTIPLIER_MAP: Dict[str, float] = {
        "k": 1000.0,
        "к": 1000.0,
        "m": 1000000.0,
        "м": 1000000.0,
        "косарь": 1000.0,
        "косаря": 1000.0,
        "косарей": 1000.0,
        "тонна": 1000.0,
        "лям": 1000000.0,
        "лямов": 1000000.0,
        
        # Extended multipliers
        "тысяча": 1000.0, "тысячи": 1000.0, "тысяч": 1000.0,
        "миллион": 1000000.0, "миллиона": 1000000.0, "миллионов": 1000000.0, "млн": 1000000.0,
        "миллиард": 1000000000.0, "миллиарда": 1000000000.0, "миллиардов": 1000000000.0, "млрд": 1000000000.0,
        "триллион": 1000000000000.0, "триллиона": 1000000000000.0, "триллионов": 1000000000000.0, "трлн": 1000000000000.0,
    }

    # Slang terms that imply RUB when used as multipliers
    IMPLIED_RUBLE_TOKENS = {"косарь", "косаря", "косарей", "лям", "лямов", "тонна"}

    # Dynamic regex parts
    # Suffix style: k, m, к, м (followed by non-letters)
    _SUFFIX_REGEX = r'[kкmм](?![a-zA-Zа-яА-Я])'
    # Word style: match any key in MULTIPLIER_MAP that is > 1 char
    _WORD_MULTIPLIERS = sorted([k for k in MULTIPLIER_MAP.keys() if len(k) > 1], key=len, reverse=True)
    _WORD_REGEX = r'(?:' + '|'.join(map(re.escape, _WORD_MULTIPLIERS)) + r')'
    
    # Combined Multiplier Regex: (Suffix | Word)
    MULTIPLIER_REGEX = f'(?:{_SUFFIX_REGEX}|{_WORD_REGEX})'

    # OPTIMIZATION: Construct whitelist of currency tokens to avoid false positives.
    # Instead of matching [a-zA-Z]+ and checking dict in Python, we match only valid tokens in regex.
    # This prevents the loop from triggering on "100 apples".
    # Note: text is lowercased before matching, so these keys (lowercase) handle all cases.
    _CURRENCY_TOKENS = set(SLANG_MAP.keys())
    # Add multiplier-as-currency tokens (e.g. "косарь", "лям")
    _CURRENCY_TOKENS.update(IMPLIED_RUBLE_TOKENS)
    # Note: SYMBOLS are already in SLANG_MAP keys, so they are included here.

    _CURRENCY_TOKEN_REGEX = r'(?:' + '|'.join(map(re.escape, sorted(_CURRENCY_TOKENS, key=len, reverse=True))) + r')'

    # Regex to capture amount and currency/slang
    # Group 1: Amount
    # Group 2: Multiplier (optional)
    # Group 3: Currency
    PATTERN_START = re.compile(
        rf'(\d+(?:[.,]\d+)?)\s*({MULTIPLIER_REGEX})?\s*({_CURRENCY_TOKEN_REGEX})'
    )
    
    # Currency Number [multiplier]
    PATTERN_END = re.compile(
        rf'({_CURRENCY_TOKEN_REGEX})\s*(\d+(?:[.,]\d+)?)\s*({MULTIPLIER_REGEX})?'
    )

    SLANG_AMOUNT_CURRENCY = {
        "косарь": (1000.0, "RUB"),
        "косаря": (1000.0, "RUB"),
        "косарей": (1000.0, "RUB"),
        "лям": (1000000.0, "RUB"),
        "лямов": (1000000.0, "RUB"),
    }

    # Compiled pattern for standalone slang words
    # Matches words from SLANG_AMOUNT_CURRENCY if not preceded by a digit
    STANDALONE_SLANG_PATTERN = re.compile(
        r'(?<!\d)\s*(?<!\d\s)(' +
        '|'.join(map(re.escape, sorted(SLANG_AMOUNT_CURRENCY.keys(), key=len, reverse=True))) +
        r')\b'
    )

    # OPTIMIZATION: Combined regex for single-pass scanning
    # Combines PATTERN_START, PATTERN_END, and STANDALONE_SLANG_PATTERN
    # Groups:
    # 1,2,3: Start Pattern (Amount, Multiplier, Currency)
    # 4,5,6: End Pattern (Currency, Amount, Multiplier)
    # 7: Standalone Slang
    COMBINED_PATTERN = re.compile(
        rf'(?:(\d+(?:[.,]\d+)?)\s*({MULTIPLIER_REGEX})?\s*({_CURRENCY_TOKEN_REGEX}))|'
        rf'(?:({_CURRENCY_TOKEN_REGEX})\s*(\d+(?:[.,]\d+)?)\s*({MULTIPLIER_REGEX})?)|'
        rf'(?:(?<!\d)\s*(?<!\d\s)(' + '|'.join(map(re.escape, sorted(SLANG_AMOUNT_CURRENCY.keys(), key=len, reverse=True))) + r')\b)'
    )

    # Compiled pattern for detecting thousands separators (e.g., "1,000")
    # Matches comma followed by exactly 3 digits and (end of string or non-digit)
    THOUSANDS_SEPARATOR_PATTERN = re.compile(r',\d{3}(?:\D|$)')

    @classmethod
    def _normalize_amount(cls, amount_str: str) -> float:
        """
        Normalize amount string to float, handling both comma as decimal separator
        and comma as thousands separator.
        
        Examples:
            "1,000" (thousands) -> 1000.0
            "1.5" (decimal) -> 1.5
            "1,5" (European decimal) -> 1.5
        """
        # If comma is followed by exactly 3 digits and then non-digit or end,
        # it's likely a thousands separator (e.g., "1,000" or "10,000")
        # Otherwise, treat it as a decimal separator (e.g., "1,5" -> 1.5)
        
        if cls.THOUSANDS_SEPARATOR_PATTERN.search(amount_str):
            # Remove comma as thousands separator
            return float(amount_str.replace(',', ''))
        else:
            # Treat comma as decimal separator
            return float(amount_str.replace(',', '.'))

    @classmethod
    def parse(cls, text: str, strict_mode: bool = False) -> List[Price]:
        """
        Parses text to identify currency amounts.

        Args:
            text: The input string to parse.
            strict_mode: If True, only matches currencies with explicit symbols (e.g., $, €)
                         and strict patterns. Used to reduce false positives in OCR text.

        Returns:
            A list of recognized Price objects.
        """
        results = []

        # Stop words removal was removed as it was redundant and caused false positives
        # (e.g. "100 gb usd" -> "100 usd"). The whitelist regex handles non-currency words correctly.
        text_cleaned = text.lower()

        # Optimization: Single pass using combined regex
        for match in cls.COMBINED_PATTERN.finditer(text_cleaned):
            # Check which group matched
            # Groups 1-3: Start Pattern (Amount, Multiplier, Currency)
            if match.group(1):
                amount_str, multiplier_str, currency_raw = match.group(1), match.group(2), match.group(3)
                amount = cls._normalize_amount(amount_str)

                # Strict mode check
                if strict_mode:
                    if currency_raw not in cls.SYMBOLS:
                        continue

                multiplier = 1.0
                if multiplier_str:
                    multiplier = cls.MULTIPLIER_MAP.get(multiplier_str, 1.0)

                # Check if currency_raw is actually a special slang amount
                if currency_raw in cls.MULTIPLIER_MAP and currency_raw not in cls.SLANG_MAP:
                    multiplier *= cls.MULTIPLIER_MAP[currency_raw]
                    if currency_raw in cls.IMPLIED_RUBLE_TOKENS:
                        currency_code = "RUB"
                    else:
                        continue
                else:
                    currency_code = cls.SLANG_MAP.get(currency_raw)
                    if not currency_code:
                        continue

                results.append(Price(amount=amount * multiplier, currency=currency_code))

            # Groups 4-6: End Pattern (Currency, Amount, Multiplier)
            elif match.group(4):
                currency_raw, amount_str, multiplier_str = match.group(4), match.group(5), match.group(6)
                amount = cls._normalize_amount(amount_str)

                # Strict mode check
                if strict_mode:
                    if currency_raw not in cls.SYMBOLS:
                        continue

                currency_code = cls.SLANG_MAP.get(currency_raw)
                if not currency_code:
                    continue

                multiplier = 1.0
                if multiplier_str:
                    multiplier = cls.MULTIPLIER_MAP.get(multiplier_str, 1.0)

                results.append(Price(amount=amount * multiplier, currency=currency_code))

            # Group 7: Standalone Slang
            elif match.group(7) and not strict_mode:
                word = match.group(7)
                if word in cls.SLANG_AMOUNT_CURRENCY:
                    val, curr = cls.SLANG_AMOUNT_CURRENCY[word]
                    results.append(Price(amount=val, currency=curr))

        return results

def recognize(text: str, strict_mode: bool = False) -> List[Price]:
    return CurrencyRecognizer.parse(text, strict_mode)
