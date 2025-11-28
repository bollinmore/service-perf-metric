# Tasks: User-Defined Version Comparison for Test Data

**Input**: Design documents from `/specs/002-user-version-compare/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Not explicitly requested; focus on implementation tasks.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Create base data-folder and logging config entries (or module) in `src/config.py` to be consumed by CLI and services.
- [ ] T002 Wire `spm.py` startup to load config and fail fast with a clear message when `--data-folder` is missing.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

- [ ] T003 Implement CLI arg parsing for `--data-folder` (required) and optional `--versions` (comma-separated) in `spm.py`.
- [ ] T004 [P] Add base-path validation and version-list parsing utilities in `src/lib/path_utils.py`.
- [ ] T005 [P] Implement version discovery that scans immediate subfolders for `<tool-version>/PerformanceLog/*.log` in `src/services/version_discovery.py`.
- [ ] T006 Add single-zip upload structure validator enforcing `<tool-version>/PerformanceLog/*.log` in `src/services/upload_validator.py`.
- [ ] T007 [P] Add logging/tracing helper to record selections, uploads, and errors with timestamps in `src/lib/logging.py`.

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Choose Versions to Compare (Priority: P1) ✅ MVP

**Goal**: Let users choose 2–4 available versions discovered under the configured base path and run a comparison.

**Independent Test**: Select two available versions (via CLI or API), run comparison, and see results using only those selections; blocked if fewer than two are chosen.

### Implementation for User Story 1

- [ ] T008 [US1] Wire `spm.py` to require validated base path and optional preselected versions, invoking discovery/validation before comparison start.
- [ ] T009 [P] [US1] Expose versions listing endpoint/handler (`GET /versions`) using discovery service in `src/cli/api.py` (Flask route) or equivalent CLI command in `spm.py`.
- [ ] T010 [US1] Implement selection validation enforcing 2–4 unique versions with clear errors in `src/services/selection_service.py`.
- [ ] T011 [US1] Implement comparison initiation to load selected versions and label outputs in `src/services/comparison_service.py`.

**Checkpoint**: User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Update Selection and Refresh Results (Priority: P2)

**Goal**: Allow users to change selected versions and refresh comparison results quickly without restarting.

**Independent Test**: Run a comparison, adjust selection, and verify refreshed results with correct labels within ~5 seconds for standard datasets.

### Implementation for User Story 2

- [ ] T012 [US2] Add comparison refresh flow to rerun with new selections without restarting in `src/services/comparison_service.py`.
- [ ] T013 [P] [US2] Add CLI/endpoint handler to accept updated selections and trigger refresh with a 5-second target in `spm.py` or `src/cli/api.py`.
- [ ] T014 [US2] Ensure comparison cache/state resets between runs to avoid stale metrics in `src/services/comparison_service.py`.

**Checkpoint**: User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Handle Missing or Incompatible Data (Priority: P3)

**Goal**: Detect missing/incompatible data and enforce upload structure; guide users to resolve issues.

**Independent Test**: Submit a version with missing logs or schema mismatch; system flags the issue, excludes or requests adjustment; uploads with bad structure are rejected.

### Implementation for User Story 3

- [ ] T015 [US3] Implement single-zip upload endpoint/CLI command using the validator to enforce `<tool-version>/PerformanceLog/*.log` in `src/cli/uploads.py` (or `spm.py` handler).
- [ ] T016 [P] [US3] Add checks for missing logs per version and surface actionable errors in `src/services/version_discovery.py`.
- [ ] T017 [US3] Implement schema/metric conflict detection with user-facing guidance in `src/services/comparison_service.py`.
- [ ] T018 [P] [US3] Emit structured logs for rejected uploads and invalid versions in `src/lib/logging.py`.

**Checkpoint**: All user stories should now be independently functional

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T019 [P] Update usage docs with CLI flags, upload rules, and examples in `specs/002-user-version-compare/quickstart.md` and `README.md`.
- [ ] T020 Run end-to-end CLI/API smoke validation for SC-001 to SC-007 and capture notes in `docs/validation.md`.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately.
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories.
- **User Stories (Phase 3+)**: All depend on Foundational completion; proceed in priority order (P1 → P2 → P3) or in parallel if capacity allows.
- **Polish (Phase 6)**: Depends on all desired user stories being complete.

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational; no dependencies on other stories.
- **User Story 2 (P2)**: Depends on User Story 1 comparison initiation being available; otherwise independent.
- **User Story 3 (P3)**: Depends on discovery and comparison services from User Story 1.

### Within Each User Story

- Validate inputs before running comparison.
- Services before handlers/endpoints.
- Refresh/error handling after base comparison flow exists.

### Parallel Opportunities

- Foundational utilities (T004, T005, T007) can proceed in parallel.
- US1 listing (T009) can proceed in parallel with selection validation (T010) once discovery exists.
- US2 handler (T013) can proceed in parallel with cache reset work (T014).
- US3 logging (T018) can proceed in parallel with upload handler (T015) once validator exists.

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. Validate US1 end-to-end (selection, compare, errors)
5. Deploy/demo if ready

### Incremental Delivery

1. Setup + Foundational → foundation ready
2. Add User Story 1 → test independently → demo (MVP)
3. Add User Story 2 → test independently → demo
4. Add User Story 3 → test independently → demo

### Parallel Team Strategy

1. Team completes Setup + Foundational together.
2. After Foundational:
   - Developer A: User Story 1
   - Developer B: User Story 2
   - Developer C: User Story 3
3. Integrate and polish.
