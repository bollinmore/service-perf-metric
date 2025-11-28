from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, List, Sequence


class ValidationError(ValueError):
    """Raised when validation of input paths or selections fails."""


def validate_base_path(base_path: Path) -> Path:
    """Ensure the base path exists and is a directory."""
    resolved = base_path.expanduser().resolve()
    if not resolved.exists():
        raise ValidationError(f"Data folder not found: {resolved}")
    if not resolved.is_dir():
        raise ValidationError(f"Data folder is not a directory: {resolved}")
    return resolved


def parse_versions_arg(raw: str | None) -> List[str]:
    """Parse a comma-separated versions argument into a unique, ordered list."""
    if not raw:
        return []
    parts = [part.strip() for part in raw.split(",") if part.strip()]
    seen = set()
    unique: List[str] = []
    for part in parts:
        if part not in seen:
            unique.append(part)
            seen.add(part)
    return unique


def ensure_within_base(path: Path, base: Path) -> Path:
    """Ensure a path resides within the base directory."""
    try:
        path.relative_to(base)
    except ValueError as exc:
        raise ValidationError(f"Path {path} is outside of base {base}") from exc
    return path
