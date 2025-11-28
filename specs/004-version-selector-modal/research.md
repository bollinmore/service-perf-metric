# Research - Version Selector Modal

## Decision: Refresh version list on modal open
- **Decision**: Re-scan datasets under the configured data folder each time the modal opens and rebuild the version list with dataset context.
- **Rationale**: Keeps options accurate if datasets/versions change between interactions and matches the clarification to avoid stale selections.
- **Alternatives considered**: Cache once per page (risk of stale data); manual refresh control (adds extra step without clear benefit).

## Decision: Deduplicate and order version options
- **Decision**: Treat dataset + version label as a unique option; display both for disambiguation and sort by dataset name then version label.
- **Rationale**: Prevents collisions when different datasets share version labels and provides predictable ordering for scanning.
- **Alternatives considered**: Version-only dedupe (ambiguous when labels collide); unsorted listing (harder to scan).

## Decision: Canonical version identifier
- **Decision**: Use a canonical identifier in the form `<dataset>/<version>` when passing selections to the backend and persisting comparison state.
- **Rationale**: Guarantees uniqueness across datasets while keeping identifiers human-readable and compatible with filesystem paths.
- **Alternatives considered**: Separate dataset/version fields (more payload structure for minimal gain); version-only identifiers (collide across datasets).

## Decision: Selection cap and feedback behavior
- **Decision**: Enforce a hard cap of three selected versions; block the fourth selection attempt with inline feedback while preserving existing selections.
- **Rationale**: Aligns with spec limits and prevents accidental overrides; inline feedback reduces confusion.
- **Alternatives considered**: Auto-deselect oldest selection (unexpected loss of context); soft warning without enforcement (does not meet requirement).
