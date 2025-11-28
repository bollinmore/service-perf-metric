# Data Model: User-Defined Version Comparison for Test Data

## Entities

### Version
- **Attributes**: name/label, source_path (within base), discovered_at, schema_version, record_count (optional), last_modified, perf_log_paths (list)
- **Constraints**: Must reside under configured base path; name unique per base path; readable folder with required test records.

### ComparisonSelection
- **Attributes**: selection_id, selected_versions [Version], created_at, created_by_role (user/admin), status (pending, running, completed, error), excluded_versions (if invalid), notes/errors
- **Constraints**: At least 2 and at most 4 versions; no duplicates; only versions under current base path.

### MetricResult
- **Attributes**: version_name, metric_set (key/value pairs), computed_at, schema_version
- **Constraints**: Metrics align to comparison schema; mismatches must be flagged and either mapped or excluded.

### UploadPackage
- **Attributes**: upload_id, package_name, version_name (derived from top-level folder), validated (bool), errors, stored_path
- **Constraints**: Must be a single zip; must contain `<tool-version>/PerformanceLog/*.log`; reject multiples or missing PerformanceLog.

## Relationships
- ComparisonSelection references 2–4 Version entities.
- MetricResult instances are grouped by ComparisonSelection for side-by-side presentation.

## Validation Rules
- Reject selections with fewer than 2 or more than 4 versions.
- Reject or flag versions missing required test records; notify user which version failed.
- Prevent duplicate version entries in a single ComparisonSelection.
- When schema versions differ, mark conflict and require user confirmation or exclusion before completing comparison.
