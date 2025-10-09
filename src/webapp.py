from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.io import to_html
from flask import Flask, abort, render_template_string, request, send_file, url_for


app = Flask(__name__)

# Base directory that holds generated CSV outputs
RESULT_DIR = Path(__file__).resolve().parent.parent / "result"
SUMMARY_FILE = RESULT_DIR / "summary.csv"


def _list_csv_files() -> List[Path]:
    if not RESULT_DIR.exists():
        return []
    return sorted(p for p in RESULT_DIR.rglob("*.csv") if p.is_file())


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


def _load_summary() -> Tuple[pd.DataFrame, List[str]]:
    if not SUMMARY_FILE.exists():
        raise FileNotFoundError("summary.csv not found. Generate it with extract.py --combine")

    df = pd.read_csv(SUMMARY_FILE)
    if "service" not in df.columns:
        raise ValueError("summary.csv must contain a 'service' column")

    numeric_cols = [c for c in df.columns if c != "service"]
    if not numeric_cols:
        raise ValueError("summary.csv must contain at least one version column")

    df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors="coerce")
    return df, numeric_cols


def _prepare_summary() -> Tuple[pd.DataFrame, List[str], pd.DataFrame, List[str]]:
    df, version_cols = _load_summary()

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


def _build_box_figure(melted: pd.DataFrame, version: str):
    box_data = melted[melted["version"] == version]
    if box_data.empty:
        return None

    fig_box = px.box(
        box_data,
        x="service",
        y="loading_time",
        points="all",
        labels={"service": "Service", "loading_time": "Loading Time (ms)"},
        title=f"Service Loading Time Distribution ({version})",
    )
    fig_box.update_traces(boxmean=True)
    fig_box.update_layout(margin=dict(l=30, r=20, t=60, b=80))
    return fig_box


@app.route("/analytics")
def analytics() -> str:
    try:
        df, version_cols, melted, service_order = _prepare_summary()
    except (FileNotFoundError, ValueError) as exc:
        abort(404, str(exc))

    selected_version = request.args.get("version")
    if not selected_version or selected_version not in version_cols:
        selected_version = version_cols[0]

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
    for ver in version_cols:
        fig = _build_box_figure(melted, ver)
        box_figures[ver] = json.loads(fig.to_json()) if fig else {"data": [], "layout": {}}
    box_fig_dict = box_figures.get(selected_version)

    # Average time per service line chart (all versions)
    service_avg_multi = (
        melted.groupby(["service", "version"])["loading_time"].mean().reset_index()
    )
    if service_order:
        service_avg_multi["service"] = pd.Categorical(
            service_avg_multi["service"], categories=service_order, ordered=True
        )
        service_avg_multi = service_avg_multi.sort_values("service")

    line_html = "<p>No data available for line chart.</p>"
    if not service_avg_multi.empty:
        wide = service_avg_multi.pivot(index="service", columns="version", values="loading_time")
        if service_order:
            wide = wide.reindex(service_order)
        wide = wide.dropna(how="all")
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

    template = """
    <!doctype html>
    <html lang="en">
    <head>
        <meta charset="utf-8" />
        <title>Analytics Dashboard</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 2rem; }
            h1 { margin-bottom: 0.5rem; }
            .toolbar { margin-bottom: 1.5rem; }
            a { text-decoration: none; color: #1a73e8; }
            a:hover { text-decoration: underline; }
            .table { border-collapse: collapse; width: auto; margin-bottom: 2rem; }
            .table th, .table td { border: 1px solid #ccc; padding: 0.5rem 0.75rem; text-align: right; }
            .table th:first-child, .table td:first-child { text-align: left; }
            .chart { margin-bottom: 2.5rem; }
            form.filter { margin-bottom: 1rem; }
            select { padding: 0.25rem 0.5rem; }
            .message { color: #666; }
        </style>
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    </head>
    <body>
        <div class="toolbar"><a href="{{ url_for('index') }}">&#8592; Back</a></div>
        <h1>Analytics</h1>
        <section>
            <h2>Per-Version Evolution (Pandas)</h2>
            {{ version_stats_table | safe }}
        </section>
        <section class="chart">
            <h2>Service Distribution (Box Plot)</h2>
            <form class="filter">
                <label for="version">Version:
                    <select id="version" name="version">
                        {% for version in versions %}
                            <option value="{{ version }}" {% if version == selected_version %}selected{% endif %}>{{ version }}</option>
                        {% endfor %}
                    </select>
                </label>
            </form>
            <div id="boxPlot"></div>
            <p id="boxMessage" class="message" style="display:none;">No data available for selected version.</p>
        </section>
        <section class="chart">
            <h2>Average Loading Time per Service</h2>
            {{ line_plot | safe }}
        </section>
        <script>
            const boxFigures = {{ box_figures | tojson }};
            const initialVersion = "{{ selected_version }}";

            function cloneFigure(fig) {
                if (!fig) {
                    return null;
                }
                return JSON.parse(JSON.stringify(fig));
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
                Plotly.newPlot(boxDiv, fig.data, fig.layout, {responsive: true});
            }

            renderBox(cloneFigure(boxFigures[initialVersion]));

            const versionSelect = document.getElementById("version");
            const form = document.querySelector("form.filter");
            if (form) {
                form.addEventListener("submit", function (ev) { ev.preventDefault(); });
            }

            function updateUrl(version) {
                const url = new URL(window.location.href);
                url.searchParams.set("version", version);
                window.history.replaceState(null, "", url);
            }

            versionSelect.addEventListener("change", function (ev) {
                const version = ev.target.value;
                updateUrl(version);
                renderBox(cloneFigure(boxFigures[version]));
            });
        </script>
    </body>
    </html>
    """

    return render_template_string(
        template,
        version_stats_table=version_stats_html,
        line_plot=line_html,
        versions=version_cols,
        selected_version=selected_version,
        box_figures=box_figures,
    )


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8000)
