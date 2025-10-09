# Service Performance Metric

Browse performance CSV outputs in a browser and generate summary reports.

## Quick Start

- Install dependencies:
  - `pip install -r requirements.txt`
- Generate per-version summaries and combined report:
  - `python src/extract.py`
  - `python src/extract.py --combine`
  - `python src/report.py`
- Run the web app to browse CSVs:
  - `python src/webapp.py`
  - Open `http://localhost:8000/`

## Project Layout

- `data/InQuire_*/PerformanceLog/` raw logs (inputs)
- `result/InQuire_*/summary.csv` per-version summaries
- `result/summary.csv` combined table across versions
- `result/summary_stats.csv` overall stats per version
- `result/service_stats.csv` per-service stats
- `src/extract.py` log parser + combiner
- `src/report.py` stats generator
- `src/webapp.py` Flask CSV browser

## CI

On every push, GitHub Actions will:
- Set up Python and install dependencies.
- Generate summaries and reports from `data/`.
- Upload the `result/` directory as a build artifact.

