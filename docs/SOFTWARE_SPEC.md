# Service Performance Metric — Software Specification

## 1. Purpose

Define the current, working behavior of Service Performance Metric based on the existing implementation and UI. This document is used for team alignment, QA acceptance, and future extension.

## 2. Product Overview

- Goal: Parse service performance logs into normalized CSVs, compute per-version statistics, and offer a browser UI for analytics, CSV browsing, and version comparison.
- Users: QA/test engineers, developers, project managers.
- Outcomes:
  - Batch-parse raw logs into per-version `summary.csv` files.
  - Combine multi-version data into a unified `summary.csv` for charts.
  - Generate `summary_stats.csv` (overall) and `service_stats.csv` (per service) for visualization.
  - Provide an interactive web UI with charts, CSV previews, and comparison tables.

## 3. System Architecture

- Backend: Flask app serving HTML and JSON APIs.
- Frontend: React UMD + htm templating, Tailwind CSS, Plotly charts.
- CLI: `spm.py` orchestrates clean/generate/serve/merge workflows.
- Processing pipeline:
  1) Extract raw entries from logs → `service, loading_time_ms`
  2) Combine per-version summaries into a unified table
  3) Compute overall/per-service stats for charts and tables

## 4. Directory Layout (Relevant)

- `data/` raw input root (configurable)
  - `data/<version>/PerformanceLog/*.log | *loading.log`
- `result/<data-folder>/` generated outputs
  - `InQuire_*/summary.csv` per version (raw rows)
  - `summary.csv` combined across versions (same service may span multiple rows)
  - `summary_stats.csv` overall stats per version
  - `service_stats.csv` per-service stats per version
- `src/extract.py` log parser → per-version `summary.csv`
- `src/report.py` stats generator → `summary_stats.csv`/`service_stats.csv`
- `src/webapp.py` Flask web app & JSON endpoints
- `templates/index.html` root HTML skeleton
- `static/js/app.js` SPA logic & UI

## 5. Installation & Execution

1) Install Python dependencies

```
pip install -r requirements.txt
```

2) Optional: merge multiple data folders

```
python spm.py merge data1 data2 data3 --into data
```

3) Generate reports

```
python spm.py generate            # defaults to data/
python spm.py generate --data data2
```

4) Serve the web UI (builds unless `--no-build`)

```
python spm.py serve               # http://localhost:8000/
python spm.py serve --data data2  # or positional: python spm.py serve data2
python spm.py serve --no-build    # skip rebuild when result exists
```

Environment variables (normally set by `spm.py serve`):

- `SPM_RESULT_ROOT`: dataset root (default `result/<data-folder>`)
- `SPM_RESULT_BASE`: base directory that contains datasets (default `result/`)
- `SPM_DEFAULT_DATASET`: default dataset name (optional)

## 6. Data Model & File Formats

### 6.1 Dataset

A Dataset is the input root used for processing. It must satisfy both of the following:

- It contains three version subdirectories under the dataset root (for example: `<root>/<versionA>`, `<root>/<versionB>`, `<root>/<versionC>`).
- Each version subdirectory contains at least one `PerformanceLog` directory.

### 6.2 Input Logs

- Location: `data/<version>/PerformanceLog/`
- Preferred file pattern: `*loading.log` (fallback to `*.log`)
- Parsing rule (case-insensitive):

```
^HH:MM:SS.mmm\s+(SERVICE_NAME)\s+-\s+(loading_time|elapsed):\s+(NUMBER)\s+ms
```

### 6.3 Per-Version Summary (raw) — `InQuire_*/summary.csv`

```
service,loading_time_ms
Service A,1234
Service B,845
Service A,1100
...
```

### 6.4 Combined Summary — `summary.csv`

- Columns: `service,<version1>,<version2>,...`
- Rows: same service can appear across multiple rows to preserve multiple samples per version (blank where no sample at that row index).

Example:

```
service,2.0.1.0,2.0.1.2,2.0.1.3
Service A,1234,1190,1105
Service A,1080,,1098
Service B,845,860,
...
```

### 6.5 Overall Stats — `summary_stats.csv`

