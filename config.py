import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

def _get(key: str, default: str | None = None, required: bool = False) -> str:
    val = os.environ.get(key, default)
    if required and not val:
        raise RuntimeError(f"Missing required env var: {key}")
    return val or ""

@dataclass(frozen=True)
class Settings:
    GEMINI_API_KEY: str
    GEMINI_MODEL: str
    GEMINI_FALLBACK_MODELS: list[str]
    TURSO_URL: str
    TURSO_TOKEN: str
    STORAGE_SECRET: str
    MAX_UPLOAD_MB: int
    MAX_FILES: int
    LOG_LEVEL: str

settings = Settings(
    GEMINI_API_KEY=_get("GEMINI_API_KEY", required=True),
    GEMINI_MODEL=_get("GEMINI_MODEL", "gemini-3.5-flash-lite"),
    GEMINI_FALLBACK_MODELS=[
        m.strip() for m in _get(
            "GEMINI_FALLBACK_MODELS",
            "gemini-2.0-flash,gemini-1.5-flash",
        ).split(",") if m.strip()
    ],
    TURSO_URL=_get("TURSO_URL", required=True),
    TURSO_TOKEN=_get("TURSO_TOKEN", required=True),
    STORAGE_SECRET=_get("STORAGE_SECRET", "dev-secret-change-me"),
    MAX_UPLOAD_MB=int(_get("MAX_UPLOAD_MB", "15")),
    MAX_FILES=int(_get("MAX_FILES", "10")),
    LOG_LEVEL=_get("LOG_LEVEL", "INFO"),
)
