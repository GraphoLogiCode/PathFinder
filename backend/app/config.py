"""
PathFinder — Application Configuration

Loads settings from .env via Pydantic BaseSettings.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration loaded from environment variables / .env file."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    supabase_url: str = ""
    supabase_key: str = ""
    model_path: str = "../ai/weights/best.pt"
    valhalla_url: str = "http://192.168.137.117:8002"
    max_upload_size_mb: int = 20


settings = Settings()
