from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    app_name: str = "NADI-HD API"
    app_version: str = "0.1.0"
    cors_origins: tuple[str, ...] = ("http://localhost:5173", "http://127.0.0.1:4173")
    synthetic_only: bool = True
    session_memory_path: Path = Path("data/runtime/nadi-hd-session-memory.sqlite")


settings = Settings()
