from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple
import zipfile

import pandas as pd
import plotly.graph_objects as go
from flask import (
    Flask,
    Response,
    abort,
    jsonify,
    redirect,
    render_template,
    render_template_string,
    request,
    send_file,
    url_for,
)

from werkzeug.utils import secure_filename

from spm import DEFAULT_DATA_DIR, generate_reports


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if DEFAULT_DATA_DIR.is_absolute():
    DATA_BASE_DIR = DEFAULT_DATA_DIR
else:
    DATA_BASE_DIR = (PROJECT_ROOT / DEFAULT_DATA_DIR).resolve()
RECYCLE_DIR = PROJECT_ROOT / "recycle"

app = Flask(
    __name__,
    template_folder=str(PROJECT_ROOT / "templates"),
    static_folder=str(PROJECT_ROOT / "static"),
)

EXCLUDED_SERVICES = {
    "EIP2",
    "EIP 2",
    "Microsoft 365",
    "MICROSOFT 365",
    "OUTLOOK",
    "Outlook",
}


def _resolve_result_dir() -> Path:
    env_value = os.environ.get("SPM_RESULT_ROOT")
    if env_value:
        return Path(env_value)
    return Path(__file__).resolve().parent.parent / "result"


def _resolve_result_base_dir() -> Path:
    env_value = os.environ.get("SPM_RESULT_BASE")
    if env_value:
        return Path(env_value)
    return Path(__file__).resolve().parent.parent / "result"


# Base directory that holds generated CSV outputs
RESULT_BASE_DIR = _resolve_result_base_dir()
RESULT_DIR = _resolve_result_dir()
DEFAULT_DATASET_NAME = os.environ.get("SPM_DEFAULT_DATASET")
SUMMARY_FILE = RESULT_DIR / "summary.csv"


def configure_result_dirs(result_dir: Path, base_dir: Path, dataset_name: str | None) -> None:
    """Update the module-level paths when the CLI provides overrides."""
    global RESULT_DIR, RESULT_BASE_DIR, SUMMARY_FILE, DEFAULT_DATASET_NAME
    RESULT_DIR = result_dir
    RESULT_BASE_DIR = base_dir
    SUMMARY_FILE = RESULT_DIR / "summary.csv"
    DEFAULT_DATASET_NAME = dataset_name


def _list_csv_files() -> List[Path]:
    if not RESULT_DIR.exists():
        return []
    return sorted(p for p in RESULT_DIR.rglob("*.csv") if p.is_file())


def _list_csv_files_under(root: Path) -> List[Path]:
    if not root.exists():
        return []
    return sorted(p for p in root.rglob("*.csv") if p.is_file())


def _available_datasets() -> List[str]:
    if not RESULT_BASE_DIR.exists():
        return []
    datasets: List[str] = []
    for entry in sorted(RESULT_BASE_DIR.iterdir()):
        if entry.is_dir() and (entry / "summary.csv").exists():
            datasets.append(entry.name)
    return datasets


def _result_dir_for_dataset(dataset: str | None) -> Path:
    if not dataset:
        return RESULT_DIR
    candidate = (RESULT_BASE_DIR / dataset).resolve()
    base_resolved = RESULT_BASE_DIR.resolve()
    if base_resolved != candidate and base_resolved not in candidate.parents:
        raise ValueError("Invalid dataset selection")
    if not candidate.exists():
        raise FileNotFoundError(f"Dataset '{dataset}' not found")
    if not candidate.is_dir():
        raise FileNotFoundError(f"Dataset '{dataset}' is not a directory")
    return candidate


def _safe_resolve(rel_path: str, base: Path | None = None) -> Path:
    base_dir = base or RESULT_DIR
    try:
        candidate = (base_dir / rel_path).resolve(strict=True)
    except FileNotFoundError as exc:
        raise FileNotFoundError from exc

    if base_dir not in candidate.parents and candidate != base_dir:
        raise FileNotFoundError("Path outside of result directory")
    if not candidate.is_file():
        raise FileNotFoundError("Not a file")
    if candidate.suffix.lower() != ".csv":
        raise FileNotFoundError("Not a CSV file")
    return candidate


def _read_csv_rows(target: Path) -> List[List[str]]:
    rows: List[List[str]] = []
    try:
        with target.open("r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            rows = [row for row in reader]
    except UnicodeDecodeError:
        with target.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f)
            rows = [row for row in reader]
    return rows


def _unique_recycle_path(base: Path, name: str) -> Path:
    base.mkdir(parents=True, exist_ok=True)
    candidate = base / name
    if not candidate.exists():
        return candidate
    # Append numeric suffix to avoid collisions
    idx = 1
    while True:
        alt = base / f"{name}-{idx}"
        if not alt.exists():
            return alt
        idx += 1


