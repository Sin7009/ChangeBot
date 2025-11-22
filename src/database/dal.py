from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import ChatSettings

DEFAULT_CURRENCIES = ["USD", "EUR", "RUB"]

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

    return settings.target_currencies
