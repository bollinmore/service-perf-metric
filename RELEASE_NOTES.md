# Release Notes

## v1.0 (2025-11-29)

First public release of Service Performance Metric.

### Highlights
- Browser-based analytics UI (Flask + plotly) for performance CSVs at `http://localhost:6231/` with compare view and CSV previews.
- CLI entrypoint `spm.py` for generating reports, serving the UI, merging datasets, uploading logs, and running version comparisons.
- Containerized deployment: defaults to production mode, port `6231`, and a named data volume for persistence.

### Added
- CLI commands: `generate`, `serve`, `compare`, `merge`, `versions`, and `upload` (zip import).
- Web features: analytics dashboard, three-version comparison outputs, dataset selector, in-page CSV viewer, and mode toggle endpoints (`/mode`, `/mode/readiness`).
- Data workflow helpers for ingesting raw logs under `data/<version>/PerformanceLog/` and writing summaries to `result/<data-folder>/<version>/`.

### Changed
- Docker defaults: port mapping `6231:6231`; `/app/data` now backed by a named volume `spm-data` (override with `SPM_DATA_VOLUME` or a bind mount); `/app/result` and `/app/recycle` remain host binds for easy inspection.
- Container paths align on `/app` to ensure templates and data resolve correctly.

### Deployment Notes
- Build: `docker build -t spm-app:latest .`
- Run: `docker run --rm -it -p 6231:6231 -v spm-data:/app/data -v "$PWD/result:/app/result" -v "$PWD/recycle:/app/recycle" --name spm spm-app:latest`
- Compose: `docker compose up --build` (override data mount with `SPM_DATA_VOLUME=/host/path` if desired).
