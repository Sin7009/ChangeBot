import time
from typing import List, Dict, Tuple, Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import ChatSettings

DEFAULT_CURRENCIES = ["USD", "EUR", "RUB"]

# Simple cache: chat_id -> (timestamp, target_currencies)
# OPTIMIZATION: Store as tuple to allow zero-copy returns
_settings_cache: Dict[int, Tuple[float, Tuple[str, ...]]] = {}
CACHE_TTL = 300  # 5 minutes

async def get_chat_settings(session: AsyncSession, chat_id: int) -> ChatSettings:
    """
    Retrieves chat settings for the given chat_id.
    If settings do not exist, creates them with defaults.
    """
    stmt = select(ChatSettings).where(ChatSettings.chat_id == chat_id)
    result = await session.execute(stmt)
    settings = result.scalar_one_or_none()

    if settings is None:
        settings = ChatSettings(
            chat_id=chat_id,
            target_currencies=list(DEFAULT_CURRENCIES), # Copy
            default_source="USD"
        )
        session.add(settings)
        await session.commit()
        await session.refresh(settings)

    return settings

async def get_target_currencies(session: AsyncSession, chat_id: int) -> Sequence[str]:
    """
    Retrieves the list of target currencies for a chat, using a read-through cache.
    This avoids database queries for every message in active chats.

    Returns a read-only sequence (tuple) to avoid list copy overhead.
    """
    now = time.time()
    if chat_id in _settings_cache:
        timestamp, data = _settings_cache[chat_id]
        if now - timestamp < CACHE_TTL:
            # OPTIMIZATION: Return tuple directly.
            # Since it's immutable, we don't need to copy it like list(data).
            # This saves an O(N) allocation on every message.
            return data

    # Cache miss
    settings = await get_chat_settings(session, chat_id)
    currencies = list(settings.target_currencies)

    # OPTIMIZATION: Convert to tuple for storage
    currencies_tuple = tuple(currencies)
    _settings_cache[chat_id] = (now, currencies_tuple)
    return currencies_tuple

async def toggle_currency(session: AsyncSession, chat_id: int, currency_code: str) -> List[str]:
    """
    Toggles a currency in the target_currencies list for the given chat_id.
    Returns the updated list of currencies.
    """
    settings = await get_chat_settings(session, chat_id)

    # Ensure it's a list (JSON type can sometimes be weird if DB is messed up, but should be fine)
    current_list = list(settings.target_currencies)

    if currency_code in current_list:
        current_list.remove(currency_code)
    else:
        current_list.append(currency_code)

    settings.target_currencies = current_list
    # For some JSON implementations in SQLAlchemy, mutation might not track automatically
    # unless we reassign or flag modified. Reassigning is safe.
    # Also need to add to session to be sure (it is attached though).

    await session.commit()
    await session.refresh(settings)

    # Update cache
    _settings_cache[chat_id] = (time.time(), tuple(settings.target_currencies))

    return settings.target_currencies
