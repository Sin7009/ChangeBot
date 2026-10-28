import re
from dataclasses import dataclass
from typing import List, Dict, Set


@dataclass
class Price:
    amount: float
    currency: str

def trie_regex_from_words(words: List[str]) -> str:
    """
    Constructs an optimized Regex from a list of words using a Trie structure.
    This reduces backtracking and improves performance compared to a simple OR list.
    """
    trie = {}
    for word in words:
        node = trie
        for char in word:
            node = node.setdefault(char, {})
        node['__end__'] = True

    def _regex_from_trie(node):
        has_end = node.pop('__end__', False)

        # Sort keys to ensure deterministic output
        chars = sorted(node.keys())

        if not chars:
            return ""

        alts = []
        for char in chars:
            child_regex = _regex_from_trie(node[char])
            alts.append(re.escape(char) + child_regex)

        if len(alts) == 1:
            res = alts[0]
        else:
            res = "(?:" + "|".join(alts) + ")"

        if has_end:
             return "(?:" + res + ")?"
        return res

    return "(?:" + _regex_from_trie(trie) + ")"

class CurrencyRecognizer:
    TRANSFER_VERBS = {
        "переведу", "перевести", "перевод", "скину", "отправлю", "закину", "перекину"
    }
    TRANSFER_TARGET_HINTS = {
        "в баксах", "в долларах", "usd", "доллар", "долларах", "доллары", "баксы", "баксов"
    }
    TRANSFER_FINANCE_CONTEXT_HINTS = {
        "карта", "карте", "счет", "счёт", "банк", "денег", "деньги", "получу", "получить"
    }
    TON_CRYPTO_HINTS = {
        "toncoin", "крипт", "кошелек", "кошелёк", "wallet", "адрес", "транзак", "депозит", "вывод", "бирж", "usdt", "btc", "eth"
    }

    # Valid currency codes - whitelist to prevent false positives
    VALID_CURRENCIES = {
        # Fiat currencies
        "USD", "EUR", "RUB", "GBP", "CNY", "KZT", "TRY", "JPY", "MXN",
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
        "py6": "RUB", "pyб": "RUB", "pуб": "RUB", "pyb": "RUB",
        
        # GBP
        "фунт": "GBP", "pound": "GBP", "£": "GBP", "фунтов": "GBP", "фунта": "GBP",
        
        # KZT
        "тенге": "KZT", "тг": "KZT", "₸": "KZT",
        
        # CNY
        "юань": "CNY", "юаней": "CNY", "юаня": "CNY", "cny": "CNY", "¥": "CNY",

        # MXN: the most traded peso, so a bare "песо" means the Mexican one
        "песо": "MXN", "peso": "MXN", "pesos": "MXN",

        # Crypto
        "биток": "BTC", "битка": "BTC", "битков": "BTC", "btc": "BTC", "bitcoin": "BTC", "₿": "BTC",
        "эфир": "ETH", "эфира": "ETH", "эфиров": "ETH", "eth": "ETH", "ethereum": "ETH",
        "ton": "TON", "тон": "TON",
        "usdt": "USDT", "tether": "USDT"
    }

    # Longer digit lines on price tags are barcodes or article numbers, not prices
    MAX_PRICE_TAG_DIGITS = 7

    CANONICAL_SYMBOLS: Dict[str, str] = {
        "RUB": "₽",
        "USD": "$",
        "EUR": "€",
        "GBP": "£",
        "CNY": "¥",
        "KZT": "₸",
        "BTC": "₿"
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
        "тыс": 1000.0, "тысяча": 1000.0, "тысячу": 1000.0, "тысячи": 1000.0, "тысяч": 1000.0,
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
    _WORD_MULTIPLIERS = [k for k in MULTIPLIER_MAP.keys() if len(k) > 1]
    # OPTIMIZATION: Use Trie-based regex for O(M) matching performance instead of O(M*N) list search.
    _WORD_REGEX = trie_regex_from_words(_WORD_MULTIPLIERS)
    
    # Combined Multiplier Regex: (Suffix | Word)
    MULTIPLIER_REGEX = f'(?:{_SUFFIX_REGEX}|{_WORD_REGEX})'

    # OPTIMIZATION: Construct whitelist of currency tokens to avoid false positives.
    # Instead of matching [a-zA-Z]+ and checking dict in Python, we match only valid tokens in regex.
    # This prevents the loop from triggering on "100 apples".
    # Note: text is lowercased before matching, so these keys (lowercase) handle all cases.
    _CURRENCY_TOKENS = sorted(set(SLANG_MAP.keys()).union(IMPLIED_RUBLE_TOKENS))
    # Note: SYMBOLS are already in SLANG_MAP keys, so they are included here.

    # OPTIMIZATION: Use Trie-based regex for O(M) matching performance instead of O(M*N) list search.
    _CURRENCY_TOKEN_REGEX = trie_regex_from_words(_CURRENCY_TOKENS)

    # Regex to capture amount and currency/slang
    # Group 1: Amount (supports space-separated thousands: "1 000 000" or "1  000  000")
    # Group 2: Multiplier (optional)
    # Group 3: Currency
    # Pattern: either space-separated (\d{1,3}(?:\s+\d{3})+) or regular (\d+), with optional decimal
    _AMOUNT_REGEX = r'(?:\d{1,3}(?:[ \t]+\d{3})+|\d+)(?:[.,]\d+)?'
    PATTERN_START = re.compile(
        rf'({_AMOUNT_REGEX})[ \t]*({MULTIPLIER_REGEX})?[ \t]*({_CURRENCY_TOKEN_REGEX})'
    )
    
    # Currency Number [multiplier]
    PATTERN_END = re.compile(
        rf'({_CURRENCY_TOKEN_REGEX})[ \t]*({_AMOUNT_REGEX})[ \t]*({MULTIPLIER_REGEX})?'
    )

    SLANG_AMOUNT_CURRENCY = {
        "косарь": (1000.0, "RUB"),
        "косаря": (1000.0, "RUB"),
        "косарей": (1000.0, "RUB"),
        "лям": (1000000.0, "RUB"),
        "лямов": (1000000.0, "RUB"),
    }

    # OPTIMIZATION: Use Trie-based regex for standalone slang to improve matching performance
    _SLANG_TOKENS = list(SLANG_AMOUNT_CURRENCY.keys())
    _SLANG_REGEX = trie_regex_from_words(_SLANG_TOKENS)

    # Compiled pattern for standalone slang words
    # Matches words from SLANG_AMOUNT_CURRENCY if not preceded by a digit
    # Note: We wrap the trie regex in a capturing group to match group(1) behavior
    STANDALONE_SLANG_PATTERN = re.compile(
        rf'(?<!\d)[ \t]*(?<!\d[ \t])({_SLANG_REGEX})\b'
    )

    # OPTIMIZATION: Combined regex for single-pass scanning
    # Combines PATTERN_START, PATTERN_END, and STANDALONE_SLANG_PATTERN
    # Groups:
    # 1,2,3: Start Pattern (Amount, Multiplier, Currency)
    # 4,5,6: End Pattern (Currency, Amount, Multiplier)
    # 7: Standalone Slang
    COMBINED_PATTERN = re.compile(
        rf'(?:({_AMOUNT_REGEX})[ \t]*({MULTIPLIER_REGEX})?[ \t]*({_CURRENCY_TOKEN_REGEX}))|'
        rf'(?:({_CURRENCY_TOKEN_REGEX})[ \t]*({_AMOUNT_REGEX})[ \t]*({MULTIPLIER_REGEX})?)|'
        rf'(?:(?<!\d)[ \t]*(?<!\d[ \t])({_SLANG_REGEX})\b)'
    )

    # OPTIMIZATION: Precompiled pattern for fast digit checking.
    # Avoiding re.search(r'\d', text) in the loop improves performance by ~2-3x.
    HAS_DIGIT_PATTERN = re.compile(r'\d')

    # "900 тыс. руб." -> "900 тыс руб.": the abbreviation dot would split multiplier and currency
    ABBREVIATED_MULTIPLIER_PATTERN = re.compile(r'(\d[ \t]*(?:тыс|млн|млрд|трлн))\.')

    # "за миллион песо" -> "за 1 миллион песо": a multiplier word without a number means one.
    # Only singular forms: "миллиона", "тысяч" always follow a number ("два миллиона").
    BARE_MULTIPLIER_PATTERN = re.compile(
        rf'(?<![\w.,])(?:(?:один|одна|одну)[ \t]+)?(тысяча|тысячу|миллион|миллиард|триллион)'
        rf'(?=[ \t]+{_CURRENCY_TOKEN_REGEX}(?![a-zа-яё]))'
    )
    # Tens and hundreds that put "один миллион" inside a bigger number: "двадцать один миллион"
    COMPOUND_NUMBER_WORDS = {
        "двадцать", "тридцать", "сорок", "пятьдесят", "шестьдесят", "семьдесят", "восемьдесят",
        "девяносто", "сто", "двести", "триста", "четыреста", "пятьсот", "шестьсот", "семьсот",
        "восемьсот", "девятьсот"
    }

    # Ranges where the multiplier/currency is written once for both ends
    _RANGE_SEP_REGEX = r'(?:[ \t]*[-–—][ \t]*|[ \t]+до[ \t]+)'
    # "$2,5-3 млн", "$2,5 - $3 млн", "$100-200"
    RANGE_PREFIX_PATTERN = re.compile(
        rf'({_CURRENCY_TOKEN_REGEX})[ \t]*({_AMOUNT_REGEX}){_RANGE_SEP_REGEX}'
        rf'(?:({_CURRENCY_TOKEN_REGEX})[ \t]*)?({_AMOUNT_REGEX})(?:[ \t]*({MULTIPLIER_REGEX}))?'
    )
    # "2,5-3 млн долларов", "от 2 до 3 млн рублей". The multiplier is required:
    # without it "250-99 руб" is a price tag, not a range.
    RANGE_SUFFIX_PATTERN = re.compile(
        rf'(?<![\d.,])({_AMOUNT_REGEX}){_RANGE_SEP_REGEX}({_AMOUNT_REGEX})[ \t]*'
        rf'({MULTIPLIER_REGEX})[ \t]*({_CURRENCY_TOKEN_REGEX})'
    )

    @classmethod
    def _normalize_amount(cls, amount_str: str) -> float:
        """
        Normalize amount string to float, handling:
        - Spaces as thousands separators (e.g., "1 000 000")
        - Comma as decimal separator (European format, e.g., "1,5")
        - Comma as thousands separator (e.g., "1,000")
        
        Examples:
            "1 000 000" (space-separated) -> 1000000.0
            "1 000" (space-separated) -> 1000.0
            "1,000" (comma thousands) -> 1000.0
            "1.5" (decimal) -> 1.5
            "1,5" (European decimal) -> 1.5
        """
        # First, handle spaces - always treat as thousands separator
        if ' ' in amount_str:
            amount_str = amount_str.replace(' ', '')
        
        # OPTIMIZATION: Early return if no comma present
        if ',' not in amount_str:
            return float(amount_str)

        # If comma is followed by exactly 3 digits and then non-digit or end,
        # it's likely a thousands separator (e.g., "1,000" or "10,000").
        # OPTIMIZATION: using rpartition is faster than regex check.

        _, _, tail = amount_str.rpartition(',')
        
        # Case 1: Comma at the end with 3 digits (e.g., "1,000")
        if len(tail) == 3 and tail.isdigit():
            return float(amount_str.replace(',', ''))

        # Case 2: Comma followed by 3 digits then non-digits (e.g., "1,000.00")
        elif len(tail) > 3 and tail[:3].isdigit() and not tail[3].isdigit():
            return float(amount_str.replace(',', ''))

        else:
            # Treat comma as decimal separator
            return float(amount_str.replace(',', '.'))

    @classmethod
    def _expand_prefix_range(cls, match: re.Match) -> str:
        """Rewrites "$2,5-3 млн" as "$ 2,5 млн ; $ 3 млн"."""
        currency, start, end_currency, end, multiplier = match.groups()
        text = match.string

        # Guard against partial word matches, e.g. "мир 2-3" -> "р 2-3" (RUB)
        if currency.isalpha() and match.start() > 0 and text[match.start() - 1].isalpha():
            return match.group(0)

        if end_currency and end_currency != currency:
            return match.group(0)

        # Only an ascending range shares the multiplier: "с 900 до 1,2 млрд" is not 900 млрд
        if cls._normalize_amount(start) >= cls._normalize_amount(end):
            return match.group(0)

        suffix = f" {multiplier}" if multiplier else ""
        return f"{currency} {start}{suffix} ; {currency} {end}{suffix}"

    @classmethod
    def _expand_suffix_range(cls, match: re.Match) -> str:
        """Rewrites "2,5-3 млн долларов" as "2,5 млн долларов ; 3 млн долларов"."""
        start, end, multiplier, currency = match.groups()
        text = match.string

        # Guard against partial word matches, e.g. "2-3 млн раз" -> "р" (RUB)
        if currency.isalpha() and match.end() < len(text) and text[match.end()].isalpha():
            return match.group(0)

        if cls._normalize_amount(start) >= cls._normalize_amount(end):
            return match.group(0)

        return f"{start} {multiplier} {currency} ; {end} {multiplier} {currency}"

    @classmethod
    def _expand_bare_multiplier(cls, match: re.Match) -> str:
        """Rewrites "миллион" and "один миллион" as "1 миллион"."""
        words = match.string[:match.start()].split()

        # "1 миллион" already has its number, "двадцать один миллион" is not one million
        if words and (words[-1][-1].isdigit() or words[-1] in cls.COMPOUND_NUMBER_WORDS):
            return match.group(0)

        return f"1 {match.group(1)}"

    @staticmethod
    def _merge_stacked_amounts(numbers: List[str]) -> List[str]:
        """["299", "95", "500"] -> ["299.95", "500"]: a 2-digit line after an amount is its kopecks."""
        amounts = []
        i = 0
        while i < len(numbers):
            if i + 1 < len(numbers) and len(numbers[i + 1]) == 2:
                amounts.append(f"{numbers[i]}.{numbers[i + 1]}")
                i += 2
                continue

            # A lone short number is not a price: "2", "$" may be unrelated lines
            if len(numbers[i]) >= 3:
                amounts.append(numbers[i])
            i += 1

        return amounts

    @classmethod
    def _get_canonical_symbol(cls, token: str) -> str | None:
        """Gets the canonical symbol (e.g. '₽') for a recognized currency token."""
        t = token.lower().strip().rstrip('.')
        currency_code = cls.SLANG_MAP.get(t)
        if currency_code:
            return cls.CANONICAL_SYMBOLS.get(currency_code)
        if t in cls.SYMBOLS:
            return t
        return None

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

        # Split text into lines, strip and clean them
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        # Merge stacked vertical prices from price tags: OCR returns rubles, kopecks and
        # currency as separate lines, often for both the old and the new price
        # (e.g. "299", "95", "500", "руб.", "руб." -> "299.95 ₽", "500 ₽")
        i = 0
        merged_lines = []
        while i < len(lines):
            numbers_end = i
            while (numbers_end < len(lines) and lines[numbers_end].isdigit()
                   and len(lines[numbers_end]) <= cls.MAX_PRICE_TAG_DIGITS):
                numbers_end += 1

            currencies_end = numbers_end
            while currencies_end < len(lines) and cls._get_canonical_symbol(lines[currencies_end]):
                currencies_end += 1

            if numbers_end > i and currencies_end > numbers_end:
                amounts = cls._merge_stacked_amounts(lines[i:numbers_end])
                if amounts:
                    symbol = cls._get_canonical_symbol(lines[numbers_end])
                    merged_lines.extend(f"{amount} {symbol}" for amount in amounts)
                    i = currencies_end
                    continue

            merged_lines.append(lines[i])
            i += 1
                
        text_cleaned = "\n".join(merged_lines).lower()

        text_cleaned = cls.ABBREVIATED_MULTIPLIER_PATTERN.sub(r'\1', text_cleaned)
        text_cleaned = cls.BARE_MULTIPLIER_PATTERN.sub(cls._expand_bare_multiplier, text_cleaned)

        # Expand ranges so both ends get the shared multiplier and currency
        # ("$2,5-3 млн" -> 2.5M and 3M USD). Ranges are rewritten before any
        # other hyphen handling, so "10-15 тыс руб" stays a range.
        text_cleaned = cls.RANGE_PREFIX_PATTERN.sub(cls._expand_prefix_range, text_cleaned)
        text_cleaned = cls.RANGE_SUFFIX_PATTERN.sub(cls._expand_suffix_range, text_cleaned)

        # Preprocess price tag hyphen format (e.g. "400-00" -> "400.00 ₽")
        # This is a very common price format in Russian retail.
        text_cleaned = re.sub(r'(?<![\d-])\b(\d+)-(\d{2})\b(?![\d-])', r'\1.\2 ₽', text_cleaned)

        # OPTIMIZATION: "Fast Path" for text without digits.
        # The COMBINED_PATTERN requires at least one digit (for amount) in its first two major parts.
        # Only the third part (STANDALONE_SLANG_PATTERN) can match without digits.
        # By checking for digits first, we can skip the complex regex scan for most chat messages.
        # text_cleaned, not text: "миллион песо" got its digit only after preprocessing.
        has_digits = cls.HAS_DIGIT_PATTERN.search(text_cleaned) is not None

        if not has_digits:
            # Only check standalone slang (e.g. "косарь")
            for match in cls.STANDALONE_SLANG_PATTERN.finditer(text_cleaned):
                 # Group 1 of STANDALONE_SLANG_PATTERN corresponds to group 7 in COMBINED_PATTERN logic
                 # but here finditer returns matches for the smaller regex, so it's group 1.
                 word = match.group(1)
                 if word in cls.SLANG_AMOUNT_CURRENCY:
                     val, curr = cls.SLANG_AMOUNT_CURRENCY[word]
                     results.append(Price(amount=val, currency=curr))
            return results

        # Optimization: Single pass using combined regex
        for match in cls.COMBINED_PATTERN.finditer(text_cleaned):
            # Check which group matched
            # Groups 1-3: Start Pattern (Amount, Multiplier, Currency)
            if match.group(1):
                amount_str, multiplier_str, currency_raw = match.group(1), match.group(2), match.group(3)
                amount = cls._normalize_amount(amount_str)

                # Guard against malformed symbol cases like "100$abc"
                if currency_raw in cls.SYMBOLS and match.end() < len(text_cleaned) and text_cleaned[match.end()].isalpha():
                    continue

                # Guard against partial word matches, e.g. "2 раза" -> "2 р" (RUB)
                if currency_raw.isalpha() and match.end() < len(text_cleaned) and text_cleaned[match.end()].isalpha():
                    continue

                # Disambiguate TON crypto vs Russian weight "тон"
                if currency_raw in {"тон", "ton"} and not any(h in text_cleaned for h in cls.TON_CRYPTO_HINTS):
                    continue

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

                # Guard against malformed symbol cases like "abc$100"
                if currency_raw in cls.SYMBOLS and match.start(4) > 0 and text_cleaned[match.start(4) - 1].isalpha():
                    continue

                # Guard against partial word matches, e.g. "раз 2" -> "р 2" (RUB)
                if currency_raw.isalpha() and match.start(4) > 0 and text_cleaned[match.start(4) - 1].isalpha():
                    continue

                # Disambiguate TON crypto vs Russian weight "тон"
                if currency_raw in {"тон", "ton"} and not any(h in text_cleaned for h in cls.TON_CRYPTO_HINTS):
                    continue

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

        if not results and not strict_mode:
            inferred = cls._infer_transfer_amount_without_currency(text_cleaned)
            if inferred:
                results.append(inferred)

        return results

    @classmethod
    def _infer_transfer_amount_without_currency(cls, text_cleaned: str) -> Price | None:
        """Infer source currency as RUB for transfer-like questions with explicit USD target hint."""
        if not any(v in text_cleaned for v in cls.TRANSFER_VERBS):
            return None

        if not any(h in text_cleaned for h in cls.TRANSFER_TARGET_HINTS):
            return None

        if not any(h in text_cleaned for h in cls.TRANSFER_FINANCE_CONTEXT_HINTS):
            return None

        m = re.search(r"\b(\d{1,3}(?:\s\d{3})+|\d+)\b", text_cleaned)
        if not m:
            return None

        amount = cls._normalize_amount(m.group(1))
        if amount <= 0:
            return None

        return Price(amount=amount, currency="RUB")

def recognize(text: str, strict_mode: bool = False) -> List[Price]:
    return CurrencyRecognizer.parse(text, strict_mode)
