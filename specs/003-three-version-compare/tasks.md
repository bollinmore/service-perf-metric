# Tasks: Three-Version Comparison Mode

**Input**: Design documents from `/specs/003-three-version-compare/`  
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests requested (selection validation, missing artifacts, temp outputs) per spec/research; include per-story tests below.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Ensure baseline config and tooling for temp outputs and logging.

- [X] T001 Define temp output root and latest-pointer constants in `src/config/paths.py`
- [X] T002 [P] Add comparison run ID generator utility in `src/lib/run_ids.py`
- [X] T003 [P] Ensure logging configuration supports comparison operations in `src/lib/logging_config.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core utilities and data access required by all stories.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 Implement version pool scanner (list versions, statuses, summaries) in `src/services/version_pool.py`
- [X] T005 [P] Add validation helpers for “exactly three distinct versions” and missing artifacts in `src/services/validation.py`
- [X] T006 [P] Create temp storage manager (create `result/<data-folder>/temp/<run-id>/`, manage `latest`) in `src/services/temp_storage.py`
- [X] T007 Seed shared test fixtures for data folders, summaries, and missing PerformanceLog cases in `tests/conftest.py`

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Choose Three Versions to Compare (Priority: P1) 🎯 MVP

**Goal**: Users select exactly three versions and trigger on-demand cross-version summaries without touching per-version outputs.

**Independent Test**: Selecting any three distinct versions generates temp cross-version reports under the isolated temp path; invalid counts or duplicates are blocked with clear errors.

### Tests for User Story 1

- [X] T008 [P] [US1] Contract test for `POST /comparisons` in `tests/contract/test_comparisons_post.py`
- [X] T009 [P] [US1] CLI integration test for `compare --data-folder <pool> --versions v1 v2 v3` in `tests/integration/test_cli_compare.py`
- [X] T010 [P] [US1] Validation test for missing PerformanceLog or missing version in `tests/unit/test_validation.py`

### Implementation for User Story 1

- [X] T011 [P] [US1] Expose version listing via `GET /versions` using pool scanner in `src/api/routes/versions.py`
- [X] T012 [US1] Implement comparison request handler `POST /comparisons` with validation and run creation in `src/api/routes/comparisons.py`
- [X] T013 [P] [US1] Implement comparison orchestrator (validation → temp run directory → generate `summary.csv`, `summary_stats.csv`, `service_stats.csv`) in `src/services/comparison.py`
- [X] T014 [US1] Update CLI to require exactly three versions and call comparison API in `src/cli/commands/compare.py`
- [X] T015 [US1] Ensure comparison generation fails fast on missing artifacts and reports clear error messages in `src/services/comparison.py`
- [X] T016 [US1] Wire logging for comparison runs (inputs, run-id, temp paths, errors) in `src/lib/logging_config.py`

**Checkpoint**: User Story 1 fully functional and testable independently

---

## Phase 4: User Story 2 - Use Temporary Comparison Reports (Priority: P2)

**Goal**: Downloads/visualizations consume the latest temp comparison outputs; prompt users to select versions when none exist.

**Independent Test**: After a valid comparison, download/visualization reads `temp/latest` outputs; when absent, users are prompted to pick three versions instead of seeing stale data.

### Tests for User Story 2

- [X] T017 [P] [US2] Contract test for `GET /comparisons/latest` in `tests/contract/test_comparisons_latest.py`
- [X] T018 [P] [US2] Integration test for download/visualization fallback when no latest comparison exists in `tests/integration/test_visualization_fallback.py`

### Implementation for User Story 2

- [X] T019 [P] [US2] Implement `GET /comparisons/latest` to return selected versions, status, and temp paths in `src/api/routes/comparisons.py`
- [X] T020 [US2] Update visualization/data-access layer to read `result/<data-folder>/temp/latest/` outputs in `src/services/visualization.py`
- [X] T021 [US2] Update download handlers to serve temp comparison files or prompt selection when missing in `src/api/routes/downloads.py`
- [X] T022 [US2] Update UI workflow to request versions from pool, submit three-version selection, and reload outputs in `src/ui/views/comparison.py`
- [X] T023 [US2] Update CLI download/view commands to prefer temp outputs and prompt when absent in `src/cli/commands/download.py`

**Checkpoint**: User Story 2 fully functional and testable independently

---

## Phase 5: User Story 3 - Maintain Version Pool Integrity (Priority: P3)

**Goal**: Keep the data folder as a clean version pool; prevent cross-version outputs during generate and avoid overwriting per-version summaries.

**Independent Test**: Generating per-version summaries never emits cross-version files; repeated comparisons isolate outputs per run-id and clean old temp folders without touching per-version summaries.

### Tests for User Story 3

- [X] T024 [P] [US3] Regression test to ensure generate flow only creates per-version summaries in `tests/integration/test_generate_single_version.py`
- [X] T025 [P] [US3] Concurrency/isolation test for overlapping comparisons and latest-pointer updates in `tests/integration/test_comparison_isolation.py`
- [X] T026 [P] [US3] Non-overwrite test for per-version summaries across multiple comparisons in `tests/unit/test_temp_storage.py`

### Implementation for User Story 3

- [X] T027 [US3] Refactor generate/read workflow to emit only per-version `summary.csv` in `src/services/generate.py`
- [X] T028 [P] [US3] Add cleanup policy: on successful comparison, delete previous temp run folder after updating `latest` in `src/services/temp_storage.py`
- [X] T029 [US3] Protect per-version summaries from modification during comparisons (read-only enforcement) in `src/services/comparison.py`
- [X] T030 [US3] Ensure non-comparison flows (refresh, single-view) never create/update cross-version outputs in `src/api/routes/versions.py`

**Checkpoint**: All user stories independently functional; pool integrity protected

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T031 [P] Refresh quickstart with new compare flow and temp paths in `specs/003-three-version-compare/quickstart.md`
- [X] T032 [P] Update README/docs/quickstart usage examples for CLI/API/UI selection rules in `README.md`
- [X] T033 [P] Add logging/monitoring notes for comparison runs and temp cleanup in `docs/observability.md`
- [X] T034 Run full regression of CLI/API/UI compare and download flows following quickstart in `tests/regression/test_compare_end_to_end.py`

---

## Dependencies & Execution Order

- Phase ordering: Setup → Foundational → US1 (P1) → US2 (P2) → US3 (P3) → Polish.
- US1 must complete before US2/US3 consumption of temp outputs; US2 depends on latest-pointer availability from US1; US3 depends on generate/read refactor and temp storage policies from US1.

### User Story Dependency Graph
- US1 (P1) → US2 (P2) (needs latest temp outputs)
- US1 (P1) → US3 (P3) (shares comparison pipeline; integrity relies on US1 temp handling)
- US2 and US3 can proceed in parallel after US1.

### Parallel Execution Examples
- US1: Run T008, T009, T010 in parallel; T011 and T013 in parallel; T012 and T014 depend on validation from T005/T006.
- US2: T017 and T018 in parallel; T019 and T020 in parallel; T021/T022/T023 can proceed once latest endpoint exists.
- US3: T024, T025, T026 in parallel; T027 before T028/T029; T030 can proceed after T027.

---

## Implementation Strategy

- MVP: Deliver US1 after Setup + Foundational, validate compare command and API create temp outputs with strict three-version rule.
- Incremental: Add US2 to consume temp outputs; then US3 to harden generate flow and cleanup/integrity.
- Testing-first: Execute contract/integration/unit tests per story before implementation tasks; ensure failures before code.
