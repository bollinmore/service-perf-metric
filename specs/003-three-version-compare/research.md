# Research: Three-Version Comparison Mode

## Temporary report storage & cleanup
- **Decision**: Store comparison outputs under `result/<data-folder>/temp/<run-id>/` with a `latest` pointer (folder or manifest) updated on each successful comparison run; overwrite `latest` atomically after generation and remove the previous run’s temp folder during the next successful run.
- **Rationale**: Keeps per-version summaries isolated, avoids accidental overwrite, and provides a single stable location for downstream readers while preventing temp buildup.
- **Alternatives considered**: (1) Single shared `temp` folder without run isolation—rejected due to race/staleness risk. (2) Long-lived run history—rejected to reduce cleanup burden and scope.

## CLI/API triggers for comparison
- **Decision**: Expose a dedicated compare action (`compare` CLI command; `POST /comparisons` API) requiring `data_folder` and exactly three distinct version identifiers; block generate paths from emitting cross-version outputs.
- **Rationale**: Clean separation keeps default generate lightweight and ensures cross-version work is intentional and validated.
- **Alternatives considered**: (1) Auto-compare during generate—rejected because it conflicts with “即選即算”. (2) Allow 2–4 versions—rejected per new rule to enforce exactly three.

## Validation and messaging
- **Decision**: Enforce “exactly three distinct versions” with a consistent error message; explicitly flag duplicate selections and missing versions from the pool before any compute starts.
- **Rationale**: Aligns UX across CLI/API/UI and prevents wasted work on invalid selections.
- **Alternatives considered**: (1) Auto-dedupe and proceed with fewer than three—rejected because it hides user intent and violates requirement. (2) Soft warnings—rejected to keep strict validation.

## Handling missing artifacts (e.g., PerformanceLog)
- **Decision**: When required inputs like `PerformanceLog` are absent for a selected version, fail the comparison with a clear message naming the missing artifact and version; do not emit partial temp reports.
- **Rationale**: Avoids incomplete/stale outputs and simplifies troubleshooting.
- **Alternatives considered**: (1) Skip missing versions and proceed—rejected because it violates “exactly three” and risks silent data gaps. (2) Fallback to previous runs—rejected to avoid stale data.

## Concurrency and isolation
- **Decision**: Treat each comparison run as independent; generate into a new `temp/<run-id>/` and flip `latest` only after generation succeeds. Concurrent runs write to distinct run-ids; the last successful run becomes `latest`.
- **Rationale**: Prevents collisions and stale reads; supports parallel requests without overwriting in-flight runs.
- **Alternatives considered**: (1) Global lock with single temp folder—rejected for brittleness under concurrent requests. (2) Allow simultaneous writes to the same folder—rejected due to corruption risk.
