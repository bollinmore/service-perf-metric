# Quickstart: Three-Version Comparison Mode

## Prerequisites
- Python 3.11 environment with project dependencies installed.
- Data folder prepared as the version pool (e.g., `data/<pool-name>/`), containing at least three distinct versions.
- CLI/API/UI access to the service.

## Generate per-version summaries (no cross-version output)
1. Place or refresh version data under `data/<pool-name>/<version-id>/PerformanceLog/*.log`.
2. Run the generate workflow (`python spm.py generate --data-folder <pool-name>`) to emit per-version `summary.csv` only. Cross-version outputs (`summary.csv`, `summary_stats.csv`, `service_stats.csv` at the pool root) are **not** produced here.
3. Verify each version is marked available via API (`GET /versions?data_folder=<pool-name>`) before comparison.

## Run a three-version comparison
1. List available versions:
   - CLI: `... list-versions --data-folder <pool-name>`
   - API: `GET /versions?data_folder=<pool-name>`
2. Trigger comparison with exactly three distinct versions:
   - CLI: `python -m src.cli.commands.compare --data-folder <pool-name> --versions v1 v2 v3`
   - API: `POST /comparisons` with `{ "data_folder": "<pool-name>", "versions": ["v1", "v2", "v3"] }`
3. On success, temporary reports are written under `result/<pool-name>/temp/<run-id>/` and promoted via `result/<pool-name>/temp/latest/`.

## Consume comparison outputs
- Downloads/visualizations should read from `result/<pool-name>/temp/latest/summary.csv`, `summary_stats.csv`, and `service_stats.csv`.
- CLI download helper: `python -m src.cli.commands.download --data-folder <pool-name> --file summary`
- API: `GET /comparisons/latest?data_folder=<pool-name>` for metadata; `GET /downloads/comparison?data_folder=<pool-name>&file=summary` for files.
- If no latest comparison exists, the system prompts for a three-version selection instead of serving stale data.

## Validation rules and errors
- Exactly three distinct versions are required; fewer or more are blocked with a clear message.
- Missing versions or artifacts (e.g., absent PerformanceLog) cause the comparison to fail without emitting partial reports.
- Duplicate selections are rejected; rerun with three unique version IDs.

## Cleanup behavior
- Each new comparison run creates `temp/<run-id>/` and updates `temp/latest/` only after outputs are fully written.
- Previous temp outputs are removed during the next successful run to avoid buildup; per-version summaries remain untouched.
