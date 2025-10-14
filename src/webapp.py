from __future__ import annotations

import csv
import json
import os
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd
import plotly.graph_objects as go
from plotly.io import to_html
from flask import Flask, abort, render_template_string, request, send_file, url_for


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


def _safe_resolve(rel_path: str) -> Path:
    try:
        candidate = (RESULT_DIR / rel_path).resolve(strict=True)
    except FileNotFoundError as exc:
        raise FileNotFoundError from exc

    if RESULT_DIR not in candidate.parents and candidate != RESULT_DIR:
        raise FileNotFoundError("Path outside of result directory")
    if not candidate.is_file():
        raise FileNotFoundError("Not a file")
    if candidate.suffix.lower() != ".csv":
        raise FileNotFoundError("Not a CSV file")
    return candidate


@app.route("/")
def index() -> str:
    csv_files = _list_csv_files()
    files = [f.relative_to(RESULT_DIR).as_posix() for f in csv_files]
    has_summary = SUMMARY_FILE.exists()

    template = """
    <!doctype html>
    <html lang="en">
    <head>
        <meta charset="utf-8" />
        <title>CSV Browser</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 2rem; }
            h1 { margin-bottom: 1rem; }
            ul { list-style: none; padding: 0; }
            li { margin-bottom: 0.5rem; }
            a { text-decoration: none; color: #1a73e8; }
            a:hover { text-decoration: underline; }
            .empty { color: #666; }
        </style>
    </head>
    <body>
        <h1>Available CSV Reports</h1>
        <p>
            <a href="{{ url_for('analytics') }}" {% if not has_summary %}class="disabled" title="summary.csv not found"{% endif %}>Analytics Dashboard</a>
        </p>
        {% if files %}
        <ul>
        {% for f in files %}
            <li><a href="{{ url_for('view_csv', file=f) }}">{{ f }}</a></li>
        {% endfor %}
        </ul>
        {% else %}
            <p class="empty">No CSV files found under {{ result_dir }}</p>
        {% endif %}
    </body>
    </html>
    """
    return render_template_string(template, files=files, result_dir=RESULT_DIR, has_summary=has_summary)


@app.route("/view")
def view_csv() -> str:
    rel_path = request.args.get("file")
    if not rel_path:
        abort(400, "Missing 'file' query parameter")

    try:
        target = _safe_resolve(rel_path)
    except FileNotFoundError:
        abort(404, "CSV not found")

    rows: List[List[str]] = []
    try:
        with target.open("r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            for row in reader:
                rows.append(row)
    except UnicodeDecodeError:
        with target.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f)
            for row in reader:
                rows.append(row)

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

    service_order = df["service"].dropna().drop_duplicates().tolist()
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