@app.post("/api/datasets/delete")
def delete_dataset() -> Response:
    dataset_name = (request.form.get("dataset") if request.form else None) or (
        request.json.get("dataset") if request.is_json else None
    )
    if not dataset_name:
        abort(400, "Missing 'dataset' in request.")

    # Resolve source paths
    data_src = DATA_BASE_DIR / dataset_name
    result_src = RESULT_BASE_DIR / dataset_name

    # Ensure something exists to delete
    if not data_src.exists() and not result_src.exists():
        abort(404, f"Dataset '{dataset_name}' not found.")

    moved: Dict[str, str] = {}

    # Move data folder
    if data_src.exists():
        data_recycle_base = RECYCLE_DIR / "data"
        data_dest = _unique_recycle_path(data_recycle_base, dataset_name)
        data_dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(data_src), str(data_dest))
        moved["data"] = str(data_dest)

    # Move result folder
    if result_src.exists():
        result_recycle_base = RECYCLE_DIR / "result"
        result_dest = _unique_recycle_path(result_recycle_base, dataset_name)
        result_dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(result_src), str(result_dest))
        moved["result"] = str(result_dest)

    return jsonify({
        "dataset": dataset_name,
        "moved": moved,
        "message": "Dataset moved to recycle folder.",
    })

def _clean_component(component: str) -> str:
    cleaned = component.strip().strip("\\/")
    if cleaned in {"", ".", ".."}:
        raise ValueError("Invalid path component in uploaded folder.")
    if "/" in cleaned or "\\" in cleaned:
        raise ValueError("Invalid path component in uploaded folder.")
    return cleaned


def _validate_import_candidate(dataset_root: Path) -> None:
    if not dataset_root.exists() or not dataset_root.is_dir():
        raise ValueError("Dataset folder is missing inside the archive.")

    version_dirs: Dict[str, Path] = {}
    for plog_dir in dataset_root.rglob("*"):
        if not plog_dir.is_dir():
            continue
        if plog_dir.name.lower() != "performancelog":
            continue
        version_dir = plog_dir.parent
        try:
            version_dir.relative_to(dataset_root)
        except ValueError:
            continue
        if version_dir == dataset_root:
            continue
        version_dirs[version_dir.as_posix()] = version_dir

    if len(version_dirs) < 3:
        raise ValueError(
            "Dataset must contain at least three version folders each containing a PerformanceLog directory."
        )


def _handle_zip_upload(file_storage, tmp_path: Path, provided_name: str | None) -> Tuple[str, Path]:
    archive_name = secure_filename(file_storage.filename or "")
    if not archive_name or not archive_name.lower().endswith(".zip"):
        abort(400, "Dataset archive must be a .zip file.")

    archive_path = tmp_path / archive_name
    file_storage.save(archive_path)

    try:
        with zipfile.ZipFile(archive_path) as zf:
            # Collect valid members and discover top-level folders, skipping hidden/mac metadata
            valid_members = []
            top_levels = set()
            for zi in zf.infolist():
                name = zi.filename.replace("\\", "/")
                if not name or name in {"/", ""}:
                    continue
                if name.startswith("__MACOSX/"):
                    continue
                parts = [p for p in Path(name).parts if p not in {"", ".", ".."}]
                if not parts or (parts[0].startswith("__MACOSX") or parts[0].startswith(".")):
                    continue
                top_levels.add(parts[0])
                valid_members.append(zi)

            if not valid_members:
                abort(400, "Dataset archive is empty.")

            # Determine dataset name
            dataset_name: str | None = None
            if provided_name:
                dataset_name = secure_filename(provided_name)
            elif len(top_levels) == 1:
                dataset_name = secure_filename(next(iter(top_levels)))
            else:
                dataset_name = secure_filename(Path(archive_name).stem)
            if not dataset_name:
                abort(400, "Dataset name is invalid.")

            dataset_root = tmp_path / dataset_name
            if dataset_root.exists():
                shutil.rmtree(dataset_root)
            dataset_root.mkdir(parents=True, exist_ok=True)

            common_prefix = next(iter(top_levels)) if len(top_levels) == 1 else None

            for zi in valid_members:
                name = zi.filename.replace("\\", "/")
                if not name:
                    continue
                if name.endswith("/"):
                    rel = name[:-1]
                else:
                    rel = name
                rel_parts = [p for p in Path(rel).parts if p not in {"", ".", ".."}]
                if not rel_parts:
                    continue
                if rel_parts[0].startswith("__MACOSX") or rel_parts[0].startswith("."):
                    continue
                if common_prefix and rel_parts[0] == common_prefix:
                    rel_parts = rel_parts[1:]
                if rel_parts and rel_parts[0] == dataset_name:
                    rel_parts = rel_parts[1:]
                if not rel_parts:
                    continue
                dest_path = dataset_root.joinpath(*rel_parts)
                if zi.is_dir() or name.endswith("/"):
                    dest_path.mkdir(parents=True, exist_ok=True)
                    continue
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(zi) as src, open(dest_path, "wb") as dst:
                    shutil.copyfileobj(src, dst)

            return dataset_name, dataset_root
    except zipfile.BadZipFile:
        abort(400, "Invalid ZIP archive.")


