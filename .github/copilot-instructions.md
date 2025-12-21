# GitHub Copilot Instructions for ChangeBot

## Project Overview

ChangeBot is a Telegram bot written in Python that automatically detects monetary amounts in chat messages and converts them to other currencies. The bot supports:

- Automatic currency conversion in group chats
- OCR (Optical Character Recognition) for images of price tags and receipts
- Historical exchange rate charts generation
- Cryptocurrency support (BTC, ETH, TON, USDT) alongside fiat currencies
- Inline mode for quick conversions in any chat

## Technology Stack

- **Python**: 3.12+
- **Bot Framework**: aiogram 3.x (modern async framework for Telegram Bot API)
- **Database**: SQLite with aiosqlite driver
- **ORM**: SQLAlchemy (async version)
- **Migrations**: Alembic
- **Exchange Rates**: Yahoo Finance (via yfinance library)
- **OCR**: Tesseract (pytesseract)
- **Charts**: Matplotlib
- **Configuration**: Pydantic Settings
- **Containerization**: Docker & Docker Compose with uv package manager

## Project Structure

```
/home/runner/work/ChangeBot/ChangeBot/
├── src/
│   ├── bot/                  # Bot handlers, keyboards, middleware
│   │   ├── handlers.py       # Main message and command handlers
│   │   ├── inline.py         # Inline query handlers
│   │   ├── keyboards.py      # Telegram keyboards and buttons
│   │   └── middlewares.py    # Middleware components
│   ├── services/             # Business logic
│   │   ├── recognizer.py     # Currency amount recognition from text
│   │   ├── rates.py          # Currency conversion service
│   │   ├── ocr.py            # Image text extraction
│   │   └── charts.py         # Chart generation
│   ├── database/             # Database layer
│   │   ├── models.py         # SQLAlchemy models
│   │   ├── dal.py            # Data Access Layer
│   │   └── engine.py         # Database connection
│   └── config.py             # Application settings (Pydantic)
├── migrations/               # Alembic database migrations
├── tests/                    # Test suite
├── main.py                   # Application entry point
├── Dockerfile                # Docker image build instructions
├── docker-compose.yml        # Container orchestration
└── pyproject.toml            # Project dependencies and metadata
```

## Coding Conventions and Best Practices

### General Python Style

1. **Async/Await**: Use async/await patterns consistently throughout the codebase. All database operations, bot handlers, and API calls should be async.

2. **Type Hints**: Always use type hints for function parameters and return values. Import from `typing` module as needed.

   ```python
   from typing import List, Optional
   
   async def convert_prices(prices: List[Price], session: AsyncSession, chat_id: int) -> Optional[str]:
       ...
   ```

3. **Dataclasses**: Use `@dataclass` for simple data structures:

   ```python
   from dataclasses import dataclass
   
   @dataclass
   class Price:
       amount: float
       currency: str
   ```

4. **Logging**: Use Python's built-in logging module. Get logger with:

   ```python
   import logging
   logger = logging.getLogger(__name__)
   ```

### Aiogram Framework Patterns

1. **Routers**: Organize handlers in routers:

   ```python
   from aiogram import Router
   
   main_router = Router()
   ```

2. **Handlers**: Use decorators for message and callback handlers:

   ```python
   @main_router.message(Command("start"))
   async def cmd_start(message: Message):
       ...
   
   @main_router.callback_query(F.data.startswith("toggle_"))
   async def toggle_currency_callback(callback: CallbackQuery, session: AsyncSession):
       ...
   ```

3. **Middleware**: Use middleware for dependency injection (e.g., database sessions):

   ```python
   dp.update.middleware(DbSessionMiddleware())
   ```

### Database Patterns

1. **SQLAlchemy Models**: Use modern SQLAlchemy 2.0 syntax with `Mapped` and `mapped_column`:

   ```python
   from sqlalchemy.orm import Mapped, mapped_column
   
   class ChatSettings(Base):
       __tablename__ = "chat_settings"
       id: Mapped[int] = mapped_column(primary_key=True)
       chat_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
   ```

2. **Async Sessions**: Always use `AsyncSession` for database operations:

   ```python
   from sqlalchemy.ext.asyncio import AsyncSession
   
   async def get_chat_settings(session: AsyncSession, chat_id: int) -> ChatSettings:
       ...
   ```

3. **DAL Pattern**: Database queries should be in the Data Access Layer (`database/dal.py`), not in handlers.