@app.route("/analytics")
def analytics() -> str:
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

        fig_bar = go.Figure()
        for version in version_cols:
            if version in wide.columns and not wide[version].dropna().empty:
                values = wide[version].tolist()
                max_val = max([v for v in values if pd.notna(v)], default=0)
                fig_bar.add_trace(
                    go.Bar(
                        x=wide.index.tolist(),
                        y=values,
                        name=version,
                        text=[f"{v:.0f}" if pd.notna(v) else "" for v in values],
                        textposition="outside",
                    )
                )
        y_max = wide.max().max()
        y_buffer = y_max * 0.1 if y_max else 0
        fig_bar.update_yaxes(range=[0, y_max + y_buffer])
        fig_bar.update_layout(
            title="Average Loading Time per Service (Grouped Bar)",
            xaxis_title="Service",
            yaxis_title="Average Loading Time (ms)",
            margin=dict(l=30, r=20, t=60, b=80),
            barmode="group",
            legend_title="Version",
        )
        bar_html = to_html(fig_bar, include_plotlyjs=False, full_html=False)
        bar_fig_payload = json.loads(fig_bar.to_json())

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
            }
            a {
                color: #1a73e8;
                text-decoration: none;
            }
            a:hover { text-decoration: underline; }

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
                padding: 1.5rem 2rem 2rem;
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
                .overlay-content {
                    width: 98vw;
                    height: 94vh;
                }
            }
        </style>
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    </head>
    <body>
        <header>
            <div class="headline">
                <a href="{{ url_for('index') }}">&#8592; Back</a>
                <h1>Analytics Dashboard</h1>
            </div>
            <div class="controls"></div>
        </header>
        <main>
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
        </main>
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
            const boxFigures = {{ box_figures | tojson }};
            const versionsList = {{ versions | tojson }};
            const lineFigure = {{ line_fig | tojson }};
            const barFigure = {{ bar_fig | tojson }};
            const versionStatsHTML = {{ version_stats_table | tojson }};
            const initialVersion = "{{ selected_version }}";

            const datasetSelect = document.getElementById("dataset");
            if (datasetSelect) {
                datasetSelect.addEventListener("change", function (ev) {
                    const dataset = ev.target.value;
                    const url = new URL(window.location.href);
                    if (dataset) {
                        url.searchParams.set("dataset", dataset);
                    } else {
                        url.searchParams.delete("dataset");
                    }
                    url.searchParams.delete("version");
                    window.location.href = url.toString();
                });
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
                layout.margin = Object.assign({l: 40, r: 20, t: 55, b: 50}, layout.margin || {});
                return Object.assign({}, fig, { layout });
            }

            function renderResponsivePlot(container, fig) {
                if (!fig || !fig.data || fig.data.length === 0) {
                    Plotly.purge(container);
                    return false;
                }
                const plotFig = applyLayoutTweaks(cloneFigure(fig));
                Plotly.newPlot(container, plotFig.data, plotFig.layout, {responsive: true, displaylogo: false});
                setTimeout(() => Plotly.Plots.resize(container), 0);
                return true;
            }

            function renderBox(fig) {
                const boxDiv = document.getElementById("boxPlot");
                const message = document.getElementById("boxMessage");
                if (!fig || !fig.data || fig.data.length === 0) {
                    Plotly.purge(boxDiv);
                    message.style.display = "block";
                    return;
                }
                message.style.display = "none";
                renderResponsivePlot(boxDiv, fig);
            }

            renderBox(cloneFigure(boxFigures[initialVersion]));

            const versionSelect = document.getElementById("version");
            let overlayVersionSelect = null;
            let overlayBoxContainer = null;

            versionSelect.addEventListener("change", function (ev) {
                const version = ev.target.value;
                const url = new URL(window.location.href);
                url.searchParams.set("version", version);
                window.history.replaceState(null, "", url);
                renderBox(cloneFigure(boxFigures[version]));
                if (overlayVersionSelect) {
                    overlayVersionSelect.value = version;
                }
                if (overlayBoxContainer) {
                    renderResponsivePlot(overlayBoxContainer, boxFigures[version]);
                }
            });

            const overlay = document.getElementById("overlay");
            const overlayBody = document.getElementById("overlayBody");
            const overlayTitle = document.getElementById("overlayTitle");
            const overlayClose = document.getElementById("overlayClose");

            function openOverlay(target) {
                overlayBody.innerHTML = "";
                overlayVersionSelect = null;
                overlayBoxContainer = null;
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
                    const mainSelect = document.getElementById("version");
                    if (mainSelect) {
                        overlaySelect.value = mainSelect.value;
                    }
                    controls.appendChild(overlayLabel);
                    controls.appendChild(overlaySelect);
                    overlayBody.appendChild(controls);

                    const boxContainer = document.createElement("div");
                    boxContainer.className = "plot-container";
                    overlayBody.appendChild(boxContainer);
                    const currentVersion = document.getElementById("version").value;
                    const fig = cloneFigure(boxFigures[currentVersion]);
                    renderResponsivePlot(boxContainer, fig);

                    overlayVersionSelect = overlaySelect;
                    overlayBoxContainer = boxContainer;

                    overlaySelect.addEventListener("change", (ev) => {
                        const chosen = ev.target.value;
                        if (mainSelect && mainSelect.value !== chosen) {
                            mainSelect.value = chosen;
                            mainSelect.dispatchEvent(new Event("change"));
                        } else {
                            renderBox(cloneFigure(boxFigures[chosen]));
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
                    overlayBody.appendChild(barContainer);
                    if (barFigure && barFigure.data) {
                        renderResponsivePlot(barContainer, barFigure);
                    }
                }
                overlay.style.display = "flex";
            }

            function closeOverlay() {
                overlay.style.display = "none";
                overlayBody.innerHTML = "";
                overlayVersionSelect = null;
                overlayBoxContainer = null;
            }

            document.querySelectorAll(".btn-expand").forEach((btn) => {
                btn.addEventListener("click", (ev) => {
                    const target = ev.currentTarget.getAttribute("data-target");
                    openOverlay(target);
                });
            });

            overlayClose.addEventListener("click", closeOverlay);
            overlay.querySelector(".overlay-backdrop").addEventListener("click", closeOverlay);
        </script>
    </body>
    </html>
    """

    return render_template_string(
        template,
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
    )


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8000)