def _handle_folder_upload(files: List, tmp_path: Path, provided_name: str | None) -> Tuple[str, Path]:
    dataset_name: str | None = None
    if provided_name:
        dataset_name = secure_filename(provided_name)
        if not dataset_name:
            raise ValueError("Dataset name is invalid.")

    saved_any = False

    for storage in files:
        filename = storage.filename or ""
        if not filename:
            continue
        rel_path = Path(filename.replace("\\", "/"))
        parts = [part for part in rel_path.parts if part and part not in {".", ".."}]
        if not parts:
            continue

        if dataset_name is None:
            candidate_name = secure_filename(parts[0])
            if not candidate_name:
                raise ValueError("Dataset name is invalid.")
            dataset_name = candidate_name

        safe_parts = [dataset_name]

        remaining_parts = parts
        if parts and secure_filename(parts[0]) == dataset_name:
            remaining_parts = parts[1:]

        for component in remaining_parts:
            try:
                safe_parts.append(_clean_component(component))
            except ValueError:
                raise ValueError("Detected invalid path inside uploaded folder.") from None

        if len(safe_parts) == 1:
            continue

        destination = tmp_path.joinpath(*safe_parts)
        destination.parent.mkdir(parents=True, exist_ok=True)
        storage.save(destination)
        saved_any = True

    if dataset_name is None or not saved_any:
        raise ValueError("Uploaded folder did not contain any files.")

    extracted_root = tmp_path / dataset_name
    if not extracted_root.exists():
        raise ValueError("Uploaded folder did not contain any files.")

    return dataset_name, extracted_root


@app.post("/api/datasets/import")
def import_dataset() -> Tuple[Response, int]:
    file_storage = request.files.get("file")
    folder_files = request.files.getlist("folder")
    provided_name = request.form.get("datasetName") if request.form else None

    dataset_name: str | None = None
    data_root: Path | None = None
    result_root: Path | None = None
    extracted_root: Path | None = None

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        if file_storage and file_storage.filename:
            dataset_name, extracted_root = _handle_zip_upload(file_storage, tmp_path, provided_name)
        elif folder_files:
            try:
                dataset_name, extracted_root = _handle_folder_upload(
                    folder_files, tmp_path, provided_name
                )
            except ValueError as exc:
                abort(400, str(exc))
        else:
            abort(400, "Missing dataset archive or folder.")

        if extracted_root is None or dataset_name is None:
            abort(500, "Failed to process uploaded dataset.")

        try:
            _validate_import_candidate(extracted_root)
        except ValueError as exc:
            abort(400, str(exc))

        data_root = DATA_BASE_DIR / dataset_name
        result_root = RESULT_BASE_DIR / dataset_name

        if data_root.exists() or result_root.exists():
            abort(409, f"Dataset '{dataset_name}' already exists.")

        data_root.parent.mkdir(parents=True, exist_ok=True)
        RESULT_BASE_DIR.mkdir(parents=True, exist_ok=True)

        shutil.move(str(extracted_root), data_root)

    if data_root is None or result_root is None:
        abort(500, "Failed to process uploaded dataset.")

    try:
        generate_reports(data_root, result_root)
    except Exception as exc:  # pragma: no cover - defensive cleanup
        if data_root and data_root.exists():
            shutil.rmtree(data_root, ignore_errors=True)
        if result_root and result_root.exists():
            shutil.rmtree(result_root, ignore_errors=True)
        abort(500, f"Failed to process dataset: {exc}")

    return (
        jsonify({"dataset": dataset_name, "message": "Dataset imported successfully."}),
        201,
    )


@app.route("/")
def index() -> str:
    view_param = request.args.get("view", "analytics")
    dataset_param = request.args.get("dataset")
    dataset_options = _available_datasets()

    active_dataset = dataset_param or DEFAULT_DATASET_NAME
    if active_dataset:
        try:
            _result_dir_for_dataset(active_dataset)
        except (ValueError, FileNotFoundError):
            active_dataset = None
    if not active_dataset and dataset_options:
        active_dataset = dataset_options[0]

    minimal_state = {
        "view": view_param,
        "selectedDataset": active_dataset or "",
        "datasetOptions": dataset_options,
        "endpoints": {
            "csv": url_for("api_csv"),
            "download": url_for("download_csv"),
            "dashboard": url_for("api_dashboard"),
            "analyticsBar": url_for("analytics_bardata"),
            "importDataset": url_for("import_dataset"),
            "deleteDataset": url_for("delete_dataset"),
        },
    }

    return render_template("index.html", initial_state=minimal_state)


@app.get("/api/dashboard")
def api_dashboard():
    view_param = request.args.get("view", "analytics")
    try:
        state = _build_dashboard_state(view_param, request.args.to_dict(flat=True))
    except ValueError as exc:
        abort(400, str(exc))
    except FileNotFoundError as exc:
        abort(404, str(exc))
    return jsonify(state)


def _load_summary(result_dir: Path) -> Tuple[pd.DataFrame, List[str]]:
    summary_path = result_dir / "summary.csv"
    if not summary_path.exists():
        raise FileNotFoundError("summary.csv not found. Generate it with extract.py --combine")

    df = pd.read_csv(summary_path)
    if "service" not in df.columns:
        raise ValueError("summary.csv must contain a 'service' column")

    df["service"] = df["service"].astype(str)
    df = df[~df["service"].isin(EXCLUDED_SERVICES)]

    numeric_cols = [c for c in df.columns if c != "service"]
    if not numeric_cols:
        raise ValueError("summary.csv must contain at least one version column")

    df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors="coerce")
    return df, numeric_cols


