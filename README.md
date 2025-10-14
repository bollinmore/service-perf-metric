# Service Performance Metric

Browse performance CSV outputs in a browser and generate summary reports.

## Quick Start

- Install dependencies with `pip install -r requirements.txt`.
- (Optional) Consolidate multiple raw folders into `data/`:
  - `python spm.py merge data1 data2 data3 --into data`
- Generate the per-version summaries and aggregated reports (default `--data data`):
  - `python spm.py generate`
  - Use a different source folder with `python spm.py generate --data data2`
  - Outputs are stored under `result/<data-folder>/`; repeated runs reuse existing CSVs
- Start the browser UI (builds reports unless `--no-build` is supplied):
  - `python spm.py serve`
  - `python spm.py serve --data data2` (shorthand: `python spm.py serve data2`)
  - Open tables at `http://localhost:8000/`
  - Analytics dashboard at `http://localhost:8000/analytics`
- Clean out generated artifacts anytime:
  - `python spm.py clean`

## Project Layout

- `data/` default root for raw logs (overridable via CLI `--data`; other folders like `data1/`, `data2/` can be merged)
- `data/<version>/PerformanceLog/` raw logs (source inputs)
- `result/<data-folder>/InQuire_*/summary.csv` per-version summaries
- `result/<data-folder>/summary.csv` combined table across versions
- `result/<data-folder>/summary_stats.csv` overall stats per version
- `result/<data-folder>/service_stats.csv` per-service stats
- `src/extract.py` log parser + combiner
- `src/report.py` stats generator
- `src/webapp.py` Flask CSV browser
- `spm.py` entry-point CLI (`clean`, `generate`, `serve`, `merge`)

## CI

On every push, GitHub Actions will:
- Set up Python and install dependencies.
- Generate summaries and reports from `data/`.
- Upload the `result/` directory as a build artifact.
