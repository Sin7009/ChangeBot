import math


def format_amount(amount: float) -> str:
    """
    Formats an amount for a reply: "9000", "2.85", "0.0000283".
    Fixed-point, not :g, which turns large amounts into "3.5e+08".
    """
    decimals = 2
    if 0 < abs(amount) < 1:
        # Keep 3 significant digits so small amounts (e.g. 228 RUB in BTC) don't round to "0"
        decimals = max(decimals, 2 - math.floor(math.log10(abs(amount))))

    return f"{amount:.{decimals}f}".rstrip("0").rstrip(".")