def _prepare_summary(result_dir: Path) -> Tuple[pd.DataFrame, List[str], pd.DataFrame, List[str]]:
    df, version_cols = _load_summary(result_dir)

    melted = df.melt(
        id_vars="service",
        value_vars=version_cols,
        var_name="version",
        value_name="loading_time",
    ).dropna(subset=["loading_time"])

    if melted.empty:
        raise ValueError("summary.csv does not contain numeric data")

    service_order = (
        df["service"]
        .dropna()
        .drop_duplicates()
        .sort_values(key=lambda col: col.str.casefold())
        .tolist()
    )
    return df, version_cols, melted, service_order


def _load_service_stats(result_dir: Path) -> Tuple[pd.DataFrame, List[str]]:
    stats_path = result_dir / "service_stats.csv"
    if not stats_path.exists():
        raise FileNotFoundError("service_stats.csv not found. Generate it with report.py")

    stats_df = pd.read_csv(stats_path)
    if "service" not in stats_df.columns:
        raise ValueError("service_stats.csv must contain a 'service' column")

    version_set = set()
    for col in stats_df.columns:
        if col == "service" or "_" not in col:
            continue
        version, metric = col.rsplit("_", 1)
        if metric in {"avg", "min", "max", "median"}:
            version_set.add(version)

    versions = sorted(version_set)
    stats_df = stats_df.set_index("service")
    stats_df.index = stats_df.index.astype(str)
    stats_df = stats_df[~stats_df.index.isin(EXCLUDED_SERVICES)]
    return stats_df, versions


def _build_bar_figure_from_wide(wide: pd.DataFrame, version_cols: List[str]) -> go.Figure:
    fig = go.Figure()
    y_max = 0.0
    x_labels = wide.index.tolist()
    for version in version_cols:
        if version not in wide.columns:
            continue
        column = wide[version]
        if column.isna().all():
            continue
        values = column.tolist()
        fig.add_trace(
            go.Bar(
                x=x_labels,
                y=values,
                name=version,
                text=[f"{v:.0f}" if pd.notna(v) else "" for v in values],
                textposition="outside",
            )
        )
        current_max = max([v for v in values if pd.notna(v)] or [0])
        y_max = max(y_max, current_max)

    if not fig.data:
        return fig

    y_buffer = y_max * 0.1 if y_max else 0
    fig.update_yaxes(range=[0, y_max + y_buffer])
    fig.update_layout(
        title="Average Loading Time per Service (Grouped Bar)",
        xaxis_title="Service",
        yaxis_title="Average Loading Time (ms)",
        margin=dict(l=30, r=20, t=60, b=80),
        barmode="group",
        legend_title="Version",
    )
    return fig


def _validate_dataset_requirements(melted: pd.DataFrame) -> Tuple[List[str], str | None]:
    warnings: List[str] = []
    error: str | None = None

    if melted.empty:
        return warnings, error

    cleaned = melted.copy()
    cleaned["service"] = cleaned["service"].astype(str).str.strip()

    unique_services = sorted(cleaned["service"].dropna().unique())
    service_count = len(unique_services)
    if service_count != 24:
        warnings.append(f"Warning: dataset must include 24 services, found {service_count}.")

    service_counts = cleaned.groupby("service")["loading_time"].count()

    auto_service = None
    for service_name in service_counts.index:
        if service_name.upper() == "AUTO TEST":
            auto_service = service_name
            break

    if auto_service is None:
        error = "Error: dataset is missing required 'AUTO TEST' service."
        return warnings, error

    baseline = int(service_counts.get(auto_service, 0))
    mismatched: List[str] = []
    for service_name, count in service_counts.items():
        count = int(count)
        if service_name == auto_service:
            continue
        if count != baseline:
            mismatched.append(f"{service_name} ({count} samples)")

    if mismatched:
        mismatch_list = ", ".join(mismatched)
        warnings.append(
            f"Warning: sample counts differ from AUTO TEST ({baseline} samples): {mismatch_list}."
        )

    return warnings, error


    return warnings, error


