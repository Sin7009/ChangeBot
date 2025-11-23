import hashlib
from aiogram import Router
from aiogram.types import InlineQuery, InlineQueryResultArticle, InputTextMessageContent

from src.services.recognizer import recognize
from src.services.rates import rates_service

inline_router = Router()


@inline_router.inline_query()
async def inline_query_handler(inline_query: InlineQuery):
    text = inline_query.query.strip()
    if not text:
        return

    prices = recognize(text)
    if not prices:
        return

    results = []
    # Default targets for inline mode
    targets = ["RUB", "USD", "EUR"]

    for price in prices:
        for target in targets:
            # Skip if converting to itself
            if price.currency == target:
                continue

            converted_amount = await rates_service.convert(price.amount, price.currency, target)
            if converted_amount == 0.0:
                continue

            formatted_val = f"{converted_amount:.2f}".rstrip("0").rstrip(".")
            result_text = f"{price.amount:g} {price.currency} ≈ {formatted_val} {target}"

            # Unique ID for the result
            result_id = hashlib.md5(result_text.encode()).hexdigest()

            article = InlineQueryResultArticle(
                id=result_id,
                title=result_text,
                description="Нажми, чтобы отправить в чат",
                input_message_content=InputTextMessageContent(
                    message_text=result_text
                )
            )
            results.append(article)

    # answer with cache_time=1 to ensure freshness if rates change fast,
    # though our rates cache is 1h. 300s is reasonable default for inline queries.
    # But prompt implies "results of conversion", maybe rates update.
    # Let's use 60s.
    await inline_query.answer(results, cache_time=60)
