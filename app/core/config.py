"""Application settings loaded from environment variables / .env file."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict

_cache: "Settings | None" = None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ── Service ───────────────────────────────────────────────────────────────
    VERSION: str = "1.0.0"
    LOG_LEVEL: str = "INFO"

    # ── Storage ───────────────────────────────────────────────────────────────
    FILE_EXPORT_DIR: str = "/output"
    FILE_EXPORT_BASE_URL: str = "http://localhost:9003/files"

    # ── Templates (optional) ─────────────────────────────────────────────────
    DOCS_TEMPLATE_PATH: str = ""

    # ── OpenWebUI integration (optional) ─────────────────────────────────────
    OWUI_URL: str = ""
    JWT_SECRET: str = ""

    # ── Cleanup ───────────────────────────────────────────────────────────────
    FILES_DELAY: int = 3600          # seconds; 0 = keep forever
    PERSISTENT_FILES: bool = False

    # ── HTTP client ───────────────────────────────────────────────────────────
    HTTP_TIMEOUT: float = 30.0


def get_settings() -> Settings:
    global _cache
    if _cache is None:
        _cache = Settings()
    return _cache


def override_settings(s: Settings) -> None:
    """For use in tests only."""
    global _cache
    _cache = s


def reset_settings() -> None:
    """For use in tests only."""
    global _cache
    _cache = None