```
metric,2.0.1.0,2.0.1.2,2.0.1.3
Average,1040,1005,980
Max,2500,2400,2100
Min,300,320,310
Median,990,980,950
```

### 6.6 Per-Service Stats — `service_stats.csv`

```
service,2.0.1.0_avg,2.0.1.0_max,2.0.1.0_min,2.0.1.0_median,2.0.1.2_avg,...
Service A,1105,2500,400,1088,1075,...
Service B,900,1950,350,870,905,...
...
```

### 6.7 Exclusions

The following service names are excluded from analytics and stats:

```
EIP2, EIP 2, Microsoft 365, MICROSOFT 365, OUTLOOK, Outlook
```

## 7. CLI Specification

### 7.1 `clean`

```
python spm.py clean [--result <path>]  # default: result/
```

Removes the entire result directory.

### 7.2 `generate`

```
python spm.py generate [--data <path>]  # default: data/
```

- Finds `PerformanceLog` under `data/<version>/`.
- Uses `*loading.log` if present; otherwise `*.log`.
- Creates per-version `summary.csv`, then writes combined `summary.csv`, followed by `summary_stats.csv` and `service_stats.csv`.
- If `result/<data-folder>/summary.csv` already exists, skips regeneration to speed up iteration.

### 7.3 `serve`

```
python spm.py serve [--data <path>] [--host 0.0.0.0] [--port 8000] [--debug] [--no-build]
```

- Builds reports unless `--no-build`.
- Serves web UI at `/` with the configured dataset root/base.

### 7.4 `merge`

```
python spm.py merge <src...> [--into <dest>] [--overwrite]
```

- Copies multiple source folders into destination tree, preserving structure.
- Reports counts of copied/skipped/overwritten files.

## 8. Backend API

### 8.1 `GET /`

- Returns the HTML page with an embedded initial state:

```json
{
  "view": "analytics",
  "selectedDataset": "data",       
  "datasetOptions": ["data", "data2"],
  "endpoints": {
    "csv": "/api/csv",
    "download": "/download",
    "dashboard": "/api/dashboard",
    "analyticsBar": "/analytics/bardata"
  }
}
```

### 8.2 `GET /api/dashboard`

Query params:

- `view`: `analytics` | `reports` | `compare`
- `dataset`: dataset name (optional)
- `version`: selected version for box chart (optional)
- `compareA`, `compareB`: versions to compare (optional)
- `filter`: `all` | `positive` | `negative` | `faster` | `slower` (optional)
- `report`: CSV relative path to preview (optional)

Response (excerpt):

```json
{
  "activeView": "analytics",
  "datasetOptions": ["data", "data2"],
  "selectedDataset": "data",
  "versions": ["2.0.1.0", "2.0.1.2", "2.0.1.3"],
  "boxVersions": ["2.0.1.0", "2.0.1.2"],
  "selectedVersion": "2.0.1.0",
  "versionStats": {
    "metrics": ["Average", "Max", "Min", "Median"],
    "versions": ["2.0.1.0", "2.0.1.2", "2.0.1.3"],
    "rows": [
      {"metric": "Average", "values": {"2.0.1.0": 1040, "2.0.1.2": 1005}}
    ]
  },
  "lineFigure": {"data": [...], "layout": {...}},
  "barFigure": {"data": [...], "layout": {...}},
  "boxFigures": {"2.0.1.0": {"data": [...], "layout": {...}}},
  "reports": {
    "files": ["InQuire_2.0.1.0/summary.csv", "service_stats.csv"],
    "initial": "InQuire_2.0.1.0/summary.csv"
  },
  "compare": {
    "services": ["Service A", "Service B"],
    "data": {"Service A": {"2.0.1.0": 1105, "2.0.1.2": 1075}},
    "defaults": {"versionA": "2.0.1.0", "versionB": "2.0.1.2", "filter": "all"}
  },
  "datasetWarnings": ["Warning: dataset must include 24 services, found 22."],
  "datasetError": null,
  "endpoints": {"csv": "/api/csv", "download": "/download", "dashboard": "/api/dashboard", "analyticsBar": "/analytics/bardata"}
}
```

