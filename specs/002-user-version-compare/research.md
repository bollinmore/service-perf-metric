# Research: User-Defined Version Comparison for Test Data

## Decisions

### Version discovery
- **Decision**: Auto-scan immediate subfolders under an admin-configured base path to list selectable versions.
- **Rationale**: Reduces user error, keeps discovery predictable, and aligns with existing filesystem layout.
- **Alternatives considered**: User-picked arbitrary folders (higher error risk); manifest/registry file (extra upkeep).

### Base path permissions
- **Decision**: Only admins/maintainers may set or change the base path; regular users only select versions.
- **Rationale**: Prevents accidental exposure of unintended directories and keeps comparisons bounded.
- **Alternatives considered**: User-editable base path (risk of bad paths); fixed, non-editable config (less flexible for environments).

### Comparison set size
- **Decision**: Support 2–4 versions per comparison.
- **Rationale**: Matches spec intent and keeps performance predictable.
- **Alternatives considered**: Unlimited selections (risk of slow/failed comparisons).

### Performance target
- **Decision**: Refresh comparison output within 5 seconds for standard dataset sizes when changing selections.
- **Rationale**: Matches success criteria; keeps UX responsive.
- **Alternatives considered**: No bound (poor UX); stricter bound (<2s) may be unrealistic for larger datasets.

### Schema/metric mismatch handling
- **Decision**: Detect mismatches, flag conflicts, and guide users to adjust selection or mappings; exclude incompatible versions unless resolved.
- **Rationale**: Avoids silent errors and keeps outputs reliable.
- **Alternatives considered**: Hard fail on any mismatch (blocks progress); auto-merge heuristics without user confirmation (risk of incorrect comparisons).

### Logging/observability
- **Decision**: Log selection sets, comparison runs, and errors (missing data, schema conflicts) with timestamps and version identifiers.
- **Rationale**: Needed for traceability and debugging user-reported issues.
- **Alternatives considered**: Minimal logging (insufficient for audit/support); verbose per-record logging (noisy, unnecessary).

### CLI launch parameters
- **Decision**: Require `--data-folder` and allow optional `--versions` comma-separated list (e.g., `--versions 2.0.1.0,2.0.1.2,2.0.1.3`) to preselect versions.
- **Rationale**: Aligns with user workflow and enforces base-path selection at startup.
- **Alternatives considered**: Optional base path (risk of implicit defaults); GUI-only selection (doesn’t cover CLI use).

### Upload packaging
- **Decision**: Accept exactly one zip per upload, enforcing `<tool-version>/PerformanceLog/*.log` structure before ingest.
- **Rationale**: Prevents malformed/mixed uploads and keeps version structure consistent.
- **Alternatives considered**: Multiple zips per request (more complex validation); allowing arbitrary folder shapes (breaks discovery and comparison).
