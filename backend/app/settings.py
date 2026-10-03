"""Paths and environment settings, read when asked so tests can change them."""
from __future__ import annotations

import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
DEFAULT_PERIOD = "2025-09"


def load_env_file() -> None:
    """Read backend/.env into the environment without overriding what is already set."""
    env_file = BACKEND_DIR / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def db_path() -> Path:
    return Path(os.environ.get("LEDGERLENS_DB", BACKEND_DIR / "data" / "ledgerlens.db"))


def dataset_path() -> Path | None:
    value = os.environ.get("LEDGERLENS_DATASET")
    return Path(value) if value else None


def derived_dir() -> Path | None:
    value = os.environ.get("LEDGERLENS_DERIVED")
    return Path(value) if value else None


def cache_dir() -> Path:
    return Path(os.environ.get("LEDGERLENS_CACHE", BACKEND_DIR / "cache"))


def cors_origins() -> list[str]:
    return [o.strip() for o in os.environ.get("CORS_ORIGIN", "http://localhost:3000,http://127.0.0.1:3000").split(",")]


def llm_mode() -> str:
    """live, cache_only or template_only. Without a key, live falls back to cache_only."""
    mode = os.environ.get("LLM_MODE", "cache_only")
    return "cache_only" if mode == "live" and not os.environ.get("GROQ_API_KEY") else mode


def llm_model() -> str:
    return os.environ.get("LLM_MODEL", "openai/gpt-oss-120b")


def stage_delay() -> float:
    """Seconds each Run stage stays on screen when results come from the cache."""
    return float(os.environ.get("LEDGERLENS_STAGE_DELAY", "0.6"))
