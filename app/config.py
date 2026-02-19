from typing import Optional

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str = "Universal Data Connector"
    MAX_RESULTS: int = 10
    DEFAULT_PAGE_SIZE: int = 10
    MAX_PAGE_SIZE: int = 50
    VOICE_SUMMARY_THRESHOLD: int = 10

    ENABLE_REDIS_CACHE: bool = True
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_TTL_SECONDS: int = 60

    RATE_LIMIT_PER_SOURCE: int = 60
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    ENABLE_STREAMING: bool = True
    STREAM_MIN_TOTAL_RESULTS: int = 25
    STREAM_CHUNK_SIZE: int = 10

    AUTH_ENABLED: bool = False
    ADMIN_API_KEY: Optional[SecretStr] = SecretStr("dev-admin-key")
    API_KEYS_STORE_FILE: str = "data/api_keys.json"
    APP_DB_PATH: str = "data/app.db"
    DEFAULT_CLIENT_API_KEYS: str = ""

    WEBHOOK_SHARED_SECRET: Optional[SecretStr] = None
    WEBHOOK_MAX_EVENTS: int = 200

    OPENAI_API_KEY: Optional[SecretStr] = None
    ANTHROPIC_API_KEY: Optional[SecretStr] = None
    GEMINI_API_KEY: Optional[SecretStr] = None
    OPENAI_MODEL: str = "gpt-4.1-mini"
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-latest"
    GEMINI_MODEL: str = "gemini-2.0-flash"
    GEMINI_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    LLM_MAX_TOKENS: int = 800

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()