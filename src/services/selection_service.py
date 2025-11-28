from __future__ import annotations

from typing import Iterable, List, Sequence, Set

from src.lib.path_utils import ValidationError


MIN_SELECTION = 2
MAX_SELECTION = 4


def validate_selection(available_names: Iterable[str], requested: Sequence[str] | None) -> List[str]:
    """Validate requested versions against available options, enforcing limits."""
    available_set: Set[str] = set(available_names)
    selected: List[str]
    if requested:
        unknown = [name for name in requested if name not in available_set]
        if unknown:
            raise ValidationError(f"Unknown versions requested: {', '.join(unknown)}")
        selected = []
        seen = set()
        for name in requested:
            if name not in seen:
                selected.append(name)
                seen.add(name)
    else:
        selected = sorted(available_set)

    if len(selected) < MIN_SELECTION:
        raise ValidationError(f"At least {MIN_SELECTION} versions required (found {len(selected)}).")
    if len(selected) > MAX_SELECTION:
        raise ValidationError(f"No more than {MAX_SELECTION} versions allowed (requested {len(selected)}).")
    return selected
