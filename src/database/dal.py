from typing import List, Dict, Tuple, Sequence
import time
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import ChatSettings

DEFAULT_CURRENCIES = ["USD", "EUR", "RUB"]

# Cache: chat_id -> (timestamp, currencies)
_settings_cache: Dict[int, Tuple[float, Sequence[str]]] = {}
_CACHE_TTL = 300  # 5 minutes

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
    Retrieves the list of target currencies for a chat, using an in-memory cache.
    This avoids DB queries for every message in high-traffic chats.
    """
    now = time.time()
    if chat_id in _settings_cache:
        timestamp, currencies = _settings_cache[chat_id]
        if now - timestamp < _CACHE_TTL:
            return currencies # Zero-copy return (immutable tuple)

    # Cache miss or expired
    settings = await get_chat_settings(session, chat_id)
    # Convert to tuple for immutable storage
    currencies = tuple(settings.target_currencies)

    _settings_cache[chat_id] = (now, currencies)
    return currencies

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
