# service-perf-metric Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-11-27

## Active Technologies
- Python 3.11 + Flask, pandas, plotly (001-three-version-compare)
- Local filesystem data pool and results (per-version summaries, temp cross-version outputs) (001-three-version-compare)
- Python 3.11 + Flask app serving a React/htm-based front-end, pandas/plotly for analytics views (004-version-selector-modal)
- Local filesystem datasets under the configured `--data-folder` (004-version-selector-modal)

- Python 3.11 (assumed from typical Flask/pandas stack) + Flask, pandas, plotly (001-dev-prod-toggle)

## Project Structure

```text
src/
tests/
```

## Commands

cd src [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .

## Code Style

Python 3.11 (assumed from typical Flask/pandas stack): Follow standard conventions

## Recent Changes
- 004-version-selector-modal: Added Python 3.11 + Flask app serving a React/htm-based front-end, pandas/plotly for analytics views
- 003-three-version-compare: Added Python 3.11 + Flask, pandas, plotly
- 001-three-version-compare: Added Python 3.11 + Flask, pandas, plotly


<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
