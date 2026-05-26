from collections import defaultdict
from typing import Optional

from src.services.recognizer import recognize


def analyze_subscription_offer(text: str) -> Optional[str]:
    """Return buy/skip recommendation for subscription price-change announcements.

    Triggered only when text contains decision intent (e.g. "стоит ли", "соглашаться", "buy now")
    and at least two distinct prices in the same currency.
    """
    text_l = text.lower()

    decision_hints = (
        "стоит ли",
        "не стоит",
        "соглаш",
        "брать",
        "покупать",
        "buy now",
        "should i",
        "worth",
    )
    if not any(h in text_l for h in decision_hints):
        return None

    prices = recognize(text)
    if not prices:
        return None

    by_currency = defaultdict(set)
    for p in prices:
        by_currency[p.currency].add(round(float(p.amount), 4))

    candidate_currency = None
    candidate_values = None
    for curr, values in by_currency.items():
        if len(values) >= 2:
            sorted_vals = sorted(values)
            if candidate_values is None or (sorted_vals[-1] - sorted_vals[0]) > (candidate_values[-1] - candidate_values[0]):
                candidate_currency = curr
                candidate_values = sorted_vals

    if not candidate_values or not candidate_currency:
        return None

    old_price = candidate_values[0]
    new_price = candidate_values[-1]
    if old_price <= 0:
        return None

    increase_pct = (new_price / old_price - 1.0) * 100.0

    if increase_pct >= 20:
        verdict = "Да, скорее стоит брать до повышения."
    else:
        verdict = "Сомнительно: повышение небольшое, можно не спешить."

    return (
        f"💡 {verdict}\n"
        f"Текущая цена: {old_price:g} {candidate_currency}\n"
        f"Новая цена: {new_price:g} {candidate_currency}\n"
        f"Рост: {increase_pct:.1f}%"
    )