### Service Layer

1. **Business Logic Separation**: Keep business logic in `services/` directory, separate from bot handlers.

2. **Currency Recognition**: The `recognizer.py` service handles text parsing and currency detection with slang support.

3. **Rate Conversion**: The `rates.py` service handles currency conversion using Yahoo Finance API.

4. **OCR Processing**: The `ocr.py` service handles image processing with Tesseract OCR.

### Testing

1. **Test Framework**: Use `unittest` for tests (existing pattern in the project).

2. **Test Naming**: Test methods should start with `test_` and clearly describe what they test:

   ```python
   def test_basic_usd(self):
       res = recognize("100 баксов")
       self.assertEqual(len(res), 1)
       self.assertEqual(res[0].amount, 100.0)
   ```

3. **Run Tests**: Use `uv run pytest` or `pytest` to run tests.

### Configuration

1. **Environment Variables**: Use Pydantic Settings for configuration. All sensitive data (tokens, API keys) should be in environment variables.

2. **Required Settings**:
   - `BOT_TOKEN`: Telegram bot token (SecretStr)
   - `OER_API_KEY`: API key (currently a placeholder, required for config validation)
   - `DB_PATH`: SQLite database path (default: "bot_database.sqlite3")

### Docker and Deployment

1. **Multi-stage Build**: The Dockerfile uses multi-stage builds with `uv` package manager for efficient dependency management.

2. **Tesseract Installation**: OCR requires Tesseract to be installed in the container with Russian and English language packs.

3. **Running**: Use `docker-compose up -d --build` to build and run the bot.

### Currency Support

1. **Valid Currencies**: The bot supports a whitelist of currencies defined in `CurrencyRecognizer.VALID_CURRENCIES`:
   - Fiat: USD, EUR, RUB, GBP, CNY, KZT, TRY, JPY
   - Crypto: BTC, ETH, TON, USDT

2. **Slang Recognition**: The bot recognizes Russian slang terms for currencies (e.g., "баксов" for USD, "косарь" for 1000 RUB).

3. **Strict Mode for Images**: For OCR, amounts must contain currency symbols ($, €, ₽, etc.) to be recognized.

### Commands

- `/start` - Welcome message and brief help
- `/settings` - Configure target currencies for the chat
- `/chart <CODE>` - Generate exchange rate chart for a currency (e.g., `/chart USD`)

## Development Workflow

1. **Local Development**:
   - Create virtual environment
   - Install dependencies: `pip install .` or `pip install -r requirements.txt`
   - Install Tesseract OCR system dependency
   - Create `.env` file with required variables
   - Run migrations: `alembic upgrade head`
   - Run bot: `python main.py`

2. **Adding Dependencies**: Add to `pyproject.toml` under `dependencies` array.

3. **Database Migrations**:
   - Create: `alembic revision --autogenerate -m "description"`
   - Apply: `alembic upgrade head`

4. **Testing Changes**: Run `uv run pytest` or `pytest tests/`

## Common Tasks

### Adding a New Handler

1. Add handler function in `src/bot/handlers.py` or appropriate file
2. Use decorator: `@main_router.message(...)` or `@main_router.callback_query(...)`
3. Accept `Message` or `CallbackQuery` as first parameter
4. If database access needed, add `session: AsyncSession` parameter (injected by middleware)

### Adding a New Currency

1. Add currency code to `VALID_CURRENCIES` in `src/services/recognizer.py`
2. Add slang terms to `SLANG_MAP` if needed
3. Ensure the currency is supported by Yahoo Finance for conversion

### Adding a New Service

1. Create new file in `src/services/`
2. Implement as a class or function module
3. Use async patterns for any I/O operations
4. Import and use in handlers

## Important Notes

- **Always use async/await** for I/O operations
- **Type hints are mandatory** for new code
- **Keep handlers thin** - move logic to services
- **Use DAL for database** - no raw queries in handlers
- **Test your changes** before committing
- **Follow existing patterns** in the codebase
- **Comments should be in Russian** where they exist (optional for new code)
- **Docstrings in English** are preferred for new functions

## When Suggesting Code

1. Follow the existing code style and patterns
2. Use async/await for all I/O operations
3. Add proper type hints
4. Consider error handling and edge cases
5. Keep the code simple and maintainable
6. Test compatibility with Python 3.12+
7. Ensure suggested changes work with aiogram 3.x API
