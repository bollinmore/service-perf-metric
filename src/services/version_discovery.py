from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence

from src.lib.path_utils import ValidationError, validate_base_path, ensure_within_base


@dataclass
class DiscoveredVersion:
    name: str
    path: Path
    log_dir: Path
    log_files: List[Path]


def _collect_logs(version_dir: Path) -> List[Path]:
    log_dir = version_dir / "PerformanceLog"
    if not log_dir.is_dir():
        return []
    loading = sorted(log_dir.glob("*loading.log"))
    if loading:
        return [log for log in loading if log.is_file()]
    inquire = sorted(log_dir.glob("*inquire2.log"))
    if inquire:
        return [log for log in inquire if log.is_file()]
    # fallback to any .log if neither pattern exists
    logs = sorted(log_dir.glob("*.log"))
    return [log for log in logs if log.is_file()]


def discover_versions(base_path: Path, allowed: Sequence[str] | None = None, strict_missing: bool = True) -> List[DiscoveredVersion]:
    """Discover versions under the base path with required PerformanceLog/*.log structure."""
    root = validate_base_path(base_path)
    allowed_set = {name for name in allowed} if allowed else None
    discovered: List[DiscoveredVersion] = []
    missing_logs: List[str] = []

    for candidate in sorted(root.iterdir()):
        if not candidate.is_dir():
            continue
        if allowed_set is not None and candidate.name not in allowed_set:
            continue
        log_files = _collect_logs(candidate)
        if not log_files:
            if allowed_set:
                missing_logs.append(candidate.name)
            continue
        ensure_within_base(candidate, root)
        discovered.append(
            DiscoveredVersion(
                name=candidate.name,
                path=candidate,
                log_dir=candidate / "PerformanceLog",
                log_files=log_files,
            )
        )

    if allowed_set:
        missing = sorted(allowed_set - {v.name for v in discovered})
        missing.extend(sorted(missing_logs))
        if missing and strict_missing:
            raise ValidationError(f"Requested versions not found or missing PerformanceLog/*.log: {', '.join(sorted(set(missing)))}")

    if strict_missing and not discovered:
        raise ValidationError(f"No valid versions found under {root}. Ensure each has PerformanceLog/*.log.")

    return discovered
