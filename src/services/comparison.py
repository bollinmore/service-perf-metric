from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Sequence

import pandas as pd

from src.config.paths import latest_pointer, temp_root_for_data_folder
from src.lib.logging_config import get_comparison_logger
from src.lib.path_utils import ValidationError
from src.lib.run_ids import generate_run_id
from src.lib.version_sort import sort_versions
from src.services.temp_storage import init_run_dirs, promote_latest, prune_previous_runs
from src.services.validation import require_one_to_three
from src.services.version_pool import list_versions, require_versions_available

_SERVICE_CANONICAL = {
    "aichat": "AI CHAT",
    "aicoach": "AI Coach",
}


def _normalize_service_name(value: str) -> str:
    raw = str(value).strip()
    if not raw:
        return raw
    key = re.sub(r"\s+", "", raw).casefold()
    return _SERVICE_CANONICAL.get(key, raw)


def _load_version_series(version_dir: Path) -> pd.Series:
    summary = version_dir / "summary.csv"
    if not summary.exists():
        raise ValidationError(f"Summary missing for version '{version_dir.name}' at {summary}")
    df = pd.read_csv(summary)
    if "service" not in df.columns or df.empty:
        # Allow empty or placeholder summaries used in tests; return an empty series
        return pd.Series(dtype=float)
    df["service"] = df["service"].astype(str).map(_normalize_service_name)
    # pick the first numeric column after service
    value_cols = [c for c in df.columns if c != "service"]
    if not value_cols:
        return pd.Series(dtype=float, index=df["service"])
    series = pd.to_numeric(df[value_cols[0]], errors="coerce")
    return pd.Series(series.values, index=df["service"])


def _write_combined_outputs(run_paths: dict, versions: list[str], data_folder: Path) -> None:
    summary_path = run_paths["summary"]
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    ordered_versions = sort_versions(versions)
    per_version_frames: list[pd.DataFrame] = []
    service_order: list[str] = []
    seen_services: set[str] = set()

    for ver in ordered_versions:
        version_dir = data_folder / ver
        summary = version_dir / "summary.csv"
        if not summary.exists():
            raise ValidationError(f"Summary missing for version '{version_dir.name}' at {summary}")

        df = pd.read_csv(summary)
        if "service" not in df.columns or df.empty:
            per_version_frames.append(pd.DataFrame(columns=["service", "__idx", ver]))
            continue

        df["service"] = df["service"].astype(str).map(_normalize_service_name)
        value_cols = [c for c in df.columns if c != "service"]
        if not value_cols:
            per_version_frames.append(pd.DataFrame(columns=["service", "__idx", ver]))
            continue

        value_col = value_cols[0]
        slim = df[["service", value_col]].rename(columns={value_col: ver})
        slim["__idx"] = slim.groupby("service").cumcount()
        per_version_frames.append(slim)

        for svc in slim["service"]:
            if svc not in seen_services:
                seen_services.add(svc)
                service_order.append(svc)

    combined = None
    for frame in per_version_frames:
        if combined is None:
            combined = frame
        else:
            combined = combined.merge(frame, on=["service", "__idx"], how="outer")

    if combined is None:
        combined = pd.DataFrame(columns=["service", "__idx", *ordered_versions])

    if service_order:
        combined["service"] = pd.Categorical(combined["service"], categories=service_order, ordered=True)
        combined = combined.sort_values(["service", "__idx"])
        combined["service"] = combined["service"].astype(str)
    else:
        combined = combined.sort_values(["service", "__idx"])

    combined = combined.drop(columns="__idx")
    combined.to_csv(summary_path, index=False)

    # Build per-service stats required by box plots: version_min/median/avg/max per service
    stats_rows = []
    for service_name, group in combined.groupby("service"):
        stats_entry = {"service": service_name}
        for ver in ordered_versions:
            col = pd.to_numeric(group[ver], errors="coerce")
            stats_entry[f"{ver}_min"] = float(col.min(skipna=True)) if not col.empty else None
            stats_entry[f"{ver}_median"] = float(col.median(skipna=True)) if not col.empty else None
            stats_entry[f"{ver}_avg"] = float(col.mean(skipna=True)) if not col.empty else None
            stats_entry[f"{ver}_max"] = float(col.max(skipna=True)) if not col.empty else None
        stats_rows.append(stats_entry)

    stats_path = Path(run_paths["service_stats"])
    stats_path.parent.mkdir(parents=True, exist_ok=True)
    stats_df = pd.DataFrame(stats_rows)
    stats_df.to_csv(stats_path, index=False)

    # duplicate stats into summary_stats for compatibility
    summary_stats_path = Path(run_paths["summary_stats"])
    stats_df.to_csv(summary_stats_path, index=False)


def run_comparison(data_folder: Path, versions: Sequence[str]) -> dict:
    """
    Execute a comparison across up to three versions.

    Validates selection, ensures required artifacts exist, writes temporary outputs,
    and promotes the latest pointer.
    """
    logger = get_comparison_logger()
    selection = require_one_to_three(list(versions))
    pool = list_versions(data_folder)
    require_versions_available(selection, pool)

    run_id = generate_run_id()
    run_paths = init_run_dirs(data_folder, run_id)

    _write_combined_outputs(run_paths, selection, data_folder)

    manifest_path = Path(run_paths["run_dir"]) / "manifest.json"
    manifest_payload = {
        "run_id": run_id,
        "data_folder": str(data_folder),
        "selected_versions": selection,
        "outputs": {
            "summary": str(run_paths["summary"]),
            "summary_stats": str(run_paths["summary_stats"]),
            "service_stats": str(run_paths["service_stats"]),
        },
    }
    manifest_path.write_text(json.dumps(manifest_payload, ensure_ascii=False))

    latest = promote_latest(run_paths["temp_root"], run_paths["run_dir"])
    prune_previous_runs(run_paths["temp_root"], keep_run_id=run_id)

    logger.info(
        "comparison.run.completed",
        extra={
            "run_id": run_id,
            "data_folder": str(data_folder),
            "versions": selection,
            "run_dir": str(run_paths["run_dir"]),
            "latest_pointer": str(latest),
        },
    )

    manifest_payload.update(
        {
            "status": "completed",
            "temp_location": str(run_paths["run_dir"]),
            "latest_pointer": str(latest),
        }
    )
    return manifest_payload


def get_latest_comparison(data_folder: Path) -> dict:
    """Return metadata for the latest comparison, or raise ValidationError if absent."""
    temp_root = temp_root_for_data_folder(data_folder)
    latest = latest_pointer(temp_root)
    if not latest.exists():
        raise ValidationError("No comparison exists; select three versions to run comparison.")

    # Resolve symlink if present
    run_dir_path = latest.resolve()
    manifest = run_dir_path / "manifest.json"
    if not manifest.exists():
        raise ValidationError("Latest comparison manifest missing; rerun comparison.")

    payload = json.loads(manifest.read_text())
    payload["latest_pointer"] = str(latest)
    payload["temp_location"] = str(run_dir_path)
    return payload
