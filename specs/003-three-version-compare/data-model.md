# Data Model: Three-Version Comparison Mode

## Entities

### DataVersion
- **Attributes**: `version_id` (string, unique), `data_folder` (string), `source_path` (string), `summary_path` (string), `created_at` (datetime), `status` (available | missing_artifacts | corrupted).
- **Validation**: `version_id` must be unique within a data folder; `summary_path` must exist before use in comparison; status reflects readiness for comparison.
- **Relationships**: One DataVersion has one Per-Version Summary.

### PerVersionSummary
- **Attributes**: `data_folder` (string), `version_id` (string), `summary_path` (string), `generated_at` (datetime), `source_checksum` (string, optional).
- **Validation**: Generated during ingestion/read; must be present before a comparison run; never overwritten by cross-version runs.
- **Relationships**: Belongs to DataVersion; used by TemporaryComparisonReportSet inputs.

### ComparisonRequest
- **Attributes**: `data_folder` (string), `selected_versions` (array of 3 distinct version_ids), `requested_at` (datetime), `requested_by` (user/cli identifier), `run_id` (string, generated).
- **Validation**: Must contain exactly three distinct versions that exist and are ready (status available); reject duplicates or missing versions.
- **Relationships**: Produces one TemporaryComparisonReportSet.

### TemporaryComparisonReportSet
- **Attributes**: `data_folder` (string), `run_id` (string), `selected_versions` (array of 3 version_ids), `summary_path` (string), `summary_stats_path` (string), `service_stats_path` (string), `location` (string, e.g., `result/<data-folder>/temp/<run-id>/`), `latest_pointer` (string pointing to active run), `created_at` (datetime), `status` (pending | completed | failed), `error` (string, optional).
- **Validation**: Paths must live under the temp area and not overwrite per-version summaries; set to completed only after all outputs are written; on failure do not advance `latest_pointer`.
- **Relationships**: Generated from one ComparisonRequest; read by download/visualization flows; supersedes prior run as `latest` when completed.

## States & Transitions
- **ComparisonRequest**: created → validated (exactly 3 distinct, existing, ready versions) → processing → completed (TemporaryComparisonReportSet created) | failed (no temp outputs promoted).
- **TemporaryComparisonReportSet**: pending (outputs generating) → completed (all files written, pointer updated) | failed (pointer unchanged).
