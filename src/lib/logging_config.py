from __future__ import annotations

import logging

from src.config import configure_logging


def get_comparison_logger(name: str = "spm.comparison", level: str | None = None) -> logging.Logger:
    """Return a logger configured for comparison operations."""
    return configure_logging(name=name, level=level)
