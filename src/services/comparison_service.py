from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Sequence, Set

from src.services.selection_service import validate_selection
from src.services.version_discovery import DiscoveredVersion, discover_versions


@dataclass
class ComparisonPlan:
    base_path: Path
    selected_versions: List[str]
    result_root: Path
    discovered: List[DiscoveredVersion]
    conflicts: List[str]


def plan_comparison(base_path: Path, selected: Sequence[str] | None, result_root: Path) -> ComparisonPlan:
    """Build a comparison plan by validating selection and discovered versions."""
    discovered = discover_versions(base_path, allowed=selected if selected else None)
    available_names = [v.name for v in discovered]
    validated = validate_selection(available_names, list(selected) if selected else None)
    conflicts = detect_conflicts(discovered)
    return ComparisonPlan(
        base_path=base_path,
        selected_versions=validated,
        result_root=result_root,
        discovered=discovered,
        conflicts=conflicts,
    )


def detect_conflicts(discovered: List[DiscoveredVersion]) -> List[str]:
    """Detect basic conflicts (e.g., mismatched log filenames across versions)."""
    if not discovered:
        return []
    name_sets: List[Set[str]] = []
    for item in discovered:
        stems = {_normalize_log_name(path.name) for path in item.log_files}
        name_sets.append(stems)
    baseline = name_sets[0]
    conflicts: List[str] = []
    for idx, stems in enumerate(name_sets[1:], start=1):
        if stems != baseline:
            conflicts.append(
                f"Metric/log filenames differ between versions '{discovered[0].name}' and '{discovered[idx].name}'"
            )
    return conflicts


def _normalize_log_name(filename: str) -> str:
    """Normalize log names to align legacy and new formats (date prefix)."""
    return filename.split("_", 1)[0]


def refresh_results(plan: ComparisonPlan, force_refresh: bool) -> None:
    """Optionally clear previous results to ensure a clean comparison run."""
    if not force_refresh:
        return
    if plan.result_root.exists():
        import shutil

        shutil.rmtree(plan.result_root)
