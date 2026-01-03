"""
FavBox Backend Configuration
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite+aiosqlite:///./favbox.db"

    # JWT
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 10080  # 7 days

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True

    # CORS
    cors_origins: str = "chrome-extension://,moz-extension://,http://localhost:3000"

    # AI Services
    gemini_api_key: str = ""

    # Proxy (for accessing Gemini API from restricted networks)
    http_proxy: str = ""
    https_proxy: str = ""

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # 忽略.env中的额外字段（如vite相关配置）


@lru_cache
def get_settings() -> Settings:
    return Settings()
