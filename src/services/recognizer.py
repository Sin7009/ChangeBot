import re
from dataclasses import dataclass
from typing import List, Dict

@dataclass
class Price:
    amount: float
    currency: str

class CurrencyRecognizer:
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
        "тенге": "KZT", "тг": "KZT",
        
        # CNY
        "юань": "CNY", "юаней": "CNY", "юаня": "CNY", "cny": "CNY", "¥": "CNY",
        
        # Crypto
        "биток": "BTC", "битка": "BTC", "битков": "BTC", "btc": "BTC", "bitcoin": "BTC",
        "эфир": "ETH", "eth": "ETH", "ethereum": "ETH",
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
        "лямов": 1000000.0
    }

    STOP_WORDS = {
        "pro", "max", "plus", "ultra", "mini", "slim",
        "gb", "tb", "гб", "тб",
        "шт", "уп", "kg", "кг",
        "цена", "price", "сумма", "итого", "total"
    }

    # Regex to capture amount and currency/slang
    PATTERN_START = re.compile(r'(\d+(?:[.,]\d+)?)\s*([kкmм](?![a-zA-Zа-яА-Я]))?\s*([$€£¥₽]|[a-zA-Zа-яА-Я]+)')
    PATTERN_END = re.compile(r'([$€£¥₽]|[a-zA-Zа-яА-Я]+)\s*(\d+(?:[.,]\d+)?)\s*([kкmм](?![a-zA-Zа-яА-Я]))?')

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
    def parse(cls, text: str) -> List[Price]:
        results = []

        # Удаляем стоп-слова, чтобы они не мешали парсингу (например, "14 PRO")
        text_cleaned = text.lower()
        for word in cls.STOP_WORDS:
            # Заменяем слово на пробел, только если оно стоит отдельно (окружено границами \b)
            text_cleaned = re.sub(r'\b' + re.escape(word) + r'\b', ' ', text_cleaned)

        # Pattern 1: Number [multiplier] Currency
        for match in cls.PATTERN_START.finditer(text_cleaned):
            amount_str, multiplier_suffix, currency_raw = match.group(1), match.group(2), match.group(3)
            amount = cls._normalize_amount(amount_str)

            multiplier = 1.0
            if multiplier_suffix:
                multiplier = cls.MULTIPLIER_MAP.get(multiplier_suffix, 1.0)

            if currency_raw in cls.MULTIPLIER_MAP and currency_raw not in cls.SLANG_MAP:
                 multiplier = cls.MULTIPLIER_MAP[currency_raw]
                 if currency_raw in ["косарь", "косаря", "косарей", "лям", "лямов", "тонна"]:
                     currency_code = "RUB"
                 else:
                     continue 
            else:
                currency_code = cls.SLANG_MAP.get(currency_raw)
                if not currency_code:
                     if len(currency_raw) == 3 and currency_raw.isalpha():
                         currency_code = currency_raw.upper()
                     else:
                         continue 

            results.append(Price(amount=amount * multiplier, currency=currency_code))

        # Pattern 2: Currency Number [multiplier]
        for match in cls.PATTERN_END.finditer(text_cleaned):
            currency_raw, amount_str, multiplier_suffix = match.group(1), match.group(2), match.group(3)
            amount = cls._normalize_amount(amount_str)

            currency_code = cls.SLANG_MAP.get(currency_raw)
            if not currency_code:
                 if len(currency_raw) == 3 and currency_raw.isalpha():
                     currency_code = currency_raw.upper()
                 else:
                     continue

            multiplier = 1.0
            if multiplier_suffix:
                multiplier = cls.MULTIPLIER_MAP.get(multiplier_suffix, 1.0)

            results.append(Price(amount=amount * multiplier, currency=currency_code))

        # Standalone slang words
        standalone_slang = re.compile(r'(?<!\d)\s*(?<!\d\s)(косарь|косаря|косарей|лям|лямов)\b')
        for match in standalone_slang.finditer(text_cleaned):
            word = match.group(1)
            if word in cls.SLANG_AMOUNT_CURRENCY:
                val, curr = cls.SLANG_AMOUNT_CURRENCY[word]
                results.append(Price(amount=val, currency=curr))

        return results

def recognize(text: str) -> List[Price]:
    return CurrencyRecognizer.parse(text)
