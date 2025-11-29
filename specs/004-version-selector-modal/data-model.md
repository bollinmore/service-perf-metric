# Data Model - Version Selector Modal

## Entities

### Dataset
- **Attributes**: `name` (string), `path` (absolute path under data folder), `versions` (list of VersionOption).
- **Rules**: Must be a directory under the configured data folder; may contain zero or more version subdirectories; excluded if not readable.
- **Relationships**: Owns VersionOptions discovered within its directory.

### VersionOption
- **Attributes**: `id` (`<dataset>/<version>`), `dataset` (string), `version` (string), `status` (`available` | `missing_artifacts`), `summary_path` (path), `selectable` (bool derived from status).
- **Rules**: Selectable only when status is `available`; displayed with dataset context to disambiguate collisions; ordering is by dataset then version.
- **Relationships**: Belongs to a Dataset; referenced by VersionSelection.

### VersionSelection
- **Attributes**: `selected` (list of VersionOption ids, size 1–3), `source_data_folder` (path), `last_updated` (timestamp or run id from comparison manifest).
- **Rules**: Must contain at least one and at most three ids; all ids must be currently selectable; stale ids (missing dataset/version) are flagged and blocked on confirm.
- **Relationships**: Drives ComparisonViewState; pre-populated in the modal when reopened.

### ComparisonViewState
- **Attributes**: `active_selection` (VersionSelection), `latest_manifest` (path or payload), `view` (e.g., reports/comparison as per existing UI).
- **Rules**: Updating active_selection triggers comparison refresh; if selections are invalidated, prompt user to reselect.

## State & Validation
- On modal open: refresh Dataset and VersionOption lists from the data folder; mark selectable states.
- On selection: enforce cap of three; block additional picks with inline feedback; keep prior selections intact.
- On confirm: require 1–3 selectable ids; apply to ComparisonViewState; if any selected id no longer exists, show an error and block confirm until resolved.
- On reopen: preselect current active_selection; remove or disable stale ids if the underlying dataset/version disappeared.

## Volume & Scale Assumptions
- Expected tens of datasets and versions (human-manageable lists); single-user or small-team concurrency; no high-volume multi-tenant loads anticipated.
