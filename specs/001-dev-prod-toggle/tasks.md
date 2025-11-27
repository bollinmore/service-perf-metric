# Tasks: Dev/Production Mode Toggle

**Input**: Design documents from `/specs/001-dev-prod-toggle/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Not explicitly requested; focus on implementation and observable behavior per spec. Add tests if discovered during implementation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Ensure environment configuration and dependencies support mode toggling.

- [ ] T001 Add `python-dotenv` (or confirm existing) to `requirements.txt` for `.env` loading.
- [ ] T002 Create/update `.env.example` with `SPM_MODE=development` and note allowed values.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core configuration and service scaffolding required before user stories.

- [ ] T003 Implement environment loader for `SPM_MODE` with default `development` and invalid-value warning in `src/config.py`.
- [ ] T004 Wire `spm.py` serve bootstrap to use the env loader and expose active mode metadata to downstream services.
- [ ] T005 Create mode/readiness service scaffold (snapshot storage, readiness data structure, logging hooks) in `src/services/mode_service.py`.

**Checkpoint**: Foundation ready - user story implementation can now begin.

---

## Phase 3: User Story 1 - Toggle to Production with Dev Version Preserved (Priority: P1) 🎯 MVP

**Goal**: Allow local users to switch to Production mode while preserving the current development version.

**Independent Test**: From Development with a saved dev version, switch to Production via API/serve toggle; verify Production state is active and dev snapshot remains accessible.

### Implementation for User Story 1

- [ ] T006 [US1] Implement mode status model (mode, source, validated, snapshot) with persistence hooks in `src/services/mode_service.py`.
- [ ] T007 [US1] Add dev version snapshot capture before Production switch in `src/services/mode_service.py`.
- [ ] T008 [US1] Expose `/mode` GET/POST per contract in `spm.py` (or Flask blueprint) applying local-only toggle logic and snapshot preservation.
- [ ] T009 [P] [US1] Add mode-switch logging (user/time/result/notes) in `src/services/mode_service.py` and ensure log output during `python spm.py serve`.
- [ ] T010 [US1] Display active mode and preserved dev version in serve startup output or status UI in `spm.py` and related `templates/` assets.

**Checkpoint**: User Story 1 functional and testable independently.

---

## Phase 4: User Story 2 - Validate Production Readiness Before Deploy (Priority: P2)

**Goal**: Block Production readiness when required configuration is incomplete and surface guidance.

**Independent Test**: With `SPM_MODE=production`, attempt switch; if required readiness items missing, switch is blocked with guidance; when items satisfied, readiness reports complete.

### Implementation for User Story 2

- [ ] T011 [US2] Implement readiness checklist evaluation (required items, statuses, messages) in `src/services/readiness.py` (or within `mode_service.py`).
- [ ] T012 [US2] Integrate readiness validation into Production switch handler in `spm.py`, returning failure details when incomplete.
- [ ] T013 [P] [US2] Expose `/mode/readiness` GET endpoint per contract in `spm.py` returning checklist status.
- [ ] T014 [US2] Document readiness requirements and expected switch behavior in `README.md` under deployment instructions.

**Checkpoint**: User Story 2 functional and testable independently.

---

## Phase 5: User Story 3 - Revert to Development After Production Prep (Priority: P3)

**Goal**: Restore preserved development version after Production prep without reconfiguration.

**Independent Test**: From Production mode, trigger revert; system restores dev snapshot and clears Production overrides, confirming Development state.

### Implementation for User Story 3

- [ ] T015 [US3] Implement revert-to-development flow using preserved snapshot in `src/services/mode_service.py` (restore config/state).
- [ ] T016 [US3] Add API/serve action to revert (extend `/mode` POST or separate route) in `spm.py` with confirmations.
- [ ] T017 [P] [US3] Ensure invalid/absent `SPM_MODE` falls back to Development with warning in `src/config.py` and reflected in status outputs.

**Checkpoint**: User Story 3 functional and testable independently.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentation and consistency across deployment modes.

- [ ] T018 [P] Update `quickstart.md` and `docs/` (if referenced) to align with `.env` toggle and Docker forced-Production behavior.
- [ ] T019 Verify Docker defaults enforce `SPM_MODE=production` in `Dockerfile` and `docker-compose.yml` without reading repo `.env`.
- [ ] T020 Run end-to-end manual check following README/quickstart for local serve and Docker to confirm parity.

---

## Dependencies & Execution Order

### Phase Dependencies
- Setup (Phase 1) → Foundational (Phase 2) → User Stories (Phases 3–5) → Polish (Phase 6).

### User Story Dependencies (priority order)
- US1 (P1) enables base toggle and snapshot handling; US2 builds on toggle to enforce readiness; US3 relies on snapshot from US1 to revert. Execute sequentially for minimal rework (US1 → US2 → US3).

### Within Each User Story
- Implement service logic before wiring endpoints; ensure readiness logic is in place before validating switch outcomes; logging/UI updates follow core logic.

## Parallel Opportunities
- Parallel tasks: T009, T013, T017, T018, T019 can run alongside adjacent story work after dependencies complete.
- Different developers can tackle US1 vs US2 vs US3 once Foundational tasks are done, with coordination on `spm.py` merge points.

## Implementation Strategy
- MVP: Complete Phases 1–3 to deliver local mode toggle with snapshot preservation and status visibility.
- Incremental: Add readiness blocking (Phase 4) next, then revert flow (Phase 5); finish with docs and Docker verification (Phase 6).
