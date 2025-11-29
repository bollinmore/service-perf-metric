from __future__ import annotations

import re
from typing import Iterable, List


def _natural_key(label: str) -> List[object]:
    """
    Generate a key that sorts version-like strings in natural order.

    Splits on digit runs so "2.0.10" sorts after "2.0.2".
    """
    cleaned = str(label)
    parts = re.split(r"(\d+)", cleaned)
    key: List[object] = []
    for part in parts:
        if part == "":
            continue
        if part.isdigit():
            key.append(int(part))
        else:
            key.append(part.casefold())
    return key


def sort_versions(labels: Iterable[str]) -> list[str]:
    """Return labels sorted so older/“smaller” versions appear first."""
    return sorted((str(label) for label in labels), key=_natural_key)
