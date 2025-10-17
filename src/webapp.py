from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd
import plotly.graph_objects as go
from plotly.io import to_html
from flask import Flask, abort, jsonify, redirect, render_template_string, request, send_file, url_for


app = Flask(__name__)

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


@app.route("/")
def index() -> str:
    view_param = request.args.get("view", "analytics")
    return _render_dashboard_page(view_param)


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


def _render_dashboard_page(active_view: str) -> str:
    view_mode = active_view if active_view in {"analytics", "reports", "compare"} else "analytics"
    dataset_param = request.args.get("dataset")
    dataset_options = _available_datasets()
    active_dataset = dataset_param or DEFAULT_DATASET_NAME
    if not active_dataset and dataset_options:
        active_dataset = dataset_options[0]

    try:
        active_result_dir = _result_dir_for_dataset(active_dataset)
    except ValueError as exc:
        abort(400, str(exc))
    except FileNotFoundError as exc:
        abort(404, str(exc))

    report_paths = _list_csv_files_under(active_result_dir)
    report_files = [p.relative_to(active_result_dir).as_posix() for p in report_paths]
    selected_report_param = request.args.get("report")
    initial_report = (
        selected_report_param
        if selected_report_param and selected_report_param in report_files
        else (report_files[0] if report_files else "")
    )

    if active_dataset and active_dataset not in dataset_options:
        dataset_options = sorted(set(dataset_options + [active_dataset]))

    selected_dataset = active_dataset or ""

    try:
        df, version_cols, melted, service_order = _prepare_summary(active_result_dir)
        stats_df, stats_versions = _load_service_stats(active_result_dir)
    except (FileNotFoundError, ValueError) as exc:
        abort(404, str(exc))

    available_box_versions = [v for v in version_cols if v in stats_versions]
    dropdown_versions = available_box_versions if available_box_versions else version_cols

    dataset_warnings, dataset_error = _validate_dataset_requirements(melted)
    bar_alerts: List[str] = list(dataset_warnings)
    if dataset_error:
        bar_alerts.append(dataset_error)

    compare_version_a = request.args.get("compareA")
    compare_version_b = request.args.get("compareB")
    if compare_version_a not in version_cols:
        compare_version_a = version_cols[0] if version_cols else ""
    if compare_version_b not in version_cols:
        compare_version_b = (
            version_cols[1] if len(version_cols) > 1 else compare_version_a
        )

    selected_version = request.args.get("version")
    if not selected_version or selected_version not in dropdown_versions:
        selected_version = dropdown_versions[0]

    # Per-version evolution table using pandas
    version_stats_df = pd.DataFrame({
        "Average": df[version_cols].mean(skipna=True),
        "Max": df[version_cols].max(skipna=True),
        "Min": df[version_cols].min(skipna=True),
        "Median": df[version_cols].median(skipna=True),
    })
    version_stats_df = version_stats_df[["Average", "Max", "Min", "Median"]]
    version_stats_html = version_stats_df.T.round(2).to_html(classes="table", border=0)

    # Prepare tidy data for visualisations
    box_figures: Dict[str, Dict] = {}
    for ver in dropdown_versions:
        fig = _build_box_from_stats(stats_df, ver, service_order)
        box_figures[ver] = json.loads(fig.to_json()) if fig else {"data": [], "layout": {}}

    # Average time per service line chart (all versions)
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

    line_html = "<p>No data available for line chart.</p>"
    bar_html = "<p>No data available for bar chart.</p>"
    line_fig_payload = {}
    bar_fig_payload = {}
    if dataset_error:
        bar_html = f"<p class=\"message error\">{dataset_error}</p>"
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
        fig_line.update_layout(
            title="Average Loading Time per Service (by Version)",
            xaxis_title="Service",
            yaxis_title="Average Loading Time (ms)",
            margin=dict(l=30, r=20, t=60, b=80),
            legend_title="Version",
        )
        line_html = to_html(fig_line, include_plotlyjs=False, full_html=False)
        line_fig_payload = json.loads(fig_line.to_json())

        if not dataset_error:
            fig_bar = _build_bar_figure_from_wide(wide, version_cols)
            bar_html = to_html(fig_bar, include_plotlyjs=False, full_html=False)
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

    template = """
    <!doctype html>
    <html lang="en">
    <head>
        <meta charset="utf-8" />
        <title>Analytics Dashboard</title>
        <style>
            :root {
                color-scheme: light;
                font-family: Arial, sans-serif;
            }
            body {
                margin: 0;
                background: #f7f8fa;
                height: 100vh;
                overflow: hidden;
            }
            a {
                color: #1a73e8;
                text-decoration: none;
            }
            a:hover { text-decoration: underline; }

            .app {
                display: flex;
                min-height: 100vh;
            }
            .sidebar {
                width: 70px;
                background: #1f2933;
                color: #fff;
                display: flex;
                flex-direction: column;
                align-items: center;
                padding: 1rem 0;
                gap: 1rem;
                box-shadow: inset -1px 0 0 rgba(15, 23, 42, 0.4);
                position: sticky;
                top: 0;
                align-self: flex-start;
                flex-shrink: 0;
                min-height: 100vh;
            }
            .sidebar-btn {
                width: 100%;
                border: none;
                background: transparent;
                color: inherit;
                display: flex;
                flex-direction: column;
                align-items: center;
                gap: 0.35rem;
                padding: 0.55rem 0;
                cursor: pointer;
                opacity: 0.7;
                transition: opacity 0.2s ease, background 0.2s ease;
            }
            .sidebar-btn .icon {
                font-size: 1.35rem;
            }
            .sidebar-btn .label {
                font-size: 0.62rem;
                letter-spacing: 0.08em;
            }
            .sidebar-btn.active,
            .sidebar-btn:hover {
                opacity: 1;
                background: rgba(255, 255, 255, 0.12);
            }
            .main-shell {
                flex: 1;
                display: flex;
                flex-direction: column;
                min-height: 100vh;
                height: 100vh;
                overflow: hidden;
            }
            header {
                position: sticky;
                top: 0;
                z-index: 10;
                background: #ffffffd9;
                backdrop-filter: blur(6px);
                border-bottom: 1px solid #e0e4ea;
                padding: 1rem 2rem;
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 1rem;
            }
            header h1 {
                margin: 0;
                font-size: 1.4rem;
                font-weight: 600;
            }
            .view-indicator {
                font-size: 0.85rem;
                color: #52606d;
                margin-left: 0.75rem;
            }
            .controls {
                display: flex;
                align-items: center;
                gap: 1rem;
                font-size: 0.95rem;
            }
            .control-group {
                display: flex;
                align-items: center;
                gap: 0.5rem;
            }
            .control-group label {
                font-weight: 600;
                color: #4a4f57;
            }
            select {
                padding: 0.35rem 0.6rem;
                border-radius: 6px;
                border: 1px solid #c7ccd6;
                font-size: 0.95rem;
                background: #fff;
            }
            main {
                flex: 1;
                padding: 1.5rem 2rem 2rem;
                overflow-y: auto;
            }
            .panel {
                display: none;
            }
            .panel.active {
                display: block;
            }
            .grid {
                display: grid;
                grid-template-columns: repeat(2, minmax(0, 1fr));
                gap: 1.5rem;
            }
            .card {
                background: #fff;
                border-radius: 12px;
                padding: 1.25rem;
                box-shadow: 0 6px 16px -12px rgba(0,0,0,0.35);
                display: flex;
                flex-direction: column;
                min-height: 300px;
            }
            .card h2 {
                margin: 0 0 0.75rem;
                font-size: 1.1rem;
                font-weight: 600;
                color: #1f2933;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .card h2 span {
                font-size: 0.9rem;
                font-weight: 400;
                color: #6b7280;
            }
            .table {
                border-collapse: collapse;
                width: 100%;
                font-size: 0.9rem;
            }
            .table th,
            .table td {
                border: 1px solid #e0e4ea;
                padding: 0.4rem 0.6rem;
                text-align: right;
            }
            .table th:first-child,
            .table td:first-child {
                text-align: left;
            }
            .table thead {
                background: #f2f4f8;
            }
            .chart-area {
                flex: 1;
                min-height: 260px;
            }
            #boxPlot {
                width: 100%;
                height: 100%;
                min-height: 260px;
            }
            .message {
                color: #6b7280;
                font-size: 0.9rem;
            }
            .message.error {
                color: #d14343;
                font-weight: 600;
            }
            .message.warning {
                color: #b7791f;
                font-weight: 600;
            }
            .card-actions {
                display: flex;
                gap: 0.5rem;
            }
            .btn {
                border-radius: 6px;
                border: 1px solid #c7ccd6;
                background: #fff;
                padding: 0.35rem 0.7rem;
                font-size: 0.85rem;
                cursor: pointer;
                transition: background 0.2s ease, border-color 0.2s ease;
            }
           .btn:hover {
               background: #eef3fb;
               border-color: #a7b6d0;
           }
            .btn.btn-expand {
                font-size: 0.8rem;
                padding: 0.25rem 0.5rem;
            }
           .btn.btn-close {
               font-size: 0.85rem;
               padding: 0.35rem 0.7rem;
           }
            .reports-layout {
                display: grid;
                grid-template-columns: minmax(220px, 280px) minmax(0, 1fr);
                gap: 1.5rem;
                align-items: stretch;
            }
            .reports-list,
            .reports-viewer {
                background: #fff;
                border-radius: 12px;
                box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08);
                min-height: 320px;
            }
            .reports-list {
                padding: 1rem;
                display: flex;
                flex-direction: column;
                max-height: calc(100vh - 220px);
            }
            .reports-list h2 {
                margin: 0 0 0.75rem;
                font-size: 1rem;
                font-weight: 600;
            }
            .reports-list ul {
                list-style: none;
                padding: 0;
                margin: 0;
                overflow-y: auto;
            }
            .reports-list li {
                margin-bottom: 0.4rem;
            }
            .report-link {
                width: 100%;
                border: none;
                border-radius: 8px;
                background: #eef2f7;
                color: #1f2933;
                font-size: 0.9rem;
                padding: 0.45rem 0.6rem;
                text-align: left;
                cursor: pointer;
                transition: background 0.2s ease, color 0.2s ease;
            }
            .report-link:hover {
                background: #d9e2f1;
            }
            .report-link.active {
                background: #1a73e8;
                color: #fff;
            }
            .reports-viewer {
                padding: 1rem;
                display: flex;
                flex-direction: column;
            }
            .reports-viewer h2 {
                margin: 0 0 0.75rem;
                font-size: 1rem;
                font-weight: 600;
                display: flex;
                align-items: center;
                justify-content: space-between;
            }
            .reports-viewer h2 small {
                font-size: 0.75rem;
                color: #52606d;
                margin-left: 0.5rem;
            }
            .compare-card {
                background: #fff;
                border-radius: 12px;
                box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08);
                padding: 1.25rem;
                display: flex;
                flex-direction: column;
                gap: 1rem;
            }
            .compare-header {
                display: flex;
                flex-direction: column;
                gap: 0.75rem;
            }
            .compare-header h2 {
                margin: 0;
                font-size: 1.1rem;
                font-weight: 600;
                color: #1f2933;
            }
            .compare-controls {
                display: flex;
                flex-wrap: wrap;
                align-items: center;
                gap: 0.75rem;
            }
            .compare-controls label {
                font-weight: 600;
                color: #4a4f57;
            }
            .compare-table-wrapper {
                overflow: auto;
            }
            #compareTable {
                width: 100%;
                border-collapse: collapse;
            }
            #compareTable th,
            #compareTable td {
                border: 1px solid #e0e4ea;
                padding: 0.45rem 0.6rem;
                font-size: 0.9rem;
                text-align: left;
            }
            #compareTable thead {
                background: #f2f4f8;
                position: sticky;
                top: 0;
            }
            #compareTable td.value {
                text-align: right;
            }
            #compareTable td.diff-positive {
                color: #0f7a0f;
                font-weight: 600;
            }
            #compareTable td.diff-negative {
                color: #d14343;
                font-weight: 600;
            }
            #compareTable td.diff-neutral {
                color: #52606d;
            }
            #reportContent {
                flex: 1;
                overflow: auto;
                border-radius: 8px;
            }
            #reportContent table {
                width: 100%;
                border-collapse: collapse;
            }
            #reportContent th,
            #reportContent td {
                border: 1px solid #e0e4ea;
                padding: 0.35rem 0.5rem;
                font-size: 0.88rem;
                text-align: left;
            }
            #reportContent thead {
                background: #f2f4f8;
                position: sticky;
                top: 0;
            }
            .overlay {
                position: fixed;
                inset: 0;
                z-index: 50;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .overlay-backdrop {
                position: absolute;
                inset: 0;
                background: rgba(15, 23, 42, 0.55);
                backdrop-filter: blur(4px);
            }
            .overlay-content {
                position: relative;
                background: #fff;
                border-radius: 12px;
                width: 96vw;
                height: 96vh;
                display: flex;
                flex-direction: column;
                box-shadow: 0 25px 60px -20px rgba(15,23,42,0.45);
            }
            .overlay-header {
                padding: 1rem 1.5rem;
                border-bottom: 1px solid #e0e4ea;
                display: flex;
                justify-content: space-between;
                align-items: center;
                gap: 1rem;
            }
            .overlay-header h3 {
                margin: 0;
                font-size: 1.1rem;
            }
            .overlay-body {
                padding: 1.5rem;
                overflow: auto;
                flex: 1;
                display: flex;
                flex-direction: column;
            }
            .overlay-body table {
                width: 100%;
            }
            .overlay-body .plot-container {
                width: 100%;
                flex: 1 1 auto;
                min-height: 0;
                height: 100%;
            }
            .overlay-controls {
                display: flex;
                align-items: center;
                gap: 0.75rem;
                margin-bottom: 1rem;
            }
            .overlay-controls label {
                font-weight: 600;
                color: #4a4f57;
            }
            .overlay-controls select {
                padding: 0.35rem 0.6rem;
                border-radius: 6px;
                border: 1px solid #c7ccd6;
                font-size: 0.95rem;
                background: #fff;
            }

            @media (max-width: 1100px) {
                body {
                    height: auto;
                    overflow: auto;
                }
                .app {
                    flex-direction: column;
                }
                .sidebar {
                    width: 100%;
                    flex-direction: row;
                    justify-content: center;
                    box-shadow: inset 0 -1px 0 rgba(15, 23, 42, 0.1);
                    position: static;
                    min-height: auto;
                    height: auto;
                }
                .sidebar-btn {
                    flex-direction: row;
                    gap: 0.5rem;
                    padding: 0.6rem 1rem;
                }
                .main-shell {
                    min-height: auto;
                    height: auto;
                    overflow: visible;
                }
                header {
                    flex-direction: column;
                    align-items: flex-start;
                }
                .controls {
                    flex-wrap: wrap;
                }
                .grid {
                    grid-template-columns: 1fr;
                }
                .reports-layout {
                    grid-template-columns: 1fr;
                }
                .reports-list {
                    max-height: none;
                }
                .overlay-content {
                    width: 98vw;
                    height: 94vh;
                }
            }
        </style>
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    </head>
    <body>
        <div class="app">
            <aside class="sidebar">
                <button class="sidebar-btn{% if active_view != 'reports' %} active{% endif %}" data-view="analytics" aria-label="Analytics">
                    <span class="icon">&#128202;</span>
                    <span class="label">Analytics</span>
                </button>
                <button class="sidebar-btn{% if active_view == 'reports' %} active{% endif %}" data-view="reports" aria-label="Reports">
                    <span class="icon">&#128196;</span>
                    <span class="label">Reports</span>
                </button>
                <button class="sidebar-btn{% if active_view == 'compare' %} active{% endif %}" data-view="compare" aria-label="Compare">
                    <span class="icon">&#128200;</span>
                    <span class="label">Compare</span>
                </button>
            </aside>
            <div class="main-shell">
                <header>
                    <div class="headline">
                        <h1>Service Performance Metric</h1>
                        <span class="view-indicator" id="viewIndicator"></span>
                    </div>
                    <div class="controls"></div>
                </header>
                <main>
                    <section id="panel-analytics" class="panel{% if active_view != 'reports' %} active{% endif %}">
                        <div class="grid">
                            <section class="card" data-card="table">
                                <h2>Per-Version Evolution <span>(Aggregates)</span>
                                    <button class="btn btn-expand" data-target="table">Expand</button>
                                </h2>
                                <div class="chart-area">
                                    {{ version_stats_table | safe }}
                                </div>
                            </section>
                            <section class="card" data-card="box">
                                <h2>
                                    <span>Service Distribution <span>(Box Plot)</span></span>
                                    <span class="card-actions">
                                        <label for="version" style="font-weight:600;color:#4a4f57;margin-right:0.5rem;">Version</label>
                                        <select id="version" name="version" style="margin-right:0.75rem;">
                                            {% for version in versions %}
                                                <option value="{{ version }}" {% if version == selected_version %}selected{% endif %}>{{ version }}</option>
                                            {% endfor %}
                                        </select>
                                        <button class="btn btn-expand" data-target="box">Expand</button>
                                    </span>
                                </h2>
                                <div class="chart-area">
                                    <div id="boxPlot"></div>
                                    <p id="boxMessage" class="message" style="display:none;">No data available for selected version.</p>
                                </div>
                            </section>
                            <section class="card" data-card="line">
                                <h2>Average Loading Time Trend <span>(Line)</span>
                                    <button class="btn btn-expand" data-target="line">Expand</button>
                                </h2>
                                <div class="chart-area">
                                    {{ line_plot | safe }}
                                </div>
                            </section>
                            <section class="card" data-card="bar">
                                <h2>
                                    <span>Average Loading Time <span>(Grouped Bar)</span></span>
                                    <span class="card-actions">
                                        {% if datasets %}
                                        <label for="dataset" style="font-weight:600;color:#4a4f57;margin-right:0.5rem;">Dataset</label>
                                        <select id="dataset" name="dataset" style="margin-right:0.75rem;">
                                            {% for ds in datasets %}
                                                <option value="{{ ds }}" {% if ds == selected_dataset %}selected{% endif %}>{{ ds }}</option>
                                            {% endfor %}
                                        </select>
                                        {% endif %}
                                        <button class="btn btn-expand" data-target="bar">Expand</button>
                                    </span>
                                </h2>
                                <div class="chart-area">
                                    {{ bar_plot | safe }}
                                </div>
                            </section>
                        </div>
                    </section>
                    <section id="panel-reports" class="panel{% if active_view == 'reports' %} active{% endif %}">
                        <div class="reports-layout">
                            <div class="reports-list">
                                <h2>CSV Reports</h2>
                                {% if report_files %}
                                <ul id="reportList">
                                    {% for f in report_files %}
                                        <li><button type="button" class="report-link" data-file="{{ f }}">{{ f }}</button></li>
                                    {% endfor %}
                                </ul>
                                {% else %}
                                <p class="message">No CSV files found for this dataset.</p>
                                {% endif %}
                            </div>
                            <div class="reports-viewer">
                                <h2 id="reportTitle">Preview{% if selected_dataset %} <small>{{ selected_dataset }}</small>{% endif %}</h2>
                                <div id="reportContent">
                                    <p class="message">Select a CSV to preview.</p>
                                </div>
                            </div>
                        </div>
                    </section>
                    <section id="panel-compare" class="panel{% if active_view == 'compare' %} active{% endif %}">
                        <div class="compare-card">
                            <div class="compare-header">
                                <h2>Version Comparison</h2>
                                {% if versions %}
                                <div class="compare-controls">
                                    <label for="compareVersionA">Version A</label>
                                    <select id="compareVersionA" name="compareA">
                                        {% for ver in versions %}
                                            <option value="{{ ver }}" {% if ver == compare_default_a %}selected{% endif %}>{{ ver }}</option>
                                        {% endfor %}
                                    </select>
                                    <label for="compareVersionB">Version B</label>
                                    <select id="compareVersionB" name="compareB">
                                        {% for ver in versions %}
                                            <option value="{{ ver }}" {% if ver == compare_default_b %}selected{% endif %}>{{ ver }}</option>
                                        {% endfor %}
                                    </select>
                                </div>
                                {% endif %}
                            </div>
                            <div class="compare-table-wrapper">
                                <table id="compareTable">
                                    <thead>
                                        <tr>
                                            <th>Service</th>
                                            <th id="compareColA">Version A</th>
                                            <th id="compareColB">Version B</th>
                                            <th>Change</th>
                                        </tr>
                                    </thead>
                                    <tbody id="compareTableBody">
                                        <tr>
                                            <td colspan="4" class="message">No comparison data available.</td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </section>
                </main>
            </div>
        </div>
        <div class="overlay" id="overlay" style="display:none;">
            <div class="overlay-backdrop"></div>
            <div class="overlay-content">
                <div class="overlay-header">
                    <h3 id="overlayTitle"></h3>
                    <button class="btn btn-close" id="overlayClose">Close</button>
                </div>
                <div class="overlay-body" id="overlayBody"></div>
            </div>
        </div>


        <script>
(() => {
  const boxFigures = {{ box_figures | tojson }};
  const versionsList = {{ versions | tojson }};
  const lineFigure = {{ line_fig | tojson }};
  let currentBarFigure = {{ bar_fig | tojson }};
  const versionStatsHTML = {{ version_stats_table | tojson }};
  const initialVersion = "{{ selected_version }}";
  const barDataEndpoint = "{{ bar_data_endpoint }}";
  const barAlerts = {{ bar_alerts | tojson }};
  const csvApiEndpoint = "{{ csv_api_endpoint }}";
  const initialView = "{{ active_view }}";
  const initialDataset = "{{ selected_dataset }}";
  const initialReport = "{{ initial_report }}";
  const reportFiles = {{ report_files | tojson }};
  const compareData = {{ compare_data | tojson }};
  const compareServices = {{ compare_services | tojson }};
  const compareDefaultA = "{{ compare_default_a }}";
  const compareDefaultB = "{{ compare_default_b }}";

  const versionSelect = document.getElementById("version");
  const datasetSelect = document.getElementById("dataset");
  const sidebarButtons = Array.from(document.querySelectorAll(".sidebar-btn"));
  const panels = {
    analytics: document.getElementById("panel-analytics"),
    reports: document.getElementById("panel-reports"),
    compare: document.getElementById("panel-compare"),
  };
  const viewIndicator = document.getElementById("viewIndicator");
  const reportList = document.getElementById("reportList");
  const reportContent = document.getElementById("reportContent");
  const reportTitle = document.getElementById("reportTitle");
  const overlay = document.getElementById("overlay");
  const overlayBody = document.getElementById("overlayBody");
  const overlayTitle = document.getElementById("overlayTitle");
  const overlayClose = document.getElementById("overlayClose");
  const overlayBackdrop = overlay ? overlay.querySelector(".overlay-backdrop") : null;
  const comparePanel = document.getElementById("panel-compare");
  const compareVersionASelect = document.getElementById("compareVersionA");
  const compareVersionBSelect = document.getElementById("compareVersionB");
  const compareTableBody = document.getElementById("compareTableBody");
  const compareColA = document.getElementById("compareColA");
  const compareColB = document.getElementById("compareColB");

  let currentView = initialView === "reports" || initialView === "compare" ? initialView : "analytics";
  let currentBarDataset = initialDataset || (datasetSelect ? datasetSelect.value : "");
  let reportViewerLoaded = false;
  let activeReportFile = initialReport || "";
  let overlayVersionSelect = null;
  let overlayBoxContainer = null;
  let overlayDatasetSelect = null;

  if (Array.isArray(barAlerts) && barAlerts.length) {
    barAlerts.forEach((msg) => alert(msg));
  }

  function cloneFigure(fig) {
    if (!fig) {
      return null;
    }
    return JSON.parse(JSON.stringify(fig));
  }

  function applyLayoutTweaks(fig) {
    if (!fig || !fig.layout) {
      return fig;
    }
    const layout = Object.assign({}, fig.layout);
    layout.autosize = true;
    layout.margin = Object.assign({ l: 40, r: 20, t: 55, b: 50 }, layout.margin || {});
    return Object.assign({}, fig, { layout });
  }

  function renderResponsivePlot(container, fig) {
    if (!container) {
      return false;
    }
    if (!fig || !fig.data || !fig.data.length) {
      Plotly.purge(container);
      return false;
    }
    const plotFig = applyLayoutTweaks(cloneFigure(fig));
    Plotly.newPlot(container, plotFig.data, plotFig.layout, { responsive: true, displaylogo: false });
    setTimeout(() => Plotly.Plots.resize(container), 0);
    return true;
  }

  function renderBoxFigure(version) {
    const boxDiv = document.getElementById("boxPlot");
    const message = document.getElementById("boxMessage");
    const fig = cloneFigure(boxFigures[version] || null);
    if (!boxDiv || !message) {
      return;
    }
    if (!fig || !fig.data || !fig.data.length) {
      Plotly.purge(boxDiv);
      message.style.display = "block";
      return;
    }
    message.style.display = "none";
    renderResponsivePlot(boxDiv, fig);
  }

  function setActiveReportButton(file) {
    if (!reportList) {
      return;
    }
    Array.from(reportList.querySelectorAll(".report-link")).forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.file === file);
    });
  }

  function showReportMessage(message, type = "info") {
    if (!reportContent) {
      return;
    }
    const p = document.createElement("p");
    p.className = type === "error" ? "message error" : "message";
    p.textContent = message;
    reportContent.innerHTML = "";
    reportContent.appendChild(p);
  }

  function updateReportTitle(file) {
    if (!reportTitle) {
      return;
    }
    const datasetLabel = (datasetSelect && datasetSelect.value) || initialDataset || "default";
    if (file) {
      reportTitle.innerHTML = `Preview <small>${datasetLabel} ? ${file}</small>`;
    } else if (datasetLabel) {
      reportTitle.innerHTML = `Preview <small>${datasetLabel}</small>`;
    } else {
      reportTitle.textContent = "Preview";
    }
  }

  function renderReportTable(headers, rows) {
    if (!reportContent) {
      return;
    }
    if (!headers || !headers.length) {
      showReportMessage("No data available in this CSV.");
      return;
    }
    const table = document.createElement("table");
    const thead = document.createElement("thead");
    const headRow = document.createElement("tr");
    headers.forEach((head) => {
      const th = document.createElement("th");
      th.textContent = head;
      headRow.appendChild(th);
    });
    thead.appendChild(headRow);
    table.appendChild(thead);
    const tbody = document.createElement("tbody");
    if (rows && rows.length) {
      rows.forEach((row) => {
        const tr = document.createElement("tr");
        row.forEach((cell) => {
          const td = document.createElement("td");
          td.textContent = cell;
          tr.appendChild(td);
        });
        tbody.appendChild(tr);
      });
    } else {
      const tr = document.createElement("tr");
      const td = document.createElement("td");
      td.colSpan = headers.length;
      td.textContent = "No data rows";
      tr.appendChild(td);
      tbody.appendChild(tr);
    }
    table.appendChild(tbody);
    reportContent.innerHTML = "";
    reportContent.appendChild(table);
  }

  function getCompareValue(service, version) {
    if (!compareData || !service || !version) {
      return null;
    }
    const svcRow = compareData[service];
    if (!svcRow) {
      return null;
    }
    const val = svcRow[version];
    return typeof val === "number" ? val : null;
  }

  function formatMs(value) {
    if (value === null || value === undefined) {
      return "?";
    }
    return `${value.toFixed(1)} ms`;
  }

  function formatDiff(valueA, valueB) {
    if (valueA === null || valueB === null) {
      return { text: "?", cls: "diff-neutral" };
    }
    if (valueA === 0) {
      return { text: "N/A", cls: "diff-neutral" };
    }
    const pct = ((valueB - valueA) / valueA) * 100;
    const text = `${pct >= 0 ? "+" : ""}${pct.toFixed(1)}%`;
    let cls = "diff-neutral";
    if (pct > 0.5) {
      cls = "diff-negative";
    } else if (pct < -0.5) {
      cls = "diff-positive";
    }
    return { text, cls };
  }

  function updateCompareTable() {
    if (!compareTableBody) {
      return;
    }
    const versionA = compareVersionASelect ? compareVersionASelect.value : compareDefaultA;
    const versionB = compareVersionBSelect ? compareVersionBSelect.value : compareDefaultB;
    if (compareColA) {
      compareColA.textContent = versionA ? `${versionA} (avg ms)` : "Version A";
    }
    if (compareColB) {
      compareColB.textContent = versionB ? `${versionB} (avg ms)` : "Version B";
    }

    compareTableBody.innerHTML = "";
    if (!compareServices.length || !versionA || !versionB) {
      const row = document.createElement("tr");
      const cell = document.createElement("td");
      cell.textContent = "No comparison data available.";
      cell.colSpan = 4;
      cell.className = "message";
      row.appendChild(cell);
      compareTableBody.appendChild(row);
      return;
    }

    compareServices.forEach((service) => {
      const row = document.createElement("tr");
      const cellService = document.createElement("td");
      cellService.textContent = service;
      row.appendChild(cellService);

      const valueA = getCompareValue(service, versionA);
      const valueB = getCompareValue(service, versionB);

      const cellA = document.createElement("td");
      cellA.className = "value";
      cellA.textContent = formatMs(valueA);
      row.appendChild(cellA);

      const cellB = document.createElement("td");
      cellB.className = "value";
      cellB.textContent = formatMs(valueB);
      row.appendChild(cellB);

      const diffCell = document.createElement("td");
      diffCell.classList.add("value");
      const diff = formatDiff(valueA, valueB);
      diffCell.textContent = diff.text;
      diffCell.classList.add(diff.cls || "diff-neutral");
      row.appendChild(diffCell);

      compareTableBody.appendChild(row);
    });

    if (currentView === "compare") {
      const url = new URL(window.location.href);
      if (versionA) {
        url.searchParams.set("compareA", versionA);
      } else {
        url.searchParams.delete("compareA");
      }
      if (versionB) {
        url.searchParams.set("compareB", versionB);
      } else {
        url.searchParams.delete("compareB");
      }
      window.history.replaceState(null, "", url);
    }
  }

  function loadReport(file) {
    if (!file) {
      showReportMessage("Select a CSV to preview.");
      updateReportTitle("");
      return;
    }
    setActiveReportButton(file);
    activeReportFile = file;
    showReportMessage("Loading report...");
    const params = new URLSearchParams();
    params.set("file", file);
    const currentDatasetValue = datasetSelect ? datasetSelect.value : initialDataset;
    if (currentDatasetValue) {
      params.set("dataset", currentDatasetValue);
    }
    fetch(`${csvApiEndpoint}?${params.toString()}`)
      .then((resp) => {
        if (!resp.ok) {
          throw new Error("Failed to load CSV file");
        }
        return resp.json();
      })
      .then((payload) => {
        reportViewerLoaded = true;
        updateReportTitle(file);
        renderReportTable(payload.headers || [], payload.rows || []);
        const url = new URL(window.location.href);
        url.searchParams.set("report", file);
        url.searchParams.set("view", currentView);
        window.history.replaceState(null, "", url);
      })
      .catch((err) => {
        console.error(err);
        reportViewerLoaded = false;
        showReportMessage("Unable to load CSV content.", "error");
      });
  }

  function updateView(view) {
    let targetView = "analytics";
    if (view === "reports" && panels.reports) {
      targetView = "reports";
    } else if (view === "compare" && panels.compare) {
      targetView = "compare";
    }
    currentView = targetView;

    Object.entries(panels).forEach(([key, panel]) => {
      if (panel) {
        panel.classList.toggle("active", key === targetView);
      }
    });

    sidebarButtons.forEach((btn) => {
      const isActive = btn.dataset.view === targetView;
      btn.classList.toggle("active", isActive);
      btn.setAttribute("aria-current", isActive ? "page" : "false");
    });

    if (viewIndicator) {
      viewIndicator.textContent =
        targetView === "analytics"
          ? "Analytics Dashboard"
          : targetView === "reports"
            ? "CSV Reports"
            : "Version Comparison";
    }

    const url = new URL(window.location.href);
    url.searchParams.set("view", targetView);
    window.history.replaceState(null, "", url);

    if (targetView === "reports") {
      if (!reportViewerLoaded) {
        if (activeReportFile) {
          loadReport(activeReportFile);
        } else if (initialReport) {
          loadReport(initialReport);
        } else if (reportFiles.length) {
          loadReport(reportFiles[0]);
        } else {
          showReportMessage("No CSV files found for this dataset.");
        }
      }
    } else if (targetView === "compare") {
      updateCompareTable();
    }
  }

  function closeOverlay() {
    if (!overlay) {
      return;
    }
    overlay.style.display = "none";
    overlayBody.innerHTML = "";
    overlayVersionSelect = null;
    overlayBoxContainer = null;
    overlayDatasetSelect = null;
  }

  function openOverlay(target) {
    if (!overlay) {
      return;
    }
    overlayBody.innerHTML = "";
    overlayVersionSelect = null;
    overlayBoxContainer = null;
    overlayDatasetSelect = null;

    if (target === "table") {
      overlayTitle.textContent = "Per-Version Evolution (Aggregates)";
      const tableWrapper = document.createElement("div");
      tableWrapper.innerHTML = versionStatsHTML;
      overlayBody.appendChild(tableWrapper);
    } else if (target === "box") {
      overlayTitle.textContent = "Service Distribution (Box Plot)";
      const controls = document.createElement("div");
      controls.className = "overlay-controls";
      const overlayLabel = document.createElement("label");
      overlayLabel.setAttribute("for", "overlay-version");
      overlayLabel.textContent = "Version";
      const overlaySelect = document.createElement("select");
      overlaySelect.id = "overlay-version";
      versionsList.forEach((ver) => {
        const opt = document.createElement("option");
        opt.value = ver;
        opt.textContent = ver;
        overlaySelect.appendChild(opt);
      });
      if (versionSelect) {
        overlaySelect.value = versionSelect.value;
      }
      controls.appendChild(overlayLabel);
      controls.appendChild(overlaySelect);
      overlayBody.appendChild(controls);
      const boxContainer = document.createElement("div");
      boxContainer.className = "plot-container";
      overlayBody.appendChild(boxContainer);
      const currentVersion = (versionSelect && versionSelect.value) || versionsList[0];
      renderResponsivePlot(boxContainer, boxFigures[currentVersion]);
      overlayVersionSelect = overlaySelect;
      overlayBoxContainer = boxContainer;
      overlaySelect.addEventListener("change", (ev) => {
        const chosen = ev.target.value;
        if (versionSelect && versionSelect.value !== chosen) {
          versionSelect.value = chosen;
          versionSelect.dispatchEvent(new Event("change"));
        } else {
          renderBoxFigure(chosen);
          renderResponsivePlot(boxContainer, boxFigures[chosen]);
        }
      });
    } else if (target === "line") {
      overlayTitle.textContent = "Average Loading Time Trend (Line)";
      const lineContainer = document.createElement("div");
      lineContainer.className = "plot-container";
      overlayBody.appendChild(lineContainer);
      if (lineFigure && lineFigure.data) {
        renderResponsivePlot(lineContainer, lineFigure);
      }
    } else if (target === "bar") {
      overlayTitle.textContent = "Average Loading Time (Grouped Bar)";
      const barContainer = document.createElement("div");
      barContainer.className = "plot-container";
      if (datasetSelect) {
        const controls = document.createElement("div");
        controls.className = "overlay-controls";
        const dsLabel = document.createElement("label");
        dsLabel.setAttribute("for", "overlay-dataset");
        dsLabel.textContent = "Dataset";
        const dsSelect = datasetSelect.cloneNode(true);
        dsSelect.id = "overlay-dataset";
        dsSelect.value = currentBarDataset || (datasetSelect ? datasetSelect.value : dsSelect.value);
        controls.appendChild(dsLabel);
        controls.appendChild(dsSelect);
        overlayBody.appendChild(controls);
        overlayDatasetSelect = dsSelect;
        dsSelect.addEventListener("change", (ev) => {
          const chosen = ev.target.value;
          const params = new URLSearchParams();
          if (chosen) {
            params.set("dataset", chosen);
          }
          fetch(`${barDataEndpoint}?${params.toString()}`)
            .then((resp) => {
              if (!resp.ok) {
                throw new Error("Failed to fetch dataset bar data");
              }
              return resp.json();
            })
            .then((payload) => {
              if (Array.isArray(payload.warnings)) {
                payload.warnings.forEach((msg) => alert(msg));
              }
              if (payload.error) {
                alert(payload.error);
              }
              currentBarDataset = payload.dataset || chosen || "";
              if (dsSelect.value !== currentBarDataset) {
                dsSelect.value = currentBarDataset;
              }
              currentBarFigure = payload.figure || { data: [], layout: {} };
              if (!payload.error && currentBarFigure.data && currentBarFigure.data.length) {
                renderResponsivePlot(barContainer, currentBarFigure);
              } else {
                Plotly.purge(barContainer);
              }
            })
            .catch((err) => {
              console.error(err);
            });
        });
      }
      overlayBody.appendChild(barContainer);
      if (currentBarFigure && currentBarFigure.data) {
        renderResponsivePlot(barContainer, currentBarFigure);
      }
    }

    overlay.style.display = "flex";
  }

  Array.from(document.querySelectorAll(".btn-expand")).forEach((btn) => {
    btn.addEventListener("click", (event) => {
      event.preventDefault();
      const target = btn.getAttribute("data-target");
      openOverlay(target || "table");
    });
  });

  if (overlayClose) {
    overlayClose.addEventListener("click", () => closeOverlay());
  }
  if (overlayBackdrop) {
    overlayBackdrop.addEventListener("click", () => closeOverlay());
  }
  document.addEventListener("keydown", (ev) => {
    if (ev.key === "Escape") {
      closeOverlay();
    }
  });

  if (reportList) {
    reportList.addEventListener("click", (event) => {
      const button = event.target.closest(".report-link");
      if (!button) {
        return;
      }
      event.preventDefault();
      loadReport(button.dataset.file);
    });
  }

  if (datasetSelect) {
    datasetSelect.addEventListener("change", (ev) => {
      const dataset = ev.target.value;
      const url = new URL(window.location.href);
      if (dataset) {
        url.searchParams.set("dataset", dataset);
      } else {
        url.searchParams.delete("dataset");
      }
      url.searchParams.delete("version");
      url.searchParams.delete("report");
      url.searchParams.delete("compareA");
      url.searchParams.delete("compareB");
      url.searchParams.set("view", currentView);
      window.location.href = url.toString();
    });
  }

  if (versionSelect) {
    versionSelect.addEventListener("change", (ev) => {
      const version = ev.target.value;
      const url = new URL(window.location.href);
      url.searchParams.set("version", version);
      url.searchParams.set("view", currentView);
      window.history.replaceState(null, "", url);
      renderBoxFigure(version);
      if (overlayVersionSelect) {
        overlayVersionSelect.value = version;
      }
      if (overlayBoxContainer) {
        renderResponsivePlot(
          overlayBoxContainer,
          boxFigures[version] || { data: [], layout: {} }
        );
      }
    });
  }

  if (compareVersionASelect) {
    compareVersionASelect.addEventListener("change", () => {
      updateCompareTable();
    });
  }
  if (compareVersionBSelect) {
    compareVersionBSelect.addEventListener("change", () => {
      updateCompareTable();
    });
  }

  sidebarButtons.forEach((btn) => {
    btn.addEventListener("click", (event) => {
      event.preventDefault();
      updateView(btn.dataset.view || "analytics");
    });
  });

  const initialBoxVersion = (initialVersion && boxFigures[initialVersion])
    ? initialVersion
    : (versionsList[0] || null);
  if (compareVersionASelect && compareDefaultA) {
    compareVersionASelect.value = compareDefaultA;
  }
  if (compareVersionBSelect && compareDefaultB) {
    compareVersionBSelect.value = compareDefaultB;
  }
  if (initialBoxVersion) {
    if (versionSelect && versionSelect.value !== initialBoxVersion) {
      versionSelect.value = initialBoxVersion;
    }
    renderBoxFigure(initialBoxVersion);
  }

  updateReportTitle(activeReportFile);
  updateView(currentView);

  if (reportList && activeReportFile) {
    setActiveReportButton(activeReportFile);
  }
  if (currentView === "reports" && (activeReportFile || reportFiles.length)) {
    loadReport(activeReportFile || reportFiles[0]);
  } else if (currentView === "reports") {
    showReportMessage("No CSV files found for this dataset.");
  }
  if (currentView === "compare") {
    updateCompareTable();
  }
})();
        </script>
    </body>
    </html>
    """

    csv_api_endpoint = url_for("api_csv")

    return render_template_string(
        template,
        active_view=view_mode,
        datasets=dataset_options,
        selected_dataset=selected_dataset,
        version_stats_table=version_stats_html,
        line_plot=line_html,
        bar_plot=bar_html,
        line_fig=line_fig_payload,
        bar_fig=bar_fig_payload,
        versions=dropdown_versions,
        selected_version=selected_version,
        box_figures=box_figures,
        bar_data_endpoint=url_for("analytics_bardata"),
        bar_alerts=bar_alerts,
        report_files=report_files,
        initial_report=initial_report,
        csv_api_endpoint=csv_api_endpoint,
        compare_services=compare_services,
        compare_data=compare_data,
        compare_default_a=compare_version_a,
        compare_default_b=compare_version_b,
    )


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