### 8.3 `GET /api/csv?file=<rel>[&dataset=<name>]`

Response:

```json
{
  "file": "InQuire_2.0.1.0/summary.csv",
  "dataset": "data",
  "headers": ["service", "loading_time_ms"],
  "rows": [["Service A", "1234"], ["Service B", "845"]]
}
```

Notes:

- Only `.csv` files are served.
- Path is validated to be inside the selected dataset root.

### 8.4 `GET /download?file=<rel>[&dataset=<name>]`

- Sends the requested CSV as a file download.

### 8.5 `GET /analytics`

- Redirects to `/` with `view=analytics`.

### 8.6 `GET /analytics/bardata[?dataset=<name>]`

Response (when valid): `{"figure": {"data": [...], "layout": {...}}, "dataset": "...", "warnings": [...], "error": null}`.
If data is insufficient, returns `warnings`/`error` and an empty figure.

### 8.7 `POST /api/datasets/import`

- Purpose: Import a dataset from a ZIP file or a folder upload and generate reports.
- Form fields (either option works):
  - ZIP upload:
    - `file`: a `.zip` archive of the dataset
    - `datasetName` (optional): name to use for `data/<datasetName>`
  - Folder upload (multi-file):
    - `folder`: multiple files with relative paths (e.g., `myData/2.0.1.0/PerformanceLog/x.log`)
    - `datasetName` (optional): overrides inferred name
- Validation: dataset must contain at least three version folders; each version must contain a `PerformanceLog` directory (can be nested). On success, files are moved to `data/<dataset>/` and reports are generated under `result/<dataset>/`.
- Success response: `201` with JSON `{ "dataset": "<name>", "message": "Dataset imported successfully." }`
- Error responses: `400` invalid upload/structure, `409` dataset already exists, `500` server error.

Example (ZIP):

```
curl -F "file=@/path/to/myData.zip" -F "datasetName=myData" http://localhost:8000/api/datasets/import
```

## 9. Data Quality Rules

- Total unique services should equal 24; otherwise produce a warning.
- Must contain a service named `AUTO TEST` (case-insensitive match by equality after normalization); otherwise return an error.
- Sample count per service should match `AUTO TEST`; mismatches listed as warnings.
- Excluded services (see 6.7) are filtered out before analytics.

## 10. Frontend UI Specification

### 10.1 Global Layout

- Left vertical sidebar: view switcher (icons + labels): Analytics / CSV Viewer / Compare / API (Backend API reference).
- Header bar: title + dataset selector + loading indicator.
- Main content: renders current view body.

### 10.2 Analytics View

- Cards:
  - Line: Average Loading Time per Service (by Version)
  - Grouped Bar: Average Loading Time per Service (grouped by version)
  - Distribution: Box plots per service for a selected version + version selector
  - Version Summary Statistics: table for Average/Max/Min/Median per version
- Interactions:
  - Expand card to full-screen overlay; Esc closes.
  - Warning/error banners show dataset quality messages.

### 10.3 CSV Viewer

