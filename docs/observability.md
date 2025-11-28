# Observability Notes: Three-Version Comparison Mode

- **Comparison runs**: Structured log `comparison.run.completed` with `run_id`, `data_folder`, `versions`, `run_dir`, `latest_pointer`. Ensure log level `INFO` enabled (`SPM_LOG_LEVEL`).
- **Validation failures**: ValidationError messages surface to CLI/API and should be mirrored in service logs for missing artifacts or invalid selections.
- **Temp storage**: Each comparison writes to `result/<data-folder>/temp/<run-id>/` and promotes `temp/latest/`. Previous runs are pruned after a successful promote.
- **Per-version generation**: `python spm.py generate` now logs only per-version outputs; no cross-version reports are written in generate.
- **Troubleshooting**: If `latest` is missing or stale, rerun comparison and check temp directory for `manifest.json` to verify outputs and selection metadata.
