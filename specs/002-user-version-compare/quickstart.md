# Quickstart: User-Defined Version Comparison

1) Configure base path (admins/maintainers): set the test-data base folder path in config/env so only subfolders under it are scanned.
2) Start CLI (list versions): `python spm.py versions --data-folder <path>`.
3) Upload data: `python spm.py upload --data-folder <path> --zip <file.zip>`; must contain `<tool-version>/PerformanceLog/*.log` or it is rejected.
4) Run comparison: `python spm.py compare --data-folder <path> --versions 2.0.1.0,2.0.1.2,2.0.1.3 [--refresh] [--allow-conflicts]`; requires 2–4 versions.
5) Generate reports only: `python spm.py generate --data-folder <path> [--versions ...] [--refresh] [--allow-conflicts]`.
6) Serve UI: `python spm.py serve --data-folder <path> [--versions ...] [--refresh] [--allow-conflicts] [--no-build]` (if `--versions` is omitted, the last three versions under the data folder are used by default).
7) Handle issues: if versions are missing logs or metrics mismatch, the CLI reports errors; add `--allow-conflicts` to proceed when conflicts are acceptable.
8) Refresh: use `--refresh` to clear prior results and re-run; comparisons should refresh within ~5 seconds for standard datasets.
9) Audit: check logs for selection sets, warnings, and errors to confirm traceability.
