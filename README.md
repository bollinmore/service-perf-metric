# Service Performance Metric

Browse performance CSV outputs in a browser and generate summary reports.

## Quick Start

- Install dependencies with `pip install -r requirements.txt`.
- (Optional) Consolidate multiple raw folders into `data/`:
  - `python spm.py merge data1 data2 data3 --into data`
- Generate per-version summaries only (requires `--data-folder`; cross-version reports are produced later via comparison):
  - `python spm.py generate --data-folder data`
  - Use a different source folder with `python spm.py generate --data-folder data2`
  - Optional: `--versions 2.0.1.0,2.0.1.2` to limit, `--refresh` to clear old results, `--allow-conflicts` to proceed on mismatched logs.
  - Outputs are stored under `result/<data-folder>/<version>/summary.csv`; no root-level `summary.csv`/`summary_stats.csv`/`service_stats.csv` are generated here.
- Start the browser UI (builds reports unless `--no-build` is supplied):
  - `python spm.py serve --data-folder data`
  - `python spm.py serve --data-folder data2`
  - Optional: `--versions ...`, `--refresh`, `--allow-conflicts`
  - Open tables at `http://localhost:6231/`
  - Analytics dashboard at `http://localhost:6231/analytics`
  - Switch datasets through the Average Loading Time card dropdown to compare different `result/<data-folder>` outputs
  - Use the left sidebar to flip between analytics, Compare, and in-page CSV previews
- Run a three-version comparison (temp outputs at `result/<data-folder>/temp/<run-id>/`, promoted to `result/<data-folder>/temp/latest/`):
  - API: `POST /comparisons` with `{ "data_folder": "<pool>", "versions": ["v1","v2","v3"] }`
  - CLI: `python -m src.cli.commands.compare --data-folder <pool> --versions v1 v2 v3`
  - Fetch latest: `GET /comparisons/latest?data_folder=<pool>`; download files via `GET /downloads/comparison?data_folder=<pool>&file=summary`
  - CLI download helper: `python -m src.cli.commands.download --data-folder <pool> --file summary`
- Mode toggle (local only):
  - Add `SPM_MODE=development` or `SPM_MODE=production` to `.env` (invalid/missing values default to development with a warning).
  - Start with `python spm.py serve`; startup logs display the active mode and any preserved development snapshot.
  - Check status via `GET /mode` and readiness via `GET /mode/readiness`; toggle with `POST /mode` (production toggle blocks if readiness is incomplete).
- Run the Flask app directly (custom host/port as needed):
  - `python src/webapp.py --host 127.0.0.1 --port 5001`
- Clean out generated artifacts anytime:
  - `python spm.py clean`

## Project Layout

- `data/` default root for raw logs (overridable via CLI `--data`; other folders like `data1/`, `data2/` can be merged)
- `data/<version>/PerformanceLog/` raw logs (source inputs)
- `result/<data-folder>/InQuire_*/summary.csv` per-version summaries
- `result/<data-folder>/temp/<run-id>/{summary.csv,summary_stats.csv,service_stats.csv}` comparison outputs for one run
- `result/<data-folder>/temp/latest/` pointer to the latest comparison outputs
- `src/extract.py` log parser + combiner
- `src/report.py` stats generator
- `src/webapp.py` Flask CSV browser
- `spm.py` entry-point CLI (`clean`, `generate`, `serve`, `merge`, `versions`, `compare`, `upload`)
- Docker deployments: forced Production mode by default (`SPM_MODE=production`, `SPM_FORCE_PRODUCTION=1` in Dockerfile/docker-compose) regardless of local `.env`.

## CI

On every push, GitHub Actions will:
- Set up Python and install dependencies.
- Generate summaries and reports from `data/`.
- Upload the `result/` directory as a build artifact.
