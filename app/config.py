
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "Universal Data Connector"
    MAX_RESULTS: int = 10

    class Config:
        env_file = ".env"

settings = Settings()