def _build_box_from_stats(
    stats_df: pd.DataFrame,
    version: str,
    service_order: List[str],
) -> go.Figure | None:
    required_cols = [f"{version}_" + metric for metric in ("min", "median", "avg", "max")]
    if not all(col in stats_df.columns for col in required_cols):
        return None

    fig = go.Figure()
    targets = service_order if service_order else stats_df.index.tolist()
    if not service_order:
        targets = sorted(stats_df.index.tolist(), key=lambda s: str(s).casefold())
    for service in targets:
        if service not in stats_df.index:
            continue
        row = stats_df.loc[service]
        values = [row.get(col) for col in required_cols]
        cleaned = [float(v) for v in values if pd.notna(v)]
        if not cleaned:
            continue
        stats_tuple = (
            row.get(required_cols[0]),
            row.get(required_cols[1]),
            row.get(required_cols[2]),
            row.get(required_cols[3]),
        )
        customdata = [
            [
                stats_tuple[0],
                stats_tuple[1],
                stats_tuple[2],
                stats_tuple[3],
            ]
        ] * len(cleaned)
        fig.add_trace(
            go.Box(
                y=cleaned,
                name=service,
                boxpoints=False,
                boxmean=True,
                customdata=customdata,
                hovertemplate=(
                    "Service: %{x}<br>"
                    "Min: %{customdata[0]:.0f} ms<br>"
                    "Median: %{customdata[1]:.0f} ms<br>"
                    "Average: %{customdata[2]:.0f} ms<br>"
                    "Max: %{customdata[3]:.0f} ms"
                    "<extra></extra>"
                ),
            )
        )

    if not fig.data:
        return None

    fig.update_layout(
        title=f"Service Loading Time Distribution ({version})",
        yaxis_title="Loading Time (ms)",
        xaxis_title="Service",
        margin=dict(l=30, r=20, t=60, b=80),
        showlegend=False,
    )
    return fig


@app.route("/view")
def view_csv() -> str:
    rel_path = request.args.get("file")
    if not rel_path:
        abort(400, "Missing 'file' query parameter")

    try:
        target = _safe_resolve(rel_path)
    except FileNotFoundError:
        abort(404, "CSV not found")

    rows = _read_csv_rows(target)
    headers = rows[0] if rows else []
    data_rows = rows[1:] if len(rows) > 1 else []

    template = """
    <!doctype html>
    <html lang="en">
    <head>
        <meta charset="utf-8" />
        <title>{{ filename }}</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 2rem; }
            h1 { margin-bottom: 1rem; }
            table { border-collapse: collapse; width: 100%; }
            th, td { border: 1px solid #ccc; padding: 0.5rem; text-align: left; }
            th { background: #f2f2f2; }
            tr:nth-child(even) { background: #fafafa; }
            .toolbar { margin-bottom: 1rem; }
            a { text-decoration: none; color: #1a73e8; }
            a:hover { text-decoration: underline; }
        </style>
    </head>
    <body>
        <div class="toolbar"><a href="{{ url_for('index') }}">&#8592; Back to list</a> |
            <a href="{{ download_url }}" download>Download CSV</a></div>
        <h1>{{ filename }}</h1>
        {% if headers %}
        <table>
            <thead>
                <tr>
                {% for head in headers %}
                    <th>{{ head }}</th>
                {% endfor %}
                </tr>
            </thead>
            <tbody>
            {% if data_rows %}
                {% for row in data_rows %}
                <tr>
                    {% for cell in row %}
                    <td>{{ cell }}</td>
                    {% endfor %}
                </tr>
                {% endfor %}
            {% else %}
                <tr><td colspan="{{ headers|length }}">No data rows</td></tr>
            {% endif %}
            </tbody>
        </table>
        {% else %}
            <p>No data available in this CSV.</p>
        {% endif %}
    </body>
    </html>
    """

    return render_template_string(
        template,
        filename=rel_path,
        headers=headers,
        data_rows=data_rows,
        download_url=url_for("download_csv", file=rel_path),
    )


@app.route("/download")
def download_csv():
    rel_path = request.args.get("file")
    if not rel_path:
        abort(400, "Missing 'file' query parameter")

    try:
        target = _safe_resolve(rel_path)
    except FileNotFoundError:
        abort(404, "CSV not found")

    return send_file(target, mimetype="text/csv", as_attachment=True, download_name=target.name)


@app.route("/api/csv")
def api_csv():
    rel_path = request.args.get("file")
    if not rel_path:
        abort(400, "Missing 'file' query parameter")

    dataset_param = request.args.get("dataset")
    result_root = RESULT_DIR
    if dataset_param:
        try:
            result_root = _result_dir_for_dataset(dataset_param)
        except (ValueError, FileNotFoundError):
            abort(404, "Dataset not found")

    try:
        target = _safe_resolve(rel_path, base=result_root)
    except FileNotFoundError:
        abort(404, "CSV not found")

    rows = _read_csv_rows(target)
    headers = rows[0] if rows else []
    data_rows = rows[1:] if len(rows) > 1 else []
    return jsonify(
        {
            "file": rel_path,
            "dataset": dataset_param or "",
            "headers": headers,
            "rows": data_rows,
        }
    )


def _load_summary(result_dir: Path) -> Tuple[pd.DataFrame, List[str]]:
    summary_path = result_dir / "summary.csv"
    if not summary_path.exists():
        raise FileNotFoundError("summary.csv not found. Generate it with extract.py --combine")

    df = pd.read_csv(summary_path)
    if "service" not in df.columns:
        raise ValueError("summary.csv must contain a 'service' column")

    df["service"] = df["service"].astype(str)
    df = df[~df["service"].isin(EXCLUDED_SERVICES)]

    numeric_cols = [c for c in df.columns if c != "service"]
    if not numeric_cols:
        raise ValueError("summary.csv must contain at least one version column")

    df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors="coerce")
    return df, numeric_cols


