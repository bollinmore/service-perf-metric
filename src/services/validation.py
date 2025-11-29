from __future__ import annotations

from typing import Iterable, List, Sequence

from src.lib.path_utils import ValidationError


def require_exact_three(versions: Sequence[str]) -> List[str]:
    """Validate selection contains exactly three distinct versions."""
    cleaned = [v for v in versions if v]
    if len(cleaned) != len(set(cleaned)):
        raise ValidationError("Versions must be distinct; duplicates detected.")
    if len(cleaned) != 3:
        raise ValidationError("Exactly three versions are required for comparison.")
    return cleaned


def require_one_to_three(versions: Sequence[str]) -> List[str]:
    """Validate selection contains between one and three distinct versions."""
    cleaned = [v for v in versions if v]
    if len(cleaned) != len(set(cleaned)):
        raise ValidationError("Versions must be distinct; duplicates detected.")
    if not cleaned:
        raise ValidationError("At least one version is required for comparison.")
    if len(cleaned) > 3:
        raise ValidationError("No more than three versions are allowed for comparison.")
    return cleaned


def require_present(requested: Iterable[str], available: Iterable[str]) -> None:
    """Validate requested versions are present in the available set."""
    available_set = set(available)
    missing = [v for v in requested if v not in available_set]
    if missing:
        raise ValidationError(f"Requested versions not found: {', '.join(sorted(missing))}")
