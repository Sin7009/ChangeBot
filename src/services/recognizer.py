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
        "миллион": 1000000.0, "миллиона": 1000000.0, "миллионов": 1000000.0,
        "млн": 1000000.0,
        "миллиард": 1000000000.0, "миллиарда": 1000000000.0,
        "миллиардов": 1000000000.0, "млрд": 1000000000.0,
        "триллион": 1000000000000.0, "триллиона": 1000000000000.0,
        "триллионов": 1000000000000.0, "трлн": 1000000000000.0,
    }

    STOP_WORDS = {
        "pro", "max", "plus", "ultra", "mini", "slim",
        "gb", "tb", "гб", "тб", "мб", "кб",
        "шт", "уп", "kg", "кг",
        "цена", "price", "сумма", "итого", "total",
        # Technical terms that can be mistaken for currencies
        "bit", "бит", "gpu", "rtx", "gtx", "cpu", "ram",
        "ssd", "hdd", "mhz", "ghz", "ddr",
    }

    # Dynamic regex parts
    # Suffix style: k, m, к, м (followed by non-letters)
    _SUFFIX_REGEX = r'[kкmм](?![a-zA-Zа-яА-Я])'
    # Word style: match any key in MULTIPLIER_MAP that is > 1 char
    _WORD_MULTIPLIERS = sorted(
        [k for k in MULTIPLIER_MAP.keys() if len(k) > 1],
        key=len, reverse=True
    )
    _WORD_REGEX = r'(?:' + '|'.join(map(re.escape, _WORD_MULTIPLIERS)) + r')'

    # Combined Multiplier Regex: (Suffix | Word)
    MULTIPLIER_REGEX = f'(?:{_SUFFIX_REGEX}|{_WORD_REGEX})'

    # Regex to capture amount and currency/slang
    # Group 1: Amount
    # Group 2: Multiplier (optional)
    # Group 3: Currency
    PATTERN_START = re.compile(
        rf'(\d+(?:[.,]\d+)?)\s*({MULTIPLIER_REGEX})?\s*([$€£¥₽₸₿]|[a-zA-Zа-яА-Я]+)'
    )

    # Currency Number [multiplier]
    PATTERN_END = re.compile(
        rf'([$€£¥₽₸₿]|[a-zA-Zа-яА-Я]+)\s*(\d+(?:[.,]\d+)?)\s*({MULTIPLIER_REGEX})?'
    )

    SLANG_AMOUNT_CURRENCY = {
        "косарь": (1000.0, "RUB"),
        "косаря": (1000.0, "RUB"),
        "косарей": (1000.0, "RUB"),
        "лям": (1000000.0, "RUB"),
        "лямов": (1000000.0, "RUB"),
    }

    @staticmethod
    def _normalize_amount(amount_str: str) -> float:
        return float(amount_str.replace(',', '.'))

    @classmethod
    def _validate_currency_code(cls, currency_raw: str) -> Optional[str]:
        """
        Validates and returns a currency code from raw input.
        Returns the currency code if valid, None otherwise.
        """
        # Check if it's in the slang map first
        currency_code = cls.SLANG_MAP.get(currency_raw)
        if currency_code:
            return currency_code

        # Only accept 3-letter codes that are in the valid currencies whitelist
        if len(currency_raw) == 3 and currency_raw.isalpha():
            currency_code = currency_raw.upper()
            if currency_code in cls.VALID_CURRENCIES:
                return currency_code

        return None

    @classmethod
    def parse(cls, text: str, strict_mode: bool = False) -> List[Price]:
        results = []

        # Удаляем стоп-слова, чтобы они не мешали парсингу (например, "14 PRO")
        text_cleaned = text.lower()
        for word in cls.STOP_WORDS:
            # Заменяем слово на пробел, только если оно стоит отдельно (окружено границами \b)
            text_cleaned = re.sub(r'\b' + re.escape(word) + r'\b', ' ', text_cleaned)

        # Pattern 1: Number [multiplier] Currency
        for match in cls.PATTERN_START.finditer(text_cleaned):
            amount_str, multiplier_str, currency_raw = match.group(1), match.group(2), match.group(3)
            amount = cls._normalize_amount(amount_str)

            # Strict mode check
            if strict_mode:
                if currency_raw not in cls.SYMBOLS:
                    continue

            multiplier = 1.0
            if multiplier_str:
                multiplier = cls.MULTIPLIER_MAP.get(multiplier_str, 1.0)

            # Check if currency_raw is actually a special slang amount (like "косарь" used as currency placeholder)
            if currency_raw in cls.MULTIPLIER_MAP and currency_raw not in cls.SLANG_MAP:
                # Logic for "5 косарей" where "косарей" acts as multiplier AND implies RUB
                multiplier = cls.MULTIPLIER_MAP[currency_raw]
                if currency_raw in ["косарь", "косаря", "косарей", "лям", "лямов", "тонна"]:
                    currency_code = "RUB"
                else:
                    continue
            else:
                currency_code = cls._validate_currency_code(currency_raw)
                if not currency_code:
                    continue

            results.append(Price(amount=amount * multiplier, currency=currency_code))

        # Pattern 2: Currency Number [multiplier]
        for match in cls.PATTERN_END.finditer(text_cleaned):
            currency_raw, amount_str, multiplier_str = match.group(1), match.group(2), match.group(3)
            amount = cls._normalize_amount(amount_str)

            # Strict mode check
            if strict_mode:
                if currency_raw not in cls.SYMBOLS:
                    continue

            currency_code = cls._validate_currency_code(currency_raw)
            if not currency_code:
                continue

            multiplier = 1.0
            if multiplier_str:
                multiplier = cls.MULTIPLIER_MAP.get(multiplier_str, 1.0)

            results.append(Price(amount=amount * multiplier, currency=currency_code))

        # Standalone slang words (Ignore in strict mode? Usually yes, as they are words not signs)
        if not strict_mode:
            standalone_slang = re.compile(r'(?<!\d)\s*(?<!\d\s)(косарь|косаря|косарей|лям|лямов)\b')
            for match in standalone_slang.finditer(text_cleaned):
                word = match.group(1)
                if word in cls.SLANG_AMOUNT_CURRENCY:
                    val, curr = cls.SLANG_AMOUNT_CURRENCY[word]
                    results.append(Price(amount=val, currency=curr))

        return results


def recognize(text: str, strict_mode: bool = False) -> List[Price]:
    return CurrencyRecognizer.parse(text, strict_mode)
