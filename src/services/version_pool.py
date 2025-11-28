from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List

from src.lib.path_utils import ValidationError, ensure_within_base, validate_base_path
from src.services.version_discovery import _collect_logs


@dataclass
class VersionStatus:
    version_id: str
    path: Path
    summary_path: Path
    status: str  # available | missing_artifacts
    message: str = ""


def _summary_path(version_dir: Path) -> Path:
    return version_dir / "summary.csv"


def list_versions(base_path: Path) -> List[VersionStatus]:
    """
    Scan the data folder (version pool) and return version statuses.

    A version is considered:
    - available: PerformanceLog exists with logs AND summary.csv exists.
    - missing_artifacts: missing logs or summary.csv.
    """
    root = validate_base_path(base_path)
    versions: List[VersionStatus] = []

    for candidate in sorted(root.iterdir()):
        if not candidate.is_dir():
            continue
        ensure_within_base(candidate, root)
        logs = _collect_logs(candidate)
        summary = _summary_path(candidate)

        if not logs:
            status = "missing_artifacts"
            message = "PerformanceLog missing"
        elif not summary.exists():
            status = "missing_artifacts"
            message = "summary.csv missing"
        else:
            status = "available"
            message = ""

        versions.append(
            VersionStatus(
                version_id=candidate.name,
                path=candidate,
                summary_path=summary,
                status=status,
                message=message,
            )
        )

    if not versions:
        raise ValidationError(f"No versions found under {root}")

    return versions


def require_versions_available(versions: List[str], pool: List[VersionStatus]) -> None:
    """Ensure requested versions exist and are available."""
    available = {v.version_id for v in pool if v.status == "available"}
    missing = [v for v in versions if v not in available]
    if missing:
        raise ValidationError(f"Requested versions not available: {', '.join(missing)}")
