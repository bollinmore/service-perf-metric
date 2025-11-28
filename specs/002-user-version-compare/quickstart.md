# Quickstart: User-Defined Version Comparison

1) Configure base path (admins/maintainers): set the test-data base folder path in config/env so only subfolders under it are scanned.
2) Start CLI: run `python spm.py --data-folder <path> [--versions 2.0.1.0,2.0.1.2,2.0.1.3]`.
3) Discover versions: run the CLI or service endpoint to list versions (`GET /versions` or equivalent CLI command).
4) Upload data: submit exactly one zip containing `<tool-version>/PerformanceLog/*.log`; invalid shapes are rejected before ingest.
5) Run comparison: submit 2–4 version names to start a comparison (`POST /comparisons` or CLI), avoiding duplicates.
6) Handle issues: if a version is missing data or has schema conflicts, review returned warnings/errors and adjust the selection.
7) Refresh: change selections and re-run; comparisons should refresh within ~5 seconds for standard datasets.
8) Audit: check logs for selection sets, warnings, and errors to confirm traceability.