- Left list: 
  - This list is always visible even when the user scrolls in the right pane. 
  - discovered CSV files under the selected dataset root. 
  - A button located at the top-right corner allows user to import a new [dataset](#61-dataset).
  - Display the dataset name as the group name, and all CSV files should be under their respective groups; Display counts beside each group name and provide collapse/expand buttons.
  - A button located at the top-right corner of each group allows the user to delete the dataset. The deleted dataset will be moved to the recycle folder.
- Right pane: file title, dataset label, Download and Refresh buttons, table preview.

### 10.4 Compare View

- Controls: Baseline/Target version selectors; Filter selector (`All`, `≥30% faster`, `≥30% slower`, `Faster`, `Slower`).
- Table: service, baseline ms, target ms, delta ms, delta %; improved/regressed badges.

### 10.5 Units & Formatting

- Time in milliseconds (ms), percentages with 1 fractional digit.

## 11. Security & Safety

- Path resolution strictly confines CSV access to the dataset root; rejects non-CSV.
- Dataset selection is constrained to subdirectories of `SPM_RESULT_BASE` that contain `summary.csv`.
- CSV reads support `utf-8` and `utf-8-sig` to tolerate BOM.

## 12. Acceptance Criteria

- CLI
  - `generate` produces `summary.csv`, `summary_stats.csv`, `service_stats.csv` with expected headers and values.
  - `serve` starts UI; `--no-build` skips regeneration when artifacts exist.
  - `merge` reports copied/skipped/overwritten and preserves directory layout.
- Backend
  - `/api/dashboard` returns figures/tables when data valid; includes warnings/errors as specified.
  - `/api/csv` previews any CSV under dataset; `/download` downloads it.
- Frontend
  - Views toggle and preserve URL state (`dataset`, `view`, `version`, compare params, `report`).
  - Analytics shows 3 charts + stats table; overlay expand works.
  - CSV Viewer lists files, previews contents, and downloads on click.
  - Compare computes deltas and respects filters.

## 13. Known Limitations

- Combined `summary.csv` stores multiple samples by repeating service rows; charts compute averages from these.
- Hardcoded exclusions and data-quality rules; changes require code updates.
- Assumes 24 services as completeness criterion; projects with different counts must adjust validation.

## 14. Future Enhancements (Non-functional)

- Configurable aggregation (mean/median/percentiles) and baseline version.
- Chart export (PNG/SVG) and sharable dashboard state URLs.
- Custom service groups/tags and saved filters.
- Authentication if deployed in shared environments.

## 15. Example Screens (Placeholders)

Add screenshots here when available, suggested shots:

- Analytics view with all four cards populated.
- CSV Viewer with a file selected and table preview visible.
- Compare view highlighting regressions and improvements.

Directory suggestion for images:

```
docs/images/
  analytics.png
  csv-viewer.png
  compare.png
```

## 16. Containerization

### 16.1 Build Image

- Build a local Docker image from the project root:

```
docker build -t spm-app:latest .
```

### 16.2 Run Container (simple)

- Start the app on port 8000 (maps host ./data, ./result, and ./recycle into the container):

```
docker run --rm -it \
  -p 8000:8000 \
  -v "$PWD/data:/app/data" \
  -v "$PWD/result:/app/result" \
  -v "$PWD/recycle:/app/recycle" \
  --name spm spm-app:latest
```

- Access UI at `http://localhost:8000/`.

### 16.3 docker-compose

- A `docker-compose.yml` is included. Bring the stack up with:

```
docker compose up --build
```

- Default ports: `8000:8000`. Data and results are persisted via bind mounts.

### 16.4 Environment Variables

- `SPM_DEFAULT_DATASET` (optional): default dataset name shown in the UI dropdown.
- `SPM_RESULT_BASE` (optional): base directory that contains datasets in results (default `/app/result`).
- `SPM_RESULT_ROOT` (optional): active dataset result root (default `/app/result/<dataset>`; set by the server).

### 16.5 Data Workflow in Containers

- To pre-seed raw logs, place them on the host under `./data/<version>/PerformanceLog` before starting the container. The app will parse and generate reports on first run.
- Alternatively, upload datasets at runtime via the UI “Import Dataset” button or the API:

```
curl -F "file=@/path/to/myData.zip" -F "datasetName=myData" http://localhost:8000/api/datasets/import
```

- Generated artifacts are written to `./result/<dataset>/`. Deleting a dataset via the UI moves its data and results under `./recycle/`.

### 16.6 Makefile Shortcuts

- Build image: `make build` (override `IMAGE=spm-app:dev` if needed)
- Run container: `make run` (override `PORT=8080`, `NAME=spm`)
- Stop container: `make stop`
- Tail logs: `make logs`
- Compose up/down: `make compose-up` / `make compose-down`
- Open shell in container image: `make shell`

### 16.7 CI Image Publishing

- GitHub Actions workflow builds and publishes a Docker image to GitHub Container Registry (GHCR) on Git tags starting with `v`.
- Tags produced:
  - `ghcr.io/<owner>/<repo>:<tag>` (e.g., `v1.2.3`)
  - `ghcr.io/<owner>/<repo>:latest`
- Trigger: push a tag like `v1.0.0`.
- Location of workflow: `.github/workflows/docker-image.yml`.
