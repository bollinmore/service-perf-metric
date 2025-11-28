# Feature Specification: User-Defined Version Comparison for Test Data

**Feature Branch**: `002-user-version-compare`  
**Created**: 2025-11-28  
**Status**: Draft  
**Input**: User description: "修改目前測試資料的檔案結構，不再使用指定 data folder 固定讀取其中三個資料夾的測試紀錄，而是交由使用者決定要比較的版本。"

## Clarifications

### Session 2025-11-28

- Q: How should available versions be discovered? → A: Auto-scan all immediate subfolders under a configurable base path as selectable versions.
- Q: Who can configure the base folder? → A: Only admins/maintainers can set or change the base folder; regular users only pick versions.

## User Scenarios & Testing *(mandatory)*

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
  Each user story/journey must be INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.
  
  Assign priorities (P1, P2, P3, etc.) to each story, where P1 is the most critical.
  Think of each story as a standalone slice of functionality that can be:
  - Developed independently
  - Tested independently
  - Deployed independently
  - Demonstrated to users independently
-->

### User Story 1 - Choose Versions to Compare (Priority: P1)

A user selects any two or more available test-data versions to compare instead of being limited to three hardcoded folders.

**Why this priority**: Unlocks the primary goal of user-driven comparisons, removing the current structural constraint.

**Independent Test**: Select two available versions from the list and confirm that a comparison view loads using only those selections.

**Acceptance Scenarios**:

1. **Given** the system has a discoverable list of available versions, **When** a user selects at least two versions and starts comparison, **Then** the comparison is generated using only the selected versions.
2. **Given** at least two versions exist, **When** the user tries to proceed with fewer than two selected, **Then** the system blocks the action and explains the minimum requirement.

---

### User Story 2 - Update Selection and Refresh Results (Priority: P2)

After an initial comparison, the user can change which versions are included and quickly see refreshed results reflecting the new selection.

**Why this priority**: Supports iterative analysis without manual folder changes or app restarts.

**Independent Test**: Run a comparison, adjust the version selection, and verify the comparison view refreshes with the new set without errors.

**Acceptance Scenarios**:

1. **Given** a completed comparison, **When** the user deselects one version and selects another, **Then** the view refreshes to show only the updated selection with correct labels.
2. **Given** large datasets within supported limits, **When** the selection is changed, **Then** the refresh completes within the defined performance threshold.

---

### User Story 3 - Handle Missing or Incompatible Data (Priority: P3)

If a selected version is missing data or uses an incompatible layout, the user is notified and can adjust selection without breaking the comparison flow.

**Why this priority**: Prevents silent failures and ensures users understand how to resolve issues.

**Independent Test**: Include a version with incomplete data, attempt comparison, and confirm the system flags the issue while allowing correction.

**Acceptance Scenarios**:

1. **Given** one selected version lacks required test records, **When** the comparison runs, **Then** the system reports which version is incomplete and excludes it unless the user confirms an alternative.
2. **Given** schema differences across versions, **When** metrics cannot be aligned, **Then** the system highlights the mismatch and requests a different selection or provides a mapping prompt.

---

### Edge Cases

- User selects fewer than two versions and tries to compare.
- A chosen version folder exists but contains no readable test records.
- Selected versions have mismatched data schemas or missing required fields.
- Duplicate selection of the same version.
- Extremely large version sets exceeding supported comparison count.
- Uploaded zip lacks the required `<tool-version>/PerformanceLog/*.log` structure or contains multiple top-level versions.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system must surface a discoverable list of available test-data versions by auto-scanning immediate subfolders under a configurable base path instead of relying on fixed folder names.
- **FR-001a**: Base folder configuration must be restricted to admins/maintainers; regular users can only select versions within the configured base path.
- **FR-002**: The system must allow users to select any combination of at least two and up to four versions for comparison in a single session.
- **FR-003**: The system must validate selections, preventing comparison when fewer than two versions are chosen and indicating the minimum requirement.
- **FR-004**: The system must load and label comparison outputs using only the user-selected versions.
- **FR-005**: The system must refresh comparison results when the user updates the selected versions without requiring application restart.
- **FR-006**: The system must detect when a selected version is missing required test records and notify the user which version needs attention.
- **FR-007**: The system must handle schema or metric mismatches across selected versions by flagging conflicts and guiding users to adjust selection or mappings.
- **FR-008**: The system must prevent duplicate inclusion of the same version in a comparison run.
- **FR-009**: The system must enforce a maximum supported number of versions per comparison (default four) and inform users when they exceed it.
- **FR-010**: The system must log user selections and comparison runs for traceability, including which versions were compared and when.
- **FR-011**: The CLI (`spm.py`) must accept a required `--data-folder` argument to set the base path and an optional `--versions` argument to preselect specific versions (comma-separated like `2.0.1.0,2.0.1.2,2.0.1.3`).
- **FR-012**: Each version’s test data must follow the structure `<tool-version>/PerformanceLog/*.log` under the configured base path.
- **FR-013**: Upload flow must accept exactly one zip per submission and validate that it matches the required `<tool-version>/PerformanceLog/*.log` structure before ingesting.

### Key Entities *(include if feature involves data)*

- **Version**: A labeled set of test records with metadata such as name, source path, timestamp, and schema version.
- **Comparison Selection**: A collection of chosen versions for a single comparison run, including validation status and any exclusions.
- **Test Metrics**: Comparable measurements derived from each version, aligned across selections for presentation.

### Assumptions

- Available versions can be discovered from existing storage locations without manual renaming.
- All versions use broadly compatible schemas; minor mismatches can be flagged and resolved by the user.
- Typical comparison involves two to four versions; performance targets are scoped to this range.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can select and launch a comparison with at least two versions in under 3 steps.
- **SC-002**: Changing the selected versions refreshes comparison outputs within 5 seconds for standard dataset sizes.
- **SC-003**: 100% of available versions with valid data are presented as selectable options.
- **SC-004**: Error states for missing or incompatible version data are surfaced with actionable guidance in 1 step or less.
- **SC-005**: At least 90% of user attempts to run comparisons complete without needing to adjust folder structures manually.
- **SC-006**: CLI startup succeeds when `--data-folder` is provided and either zero or valid comma-separated `--versions` are supplied, with clear errors otherwise.
- **SC-007**: 100% of uploads that lack the required `<tool-version>/PerformanceLog/*.log` structure are rejected with a clear message before processing.