def _prepare_summary(result_dir: Path) -> Tuple[pd.DataFrame, List[str], pd.DataFrame, List[str]]:
    df, version_cols = _load_summary(result_dir)

    melted = df.melt(
        id_vars="service",
        value_vars=version_cols,
        var_name="version",
        value_name="loading_time",
    ).dropna(subset=["loading_time"])

    if melted.empty:
        raise ValueError("summary.csv does not contain numeric data")

    service_order = (
        df["service"]
        .dropna()
        .drop_duplicates()
        .sort_values(key=lambda col: col.str.casefold())
        .tolist()
    )
    return df, version_cols, melted, service_order


def _load_service_stats(result_dir: Path) -> Tuple[pd.DataFrame, List[str]]:
    stats_path = result_dir / "service_stats.csv"
    if not stats_path.exists():
        raise FileNotFoundError("service_stats.csv not found. Generate it with report.py")

    stats_df = pd.read_csv(stats_path)
    if "service" not in stats_df.columns:
        raise ValueError("service_stats.csv must contain a 'service' column")

    version_set = set()
    for col in stats_df.columns:
        if col == "service" or "_" not in col:
            continue
        version, metric = col.rsplit("_", 1)
        if metric in {"avg", "min", "max", "median"}:
            version_set.add(version)

    versions = sorted(version_set)
    stats_df = stats_df.set_index("service")
    stats_df.index = stats_df.index.astype(str)
    stats_df = stats_df[~stats_df.index.isin(EXCLUDED_SERVICES)]
    return stats_df, versions


def _build_bar_figure_from_wide(wide: pd.DataFrame, version_cols: List[str]) -> go.Figure:
    fig = go.Figure()
    y_max = 0.0
    x_labels = wide.index.tolist()
    for version in version_cols:
        if version not in wide.columns:
            continue
        column = wide[version]
        if column.isna().all():
            continue
        values = column.tolist()
        fig.add_trace(
            go.Bar(
                x=x_labels,
                y=values,
                name=version,
                text=[f"{v:.0f}" if pd.notna(v) else "" for v in values],
                textposition="outside",
            )
        )
        current_max = max([v for v in values if pd.notna(v)] or [0])
        y_max = max(y_max, current_max)

    if not fig.data:
        return fig

    y_buffer = y_max * 0.1 if y_max else 0
    fig.update_yaxes(range=[0, y_max + y_buffer])
    fig.update_layout(
        title="Average Loading Time per Service (Grouped Bar)",
        xaxis_title="Service",
        yaxis_title="Average Loading Time (ms)",
        margin=dict(l=30, r=20, t=60, b=80),
        barmode="group",
        legend_title="Version",
    )
    return fig


def _validate_dataset_requirements(melted: pd.DataFrame) -> Tuple[List[str], str | None]:
    warnings: List[str] = []
    error: str | None = None

    if melted.empty:
        return warnings, error

    cleaned = melted.copy()
    cleaned["service"] = cleaned["service"].astype(str).str.strip()

    unique_services = sorted(cleaned["service"].dropna().unique())
    service_count = len(unique_services)
    if service_count != 24:
        warnings.append(f"Warning: dataset must include 24 services, found {service_count}.")

    service_counts = cleaned.groupby("service")["loading_time"].count()

    auto_service = None
    for service_name in service_counts.index:
        if service_name.upper() == "AUTO TEST":
            auto_service = service_name
            break

    if auto_service is None:
        error = "Error: dataset is missing required 'AUTO TEST' service."
        return warnings, error

    baseline = int(service_counts.get(auto_service, 0))
    mismatched: List[str] = []
    for service_name, count in service_counts.items():
        count = int(count)
        if service_name == auto_service:
            continue
        if count != baseline:
            mismatched.append(f"{service_name} ({count} samples)")

    if mismatched:
        mismatch_list = ", ".join(mismatched)
        warnings.append(
            f"Warning: sample counts differ from AUTO TEST ({baseline} samples): {mismatch_list}."
        )

    return warnings, error


    return warnings, error


def _build_box_from_stats(
    stats_df: pd.DataFrame,
    version: str,
    service_order: List[str],
) -> go.Figure | None:
    required_cols = [f"{version}_" + metric for metric in ("min", "median", "avg", "max")]
    if not all(col in stats_df.columns for col in required_cols):
        return None

    fig = go.Figure()
    targets = service_order if service_order else stats_df.index.tolist()
    if not service_order:
        targets = sorted(stats_df.index.tolist(), key=lambda s: str(s).casefold())
    for service in targets:
        if service not in stats_df.index:
            continue
        row = stats_df.loc[service]
        values = [row.get(col) for col in required_cols]
        cleaned = [float(v) for v in values if pd.notna(v)]
        if not cleaned:
            continue
        stats_tuple = (
            row.get(required_cols[0]),
            row.get(required_cols[1]),
            row.get(required_cols[2]),
            row.get(required_cols[3]),
        )
        customdata = [
            [
                stats_tuple[0],
                stats_tuple[1],
                stats_tuple[2],
                stats_tuple[3],
            ]
        ] * len(cleaned)
        fig.add_trace(
            go.Box(
                y=cleaned,
                name=service,
                boxpoints=False,
                boxmean=True,
                customdata=customdata,
                hovertemplate=(
                    "Service: %{x}<br>"
                    "Min: %{customdata[0]:.0f} ms<br>"
                    "Median: %{customdata[1]:.0f} ms<br>"
                    "Average: %{customdata[2]:.0f} ms<br>"
                    "Max: %{customdata[3]:.0f} ms"
                    "<extra></extra>"
                ),
            )
        )

    if not fig.data:
        return None

    fig.update_layout(
        title=f"Service Loading Time Distribution ({version})",
        yaxis_title="Loading Time (ms)",
        xaxis_title="Service",
        margin=dict(l=30, r=20, t=60, b=80),
        showlegend=False,
    )
    return fig


