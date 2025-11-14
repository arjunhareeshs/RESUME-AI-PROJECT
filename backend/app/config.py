from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    DEEPSEEK_API_KEY: Optional[str] = None  # Optional, only needed for image OCR extraction
    GITHUB_TOKEN: Optional[str] = None
    HF_TOKEN: Optional[str] = None

    # Pydantic v2 settings configuration
    model_config = SettingsConfigDict(env_file=["../.env", ".env"], env_file_encoding="utf-8")

settings = Settings()