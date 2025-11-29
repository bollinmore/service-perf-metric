from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List

from src.lib.path_utils import ValidationError, ensure_within_base, validate_base_path
from src.services.version_discovery import _collect_logs


@dataclass
class VersionStatus:
    version_id: str
    dataset: str
    version: str
    path: Path
    summary_path: Path
    status: str  # available | missing_artifacts
    message: str = ""


def _summary_path(version_dir: Path) -> Path:
    return version_dir / "summary.csv"


def list_versions(base_path: Path) -> List[VersionStatus]:
    """
    Scan datasets under the data folder and return version statuses.

    A version is considered:
    - available: PerformanceLog exists with logs AND summary.csv exists.
    - missing_artifacts: missing logs or summary.csv.
    """
    root = validate_base_path(base_path)
    base_dataset_name = root.name
    versions: List[VersionStatus] = []

    for dataset_dir in sorted(root.iterdir()):
        if not dataset_dir.is_dir():
            continue
        # Skip temp outputs
        if dataset_dir.name == "temp":
            continue
        ensure_within_base(dataset_dir, root)

        potential_version_logs = _collect_logs(dataset_dir)
        potential_summary = _summary_path(dataset_dir)

        def _append_version(version_path: Path, dataset: str, version: str, version_id: str) -> None:
            summary = _summary_path(version_path)
            if not summary.exists():
                status = "missing_artifacts"
                msg = "summary.csv missing"
            else:
                status = "available"
                msg = ""
            versions.append(
                VersionStatus(
                    version_id=version_id,
                    dataset=dataset,
                    version=version,
                    path=version_path,
                    summary_path=summary,
                    status=status,
                    message=msg,
                )
            )

        # Flat structure: versions directly under root
        if potential_version_logs or potential_summary.exists():
            version_name = dataset_dir.name
            _append_version(dataset_dir, base_dataset_name, version_name, version_name)
            continue

        # Nested structure: dataset/version
        for version_dir in sorted(dataset_dir.iterdir()):
            if not version_dir.is_dir():
                continue
            ensure_within_base(version_dir, root)
            _append_version(version_dir, dataset_dir.name, version_dir.name, f"{dataset_dir.name}/{version_dir.name}")

    if not versions:
        raise ValidationError(f"No versions found under {root}")

    return versions


def require_versions_available(versions: List[str], pool: List[VersionStatus]) -> None:
    """Ensure requested versions exist and are available."""
    available = {v.version_id for v in pool if v.status == "available"}
    missing = [v for v in versions if v not in available]
    if missing:
        raise ValidationError(f"Requested versions not available: {', '.join(missing)}")
