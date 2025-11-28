from __future__ import annotations

import os
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple, Optional

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
ALLOWED_MODES = {"development", "production"}
DEFAULT_DATA_FOLDER = PROJECT_ROOT / "data"
DEFAULT_LOG_LEVEL = "INFO"


@dataclass
class ModeResolution:
    mode: str
    source: str
    warnings: List[str]
    docker_forced: bool


def load_env(dotenv_path: Path | None = None) -> Path:
    """Load environment variables from a .env file if present."""
    path = dotenv_path or PROJECT_ROOT / ".env"
    load_dotenv(dotenv_path=path, override=False)
    return path


def _is_docker_forced() -> bool:
    docker_hint = os.environ.get("SPM_FORCE_PRODUCTION", "").lower()
    if docker_hint in {"1", "true", "yes"}:
        return True
    if Path("/.dockerenv").exists():
        return True
    return False


def resolve_mode(env: os._Environ | None = None) -> ModeResolution:
    """Resolve the desired mode with safe defaults and warnings."""
    environ = env or os.environ
    docker_forced = _is_docker_forced()
    if docker_forced:
        return ModeResolution("production", "docker-forced", [], True)

    raw_mode = environ.get("SPM_MODE", "").strip().lower()
    warnings: List[str] = []
    if raw_mode in ALLOWED_MODES:
        return ModeResolution(raw_mode, "env", warnings, False)

    warnings.append(
        "SPM_MODE missing or invalid; defaulting to development for local serve."
    )
    return ModeResolution("development", "env", warnings, False)


def apply_mode_env(resolution: ModeResolution) -> None:
    """Persist the resolved mode back to the environment for downstream use."""
    os.environ["SPM_MODE"] = resolution.mode
    os.environ["SPM_MODE_SOURCE"] = resolution.source
    if resolution.docker_forced:
        os.environ["SPM_MODE_FORCED"] = "1"
    else:
        os.environ.pop("SPM_MODE_FORCED", None)


def resolve_data_folder(explicit: Path | None) -> Path:
    """Resolve the data folder from explicit CLI input or environment, with a safe default."""
    if explicit:
        return explicit
    env_path = os.environ.get("SPM_DATA_FOLDER")
    if env_path:
        return Path(env_path)
    return DEFAULT_DATA_FOLDER


def configure_logging(name: str = "spm", level: Optional[str] = None) -> logging.Logger:
    """Configure a root logger with sane defaults for CLI and services."""
    log_level = getattr(logging, (level or os.environ.get("SPM_LOG_LEVEL", DEFAULT_LOG_LEVEL)).upper(), logging.INFO)
    root_logger = logging.getLogger(name)
    if not root_logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s - %(message)s")
        )
        root_logger.addHandler(handler)
    root_logger.setLevel(log_level)
    root_logger.propagate = False
    return root_logger