def _build_dashboard_state(active_view: str, query_params: Dict[str, str]) -> Dict[str, object]:
    view_mode = active_view if active_view in {"analytics", "reports", "compare"} else "analytics"
    dataset_param = query_params.get("dataset")
    dataset_options = _available_datasets()
    active_dataset = dataset_param or DEFAULT_DATASET_NAME
    if not active_dataset and dataset_options:
        active_dataset = dataset_options[0]

    active_result_dir = _result_dir_for_dataset(active_dataset)

    if active_dataset and active_dataset not in dataset_options:
        dataset_options = sorted(set(dataset_options + [active_dataset]))

    selected_dataset = active_dataset or ""

    dataset_label = selected_dataset or "Current Dataset"

    report_paths = _list_csv_files_under(active_result_dir)
    report_files = [p.relative_to(active_result_dir).as_posix() for p in report_paths]

    # Group all CSVs under the selected dataset name as the single group label.
    report_groups: Dict[str, List[str]] = {
        dataset_label: sorted(report_files)
    }

    selected_report_param = query_params.get("report")
    initial_report = (
        selected_report_param
        if selected_report_param and selected_report_param in report_files
        else (report_files[0] if report_files else "")
    )

    df, version_cols, melted, service_order = _prepare_summary(active_result_dir)
    stats_df, stats_versions = _load_service_stats(active_result_dir)

    available_box_versions = [v for v in version_cols if v in stats_versions]
    dropdown_versions = available_box_versions if available_box_versions else version_cols

    dataset_warnings, dataset_error = _validate_dataset_requirements(melted)
    bar_alerts: List[str] = list(dataset_warnings)
    if dataset_error:
        bar_alerts.append(dataset_error)

    compare_version_a = query_params.get("compareA")
    compare_version_b = query_params.get("compareB")
    compare_filter = query_params.get("filter", "all")
    if compare_filter not in {"positive", "negative"}:
        compare_filter = "all"
    if compare_version_a not in version_cols:
        compare_version_a = version_cols[0] if version_cols else ""
    if compare_version_b not in version_cols:
        compare_version_b = version_cols[1] if len(version_cols) > 1 else compare_version_a

    selected_version = query_params.get("version")
    if not selected_version or selected_version not in dropdown_versions:
        selected_version = dropdown_versions[0] if dropdown_versions else ""

    metrics = ["Average", "Max", "Min", "Median"]
    version_stats_df = pd.DataFrame(
        {
            "Average": df[version_cols].mean(skipna=True),
            "Max": df[version_cols].max(skipna=True),
            "Min": df[version_cols].min(skipna=True),
            "Median": df[version_cols].median(skipna=True),
        }
    )
    version_stats_df = version_stats_df[metrics].round(2)

    version_stats_rows: List[Dict[str, object]] = []
    for metric in metrics:
        metric_values: Dict[str, float | None] = {}
        for version in version_cols:
            if version in version_stats_df.index:
                value = version_stats_df.at[version, metric]
                metric_values[version] = float(value) if pd.notna(value) else None
            else:
                metric_values[version] = None
        version_stats_rows.append({"metric": metric, "values": metric_values})

    box_figures: Dict[str, Dict[str, object]] = {}
    for ver in dropdown_versions:
        fig = _build_box_from_stats(stats_df, ver, service_order)
        box_figures[ver] = json.loads(fig.to_json()) if fig else {"data": [], "layout": {}}

    service_avg_multi = (
        melted.groupby(["service", "version"])["loading_time"].mean().reset_index()
    )
    if service_order:
        service_avg_multi["service"] = pd.Categorical(
            service_avg_multi["service"], categories=service_order, ordered=True
        )
        service_avg_multi = service_avg_multi.sort_values("service")
    else:
        service_avg_multi = service_avg_multi.sort_values(
            "service", key=lambda col: col.astype(str).str.casefold()
        )

    wide = pd.DataFrame()
    if not service_avg_multi.empty:
        wide = service_avg_multi.pivot(index="service", columns="version", values="loading_time")
        if service_order:
            wide = wide.reindex(service_order)
        wide = wide.dropna(how="all")

    line_fig_payload: Dict[str, object] = {"data": [], "layout": {}}
    bar_fig_payload: Dict[str, object] = {"data": [], "layout": {}}

    if not wide.empty:
        fig_line = go.Figure()
        for version in version_cols:
            if version in wide.columns and not wide[version].dropna().empty:
                fig_line.add_trace(
                    go.Scatter(
                        x=wide.index.tolist(),
                        y=wide[version].tolist(),
                        mode="lines+markers",
                        name=version,
                    )
                )
        if fig_line.data:
            fig_line.update_layout(
                title="Average Loading Time per Service (by Version)",
                xaxis_title="Service",
                yaxis_title="Average Loading Time (ms)",
                margin=dict(l=30, r=20, t=60, b=80),
                legend_title="Version",
            )
            line_fig_payload = json.loads(fig_line.to_json())

        if not dataset_error:
            fig_bar = _build_bar_figure_from_wide(wide, version_cols)
            if fig_bar.data:
                bar_fig_payload = json.loads(fig_bar.to_json())

    compare_data: Dict[str, Dict[str, float]] = {}
    compare_services: List[str] = []
    if not service_avg_multi.empty:
        pivot = service_avg_multi.pivot(
            index="service", columns="version", values="loading_time"
        )
        if service_order:
            pivot = pivot.reindex(service_order)
        compare_services = [
            svc for svc in pivot.index.tolist() if isinstance(svc, str)
        ]
        for svc in compare_services:
            row = pivot.loc[svc]
            svc_values: Dict[str, float] = {}
            for ver in version_cols:
                val = row.get(ver)
                if pd.notna(val):
                    try:
                        svc_values[ver] = float(val)
                    except Exception:
                        continue
            if svc_values:
                compare_data[svc] = svc_values

    state: Dict[str, object] = {
        "activeView": view_mode,
        "views": ["analytics", "reports", "compare"],
        "datasetOptions": dataset_options,
        "selectedDataset": selected_dataset,
        "datasetWarnings": dataset_warnings,
        "datasetError": dataset_error,
        "barAlerts": bar_alerts,
        "versions": version_cols,
        "boxVersions": dropdown_versions,
        "selectedVersion": selected_version,
        "versionStats": {
            "metrics": metrics,
            "versions": version_stats_df.index.tolist(),
            "rows": version_stats_rows,
        },
        "boxFigures": box_figures,
        "lineFigure": line_fig_payload,
        "barFigure": bar_fig_payload,
        "reports": {
            "files": report_files,
            "groups": report_groups,
            "initial": initial_report,
        },
        "compare": {
            "services": compare_services,
            "data": compare_data,
            "defaults": {
                "versionA": compare_version_a,
                "versionB": compare_version_b,
                "filter": compare_filter,
            },
        },
        "serviceOrder": service_order,
        "endpoints": {
            "csv": url_for("api_csv"),
            "download": url_for("download_csv"),
            "dashboard": url_for("api_dashboard"),
            "analyticsBar": url_for("analytics_bardata"),
            "importDataset": url_for("import_dataset"),
            "deleteDataset": url_for("delete_dataset"),
        },
    }
    return state


