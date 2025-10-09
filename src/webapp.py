from __future__ import annotations

import csv
from pathlib import Path
from typing import List

from flask import Flask, abort, render_template_string, request, send_file, url_for


app = Flask(__name__)

# Base directory that holds generated CSV outputs
RESULT_DIR = Path(__file__).resolve().parent.parent / "result"


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
    return render_template_string(template, files=files, result_dir=RESULT_DIR)


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


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8000)
