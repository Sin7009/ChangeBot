from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr

class Settings(BaseSettings):
    BOT_TOKEN: SecretStr
    OER_API_KEY: SecretStr

    # Optional: database path for sqlite
    DB_PATH: str = "bot_database.sqlite3"
    # Last fetched rates, so the bot does not start without rates after a restart
    RATES_CACHE_PATH: str = "rates_cache.json"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()
