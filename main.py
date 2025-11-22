import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from src.config import settings
from src.database.engine import init_db, close_db
from src.bot.handlers import main_router

async def main():
    # Configure logging
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    logger = logging.getLogger(__name__)

    logger.info("Starting bot...")

    # Initialize Database
    await init_db()
    logger.info("Database initialized.")

    # Initialize Bot and Dispatcher
    bot = Bot(token=settings.BOT_TOKEN.get_secret_value())
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(main_router)

    try:
        await dp.start_polling(bot)
    finally:
        logger.info("Shutting down...")
        await close_db()
        await bot.session.close()
        logger.info("Shutdown complete.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped!")
