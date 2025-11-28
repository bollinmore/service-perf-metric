from __future__ import annotations

import logging
from typing import Any, Dict


def get_logger(name: str = "spm") -> logging.Logger:
    return logging.getLogger(name)


def log_selection(logger: logging.Logger, base_path: str, versions: list[str]) -> None:
    logger.info("comparison.selection", extra={"base_path": base_path, "versions": versions})


def log_upload_rejection(logger: logging.Logger, reason: str, details: Dict[str, Any] | None = None) -> None:
    payload = {"reason": reason}
    if details:
        payload.update(details)
    logger.warning("upload.rejected", extra=payload)
