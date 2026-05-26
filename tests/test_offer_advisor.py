from src.services.offer_advisor import analyze_subscription_offer


def test_analyze_subscription_offer_recommends_buy_before_hike():
    text = (
        'Стоит или не стоит соглашаться на такое предложение\n\n'
        'Starting July 1, 2026, the price of a new Lifetime Plex Pass will increase '
        'to $749.99 USD. You have until July 1, 2026, to get it at the current price '
        'of $249.99 USD. Buy now.'
    )

    result = analyze_subscription_offer(text)

    assert result is not None
    assert 'стоит брать' in result.lower() or 'скорее стоит' in result.lower()
    assert '249.99 USD' in result
    assert '749.99 USD' in result
    assert '200.0%' in result


def test_analyze_subscription_offer_requires_decision_intent():
    text = 'Price changes from $249.99 to $749.99 starting next month.'

    result = analyze_subscription_offer(text)

    assert result is None


def test_analyze_subscription_offer_requires_two_prices_same_currency():
    text = 'Стоит ли это брать за $249.99?' 

    result = analyze_subscription_offer(text)

    assert result is None
