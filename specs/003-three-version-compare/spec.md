# Feature Specification: Three-Version Comparison Mode

**Feature Branch**: `003-three-version-compare`  
**Created**: 2025-11-28  
**Status**: Draft  
**Input**: User description: "改為「資料池 + 即選即算」模式：data folder 只當版本池，使用者可從中自由挑選 3 個版本進行比較。 讀取資料時僅生成各版本的單版 summary.csv；不再預先生成跨版 summary.csv / summary_stats.csv / service_stats.csv。 當使用者指定要比較的 3 個版本時，才即時生成「暫時」的跨版 summary.csv、summary_stats.csv、service_stats.csv，內容僅涵蓋本次選取的版本。 選取版本數固定為 3（原本 2–4 的邏輯需更新），若不足或超過則阻擋並提示。 CLI/API/UI 的比較流程需讀取池中版本、讓使用者選 3 個並觸發上述暫時報表生成；其他非比較操作不應生成跨版報表。 報表輸出位置與存留策略需明確：暫時報表可放在 result/<data-folder>/temp 或同層命名隔離，避免覆蓋池中其他版本的單版 summary。 既有下載/視覺化路徑需改用暫時報表（若存在），否則提示尚未選擇版本進行比較。"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Choose Three Versions to Compare (Priority: P1)

Users select exactly three versions from the data pool to run a comparison and trigger on-demand cross-version summaries.

**Why this priority**: Enables the core "即選即算" value by letting users actively pick versions and get comparison output.

**Independent Test**: Can be fully tested by selecting three versions in any interface and confirming the temporary comparison output appears in the isolated location.

**Acceptance Scenarios**:

1. **Given** versions are available in the pool, **When** a user selects any three distinct versions, **Then** the system generates temporary cross-version summaries covering only those versions.
2. **Given** a user selects fewer or more than three versions, **When** they attempt to proceed, **Then** the system blocks the action and explains that exactly three versions are required.

---

### User Story 2 - Use Temporary Comparison Reports (Priority: P2)

Users download or visualize comparison outputs that reflect only the three selected versions and do not overwrite single-version summaries.

**Why this priority**: Ensures downstream consumption (downloads/visualization) aligns with the new temporary-report workflow and avoids corrupting per-version data.

**Independent Test**: Can be tested by opening download/visualization flows after a comparison run and verifying they read the temporary reports, or prompt for selection if absent.

**Acceptance Scenarios**:

1. **Given** a temporary comparison report set exists for the selected versions, **When** a user downloads or views comparison results, **Then** the system serves the temporary reports without overwriting single-version summaries.
2. **Given** no temporary comparison report exists, **When** a user tries to download or visualize comparison outputs, **Then** the system asks them to pick three versions and does not serve stale or partial data.

---

### User Story 3 - Maintain Version Pool Integrity (Priority: P3)

Operators keep the data folder as a version repository that only stores per-version outputs while allowing repeated on-demand comparisons without polluting the pool.

**Why this priority**: Protects stored version assets and keeps the pool clean from temporary cross-version artifacts.

**Independent Test**: Can be tested by loading versions to generate per-version summaries, verifying no cross-version files exist until a comparison is triggered, and confirming new comparisons do not alter stored single-version outputs.

**Acceptance Scenarios**:

1. **Given** versions are ingested or refreshed, **When** per-version summaries are generated, **Then** no cross-version summaries appear until a comparison selection is made.
2. **Given** multiple comparison runs occur over time, **When** new temporary reports are created, **Then** they remain isolated (e.g., under `result/<data-folder>/temp` or equivalent) and do not overwrite per-version summaries.

---

### Edge Cases

- Selecting the same version more than once when fewer than three distinct versions exist in the pool.
- Attempting comparison when fewer than three versions are present or a referenced version is missing or corrupted.
- Concurrent comparison requests targeting overlapping version sets and how their temporary outputs are isolated or named.
- Stale temporary reports left from a prior selection and how newer runs replace or segregate them without leaking old data.

### Assumptions & Dependencies

- The data pool already contains at least three distinct versions; otherwise the comparison flow blocks until enough versions are available.
- Temporary report storage is overwritten or cleaned on each new comparison run; long-term retention policies for temp outputs are handled operationally outside this scope.
- CLI, API, and UI share the same version pool and selection rules; access control for seeing versions is managed by existing authentication/authorization flows.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Treat the data folder as a version pool: loading data produces only per-version outputs and does not emit cross-version summaries by default.
- **FR-002**: Generate per-version `summary.csv` for each version during ingestion/read; do not generate cross-version `summary.csv`, `summary_stats.csv`, or `service_stats.csv` unless a comparison is explicitly requested.
- **FR-003**: Comparison flows in CLI, API, and UI MUST present available versions from the pool and require selection of exactly three distinct versions before proceeding.
- **FR-004**: If fewer or more than three versions are selected, block the action and return a clear message that exactly three versions are required.
- **FR-005**: Upon valid selection, produce temporary cross-version `summary.csv`, `summary_stats.csv`, and `service_stats.csv` that include only the chosen versions and reflect the latest per-version data.
- **FR-006**: Store temporary cross-version outputs in an isolated location (e.g., `result/<data-folder>/temp` or a sibling isolated name) that prevents overwriting any per-version summaries in the pool.
- **FR-007**: Non-comparison operations (e.g., data refresh, single-version views) MUST NOT create or update cross-version reports.
- **FR-008**: Download and visualization endpoints MUST read from the latest temporary comparison outputs when they exist; if absent, they MUST prompt users to pick three versions rather than serving stale or incomplete data.
- **FR-009**: Each new comparison run MUST replace or segregate prior temporary outputs so that each run reflects only its selected versions without leaking older selections.

### Key Entities *(include if feature involves data)*

- **Data Version**: A distinct dataset snapshot stored in the pool, identified by its version name and associated per-version summary.
- **Per-Version Summary**: The single-version `summary.csv` generated for each Data Version, used as the source for on-demand comparisons.
- **Temporary Comparison Report Set**: The cross-version `summary.csv`, `summary_stats.csv`, and `service_stats.csv` generated only after exactly three versions are selected; scoped to the selection and stored in an isolated temporary location.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of comparison attempts with exactly three distinct versions produce temporary cross-version reports in the isolated location within 2 minutes of submission.
- **SC-002**: 100% of attempts with fewer or more than three selected versions are blocked with an explanatory message before any report generation occurs.
- **SC-003**: For users who completed a valid comparison run, 95% of download/visualization requests serve the temporary reports corresponding to the most recent selection without requiring manual file navigation.
- **SC-004**: No per-version summaries are overwritten or modified by comparison runs across regression tests spanning at least three distinct selections.
- **SC-005**: Each new comparison run updates or isolates temporary outputs so that displayed results always match the latest selected three versions, verified across at least three successive runs with different version sets.