@app.route("/analytics")
def analytics():
    params = request.args.to_dict(flat=True)
    params["view"] = "analytics"
    return redirect(url_for("index", **params))


@app.route("/analytics/bardata")
def analytics_bardata():
    dataset_param = request.args.get("dataset")
    dataset_options = _available_datasets()
    dataset = dataset_param or DEFAULT_DATASET_NAME
    if not dataset and dataset_options:
        dataset = dataset_options[0]

    try:
        result_dir = _result_dir_for_dataset(dataset)
        df, version_cols, melted, service_order = _prepare_summary(result_dir)
    except (ValueError, FileNotFoundError) as exc:
        abort(404, str(exc))

    dataset_warnings, dataset_error = _validate_dataset_requirements(melted)
    response_payload = {
        "dataset": dataset or "",
        "warnings": dataset_warnings,
        "error": dataset_error,
        "figure": {"data": [], "layout": {}},
    }
    if dataset_error:
        return jsonify(response_payload)

    service_avg_multi = (
        melted.groupby(["service", "version"])["loading_time"].mean().reset_index()
    )
    if service_order:
        service_avg_multi["service"] = pd.Categorical(
            service_avg_multi["service"], categories=service_order, ordered=True
        )
        service_avg_multi = service_avg_multi.sort_values("service")
    else:
        service_avg_multi = service_avg_multi.sort_values(
            "service", key=lambda col: col.astype(str).str.casefold()
        )
    if service_avg_multi.empty:
        return jsonify(response_payload)

    wide = service_avg_multi.pivot(index="service", columns="version", values="loading_time")
    if service_order:
        wide = wide.reindex(service_order)
    wide = wide.dropna(how="all")

    if wide.empty:
        return jsonify(response_payload)

    fig_bar = _build_bar_figure_from_wide(wide, version_cols)
    response_payload["figure"] = json.loads(fig_bar.to_json())
    return jsonify(response_payload)


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Service Performance Metric web application")
    parser.add_argument("--host", default="0.0.0.0", help="Host interface to bind (default: 0.0.0.0)")
    parser.add_argument("--port", default=8000, type=int, help="Port to listen on (default: 8000)")
    parser.add_argument("--debug", action="store_true", help="Enable Flask debug mode")
    args = parser.parse_args(argv)

    app.run(debug=args.debug, host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
