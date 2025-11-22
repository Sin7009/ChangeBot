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
        "бакс": "USD", "баксов": "USD", "баксы": "USD", "dollar": "USD", "$": "USD",
        "евро": "EUR", "euro": "EUR", "€": "EUR",
        "руб": "RUB", "рубль": "RUB", "рублей": "RUB", "р": "RUB", "ruble": "RUB", "₽": "RUB",
        "фунт": "GBP", "pound": "GBP", "£": "GBP",
        "тенге": "KZT",
        "юань": "CNY", "cny": "CNY", "¥": "CNY"
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

    # Regex to capture amount and currency/slang
    # Case 1: "100 usd", "100$", "5k eur"
    # Group 1: Amount number
    # Group 2: Multiplier (k, m) - optional
    # Group 3: Separator (space, none)
    # Group 4: Currency/Slang
    # Fixed: Ensure multiplier isn't just the start of the next word (e.g. "5 косарей" -> 'к' shouldn't be captured as multiplier)
    PATTERN_START = re.compile(r'(\d+(?:[.,]\d+)?)\s*([kкmм](?![a-zA-Zа-яА-Я]))?\s*([$€£¥₽]|[a-zA-Zа-яА-Я]+)')

    # Case 2: "usd 100", "$100" (Currency first)
    # Group 1: Currency/Slang
    # Group 2: Separator
    # Group 3: Amount number
    # Group 4: Multiplier
    PATTERN_END = re.compile(r'([$€£¥₽]|[a-zA-Zа-яА-Я]+)\s*(\d+(?:[.,]\d+)?)\s*([kкmм](?![a-zA-Zа-яА-Я]))?')

    # Special slang with implied amount: "косарь", "лям" (without number before it usually means 1)
    # But usually people say "2 косаря". Let's handle "2 косаря" -> 2000 RUB.
    # If explicit currency is missing, we need to infer it. "косарь" usually implies RUB in RU context.
    # But the prompt says: "косарь" -> 1000 RUB.

    # Let's verify prompt req: "косарь" -> 1000 RUB.
    # This implies the word "косарь" acts as amount=1000 AND currency=RUB.

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
        text = text.lower()

        # 1. Search for explicit "Amount Currency" patterns
        # We need to iterate over matches.

        # Check standard patterns first
        # We might have overlapping matches, so we need to be careful.
        # Simple approach: find all matches for both patterns and merge?
        # Or consume the string?
        # Let's try finding all reasonable tokens.

        # Let's try a combined regex approach or iterative search.

        # Pattern 1: Number [multiplier] Currency
        # e.g. 100 usd, 5k eur, 100.50 rub
        for match in cls.PATTERN_START.finditer(text):
            amount_str, multiplier_suffix, currency_raw = match.group(1), match.group(2), match.group(3)

            # Filter: currency_raw must be in SLANG_MAP or be a valid ISO code (3 letters)
            # or it might be a special word like "косарь" acting as currency but handled separately?
            # Actually, if "косарь" is in MULTIPLIER_MAP, it handles "2 косаря".
            # Does "2 косаря" imply RUB? Yes.

            amount = cls._normalize_amount(amount_str)

            multiplier = 1.0
            if multiplier_suffix:
                multiplier = cls.MULTIPLIER_MAP.get(multiplier_suffix, 1.0)

            # Check if currency_raw is a multiplier word (e.g. "2 косаря")
            if currency_raw in cls.MULTIPLIER_MAP and currency_raw not in cls.SLANG_MAP:
                 multiplier = cls.MULTIPLIER_MAP[currency_raw]
                 # If using specific RU multipliers, default to RUB
                 if currency_raw in ["косарь", "косаря", "косарей", "лям", "лямов", "тонна"]:
                     currency_code = "RUB"
                 else:
                     continue # Valid number, valid multiplier, but no currency? ignore for now or default?
            else:
                # Normal currency lookup
                # Remove trailing s for simple plurals if not found?
                # The SLANG_MAP handles some, but maybe not all.

                clean_curr = currency_raw
                if clean_curr not in cls.SLANG_MAP:
                     # try stripping 's' or 'es'?
                     pass

                currency_code = cls.SLANG_MAP.get(clean_curr)
                if not currency_code:
                     # Check if it looks like an ISO code
                     if len(clean_curr) == 3 and clean_curr.isalpha():
                         currency_code = clean_curr.upper()
                     else:
                         continue # Not a recognized currency

            results.append(Price(amount=amount * multiplier, currency=currency_code))

        # Pattern 2: Currency Number [multiplier]
        # e.g. $100, eur 500
        # avoiding overlaps is tricky.
        # But let's assume users usually type one way or another.
        # For this task, simplicity preferred unless overlapping happens.

        # If we use finditer, we get spans. We can check overlaps.
        # But let's first see what the "Currency Number" regex catches.

        # Actually, "цена 2000р" -> pattern 1 catches "2000" "р".
        # "100 баксов" -> pattern 1 catches "100" "баксов".
        # "5k eur" -> pattern 1 catches "5" "k" "eur".

        # Pattern 2 is needed for "$100".
        for match in cls.PATTERN_END.finditer(text):
            currency_raw, amount_str, multiplier_suffix = match.group(1), match.group(2), match.group(3)

            # If this span overlaps with previous results, skip?
            # (We'd need to track spans).

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

            # Basic overlap check: if we already have this amount/currency in results?
            # Or use spans. Let's just append for now, simpler.
            results.append(Price(amount=amount * multiplier, currency=currency_code))

        # 3. Special single words: "косарь" (standalone) -> 1000 RUB
        # "лям" -> 1000000 RUB
        words = text.split()
        for word in words:
            if word in cls.SLANG_AMOUNT_CURRENCY:
                 val, curr = cls.SLANG_AMOUNT_CURRENCY[word]
                 # We should only add this if it wasn't part of a "2 косаря" match.
                 # "2 косаря" -> "2" matched number, "косаря" matched currency/multiplier.
                 # If "косарь" is standalone, it won't be adjacent to a number.
                 # This is getting complex.

                 # Simplification: The prompt examples are "100 баксов", "5k eur", "цена 2000р".
                 # "косарь" -> 1000 RUB is listed as requirement.

                 # Let's refine Pattern 1 to handle "2 косаря".
                 # If `PATTERN_START` matched "2 косаря", we successfully parsed 2000 RUB.
                 # If `words` loop sees "косаря", we avoid adding 1000 RUB again.
                 pass

        # To properly handle overlaps and isolated words, it's better to tokenize or remove matched parts.
        # Or, simplistic approach: "косарь" regex checks for NO digit before it.

        standalone_slang = re.compile(r'(?<!\d)\s*(?<!\d\s)(косарь|косаря|косарей|лям|лямов)\b')
        for match in standalone_slang.finditer(text):
            word = match.group(1)
            if word in cls.SLANG_AMOUNT_CURRENCY:
                val, curr = cls.SLANG_AMOUNT_CURRENCY[word]
                results.append(Price(amount=val, currency=curr))

        return results

def recognize(text: str) -> List[Price]:
    return CurrencyRecognizer.parse(text)
