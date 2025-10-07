---
description: "Task list for Service Latency Dashboard feature"
---

# Tasks: Service Latency Dashboard

**Input**: Design documents from `/specs/001-arguments/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Constitution requires validation tasks for every story. Include test execution, data-quality checks, and evidence capture explicitly.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions
- Observability assets live under `observability/`
- Tests under `tests/`
- Evidence artifacts stored beneath `artifacts/`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm local tooling, secrets, and repositories before foundational work begins.

- [ ] T001 Install Python 3.11 toolchain and `pipx` environment per quickstart (`scripts/setup/python-env.sh` if available).
- [ ] T002 [P] Configure Grafana admin token and Loki credentials in `.env.observability.local` (document in `docs/local-setup.md`).
- [ ] T003 [P] Generate skeleton `artifacts/` directories (`artifacts/data-quality/`, `artifacts/evidence/`, `artifacts/threshold-updates/`).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Establish ingestion scaffolding, data-quality enforcement, and baseline configurations required by all user stories.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T004 Validate `make ingest-latency-metrics deps` installs dependencies and update `observability/jobs/log_parser_requirements/requirements.txt` + `log-parser.lock` if drift detected.
- [ ] T005 Implement Loki query client in `observability/jobs/ingest_latency_metrics.py` to pull 7-day log slices with schema version tagging.
- [ ] T006 Add Great Expectations suite `tests/data-quality/expectations/log_latency_suite.json` covering request counts ≥0, non-null latency, schema version checks.
- [ ] T007 [P] Wire Prometheus Pushgateway client helper in `observability/jobs/ingest_latency_metrics.py` with configurable target gateway URL.
- [ ] T008 [P] Create config loader in `observability/jobs/config_loader.py` supporting per-service overrides from `observability/config/alert-rules.yaml`.
- [ ] T009 Establish pytest fixture scaffolding `tests/conftest.py` for synthetic log snapshots shared across tests.
- [ ] T010 Seed sample service metadata in `observability/config/services.yaml` for local validation (align with data model fields).
- [ ] T011 Document foundational setup validation outcomes in `docs/foundational-validation.md` including screenshots/log excerpts.

**Checkpoint**: Foundation ready – ingestion job callable locally with validated data-quality gates.

---

## Phase 3: User Story 1 - Monitor service latency (Priority: P1) 🎯 MVP

**Goal**: Feature engineers can view P95 latency for their owned service over the default 7-day window with breach highlighting.

**Independent Test**: Run ingestion job against synthetic logs, open Grafana dashboard filtered to a service, and observe P95 trend plus breach annotation.

### Tests & Evidence for User Story 1 ⚠️

- [ ] T012 [P][US1] Add pytest unit tests in `tests/unit/observability/test_ingest_latency_metrics.py` covering P95 computation and Pushgateway payload structure.
- [ ] T013 [P][US1] Add integration test `tests/integration/observability/test_p95_pipeline.py::test_p95_seven_day_window` simulating Loki responses.
- [ ] T014 [US1] Extend Great Expectations suite with variance check ensuring ≥3 buckets for baseline comparison.
- [ ] T015 [P][US1] Create synthetic log fixtures under `tests/fixtures/logs/p95_regression.json` for regression scenario.
- [ ] T016 [US1] Plan alert dry-run and evidence capture documented in `specs/001-arguments/tasks.md` once executed.

### Implementation for User Story 1

- [ ] T017 [P][US1] Implement ingestion aggregation logic in `observability/jobs/ingest_latency_metrics.py` to compute 5-minute buckets and push P95 metrics.
- [ ] T018 [P][US1] Add baseline comparison helper `observability/jobs/baseline.py` loading rolling 7-day P95 per service.
- [ ] T019 [US1] Implement API endpoint `/api/services/owned` in `observability/api/services.py` using EngineerAccess data.
- [ ] T020 [US1] Implement GET `/api/services/{serviceId}/latency` in `observability/api/latency.py` following contract.
- [ ] T021 [P][US1] Implement GET `/api/services/{serviceId}/alert-threshold` and POST update handler in `observability/api/thresholds.py` with validation bounds 50–1000 ms.
- [ ] T022 [US1] Provision Grafana dashboard JSON `observability/dashboards/service-latency-dashboard.json` with default 7-day window, P95 charts, breach annotation.
- [ ] T023 [P][US1] Configure PagerDuty alert rule in `observability/config/alert-rules.yaml` and sync via automation script.
- [ ] T024 [US1] Update quickstart instructions in `specs/001-arguments/quickstart.md` with command adjustments discovered during implementation.
- [ ] T025 [US1] Capture evidence bundle: dashboard screenshot (`artifacts/evidence/dashboard.png`), pytest logs, data-quality report, alert dry-run transcript.

**Checkpoint**: User Story 1 delivers functioning dashboard with evidence package and can be independently demonstrated.

---

## Phase N: Polish & Cross-Cutting Concerns

**Purpose**: Harden solution, ensure documentation completeness, and prepare for rollout.

- [ ] T026 [P] Conduct load test of ingestion job (200 services) and document results in `docs/perf/p95_ingestion.md`.
- [ ] T027 [P] Review Grafana access controls, ensuring EngineerAccess mappings reflected; update `observability/docs/access-control.md`.
- [ ] T028 [P] Perform security review checklist focusing on credentials storage (`docs/security/observability-latency-checklist.md`).
- [ ] T029 Final cleanup: remove obsolete fixtures, re-run linting/formatting (`make observability-format` if available).
- [ ] T030 Prepare rollout notes in `docs/release-notes/service-latency-dashboard.md` summarizing metrics impact and validation outcomes.

---

## Dependencies & Execution Order

### Phase Dependencies
- **Setup (Phase 1)** → completes before Foundational.
- **Foundational (Phase 2)** → must finish before User Story 1 tasks begin.
- **User Story 1 (Phase 3)** → MVP; all later polish depends on US1 completion.
- **Polish** → can run after User Story 1, with tasks marked [P] parallelizable.

### User Story Dependencies
- **User Story 1 (P1)**: Depends on foundational ingestion, config, and tests scaffolding.

### Within User Story 1
- Tests (T012–T016) run before implementation tasks T017 onward.
- API handlers (T019–T021) depend on ingestion outputs (T017–T018).
- Dashboard provisioning (T022) depends on API data availability.
- Evidence capture (T025) last after functionality verified.

### Parallel Opportunities
- T002/T003 setup steps can run in parallel.
- Foundational tasks T007 & T008 operate on distinct modules.
- US1 tasks T017 and T018 can execute concurrently; similarly T019/T021 once ingestion complete.
- Polish tasks T026–T028 run independently after US1.

---

## Parallel Example: User Story 1

```bash
# Run in parallel once foundational work completed:
Task: "Implement ingestion aggregation logic in observability/jobs/ingest_latency_metrics.py" (T017)
Task: "Add baseline comparison helper observability/jobs/baseline.py" (T018)
Task: "Implement GET /api/services/{serviceId}/latency in observability/api/latency.py" (T020)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)
1. Complete Phase 1 Setup.
2. Finish Phase 2 Foundational tasks to establish ingestion and configs.
3. Deliver User Story 1 end-to-end with evidence capture (tests + dashboard + alert).
4. Validate MVP via quickstart flow and evidence bundle.

### Incremental Delivery
1. Release MVP (User Story 1) to feature engineers.
2. Gather feedback, then extend with additional user stories (e.g., team roll-ups, comparative trends) in future iterations.
3. Apply polish tasks before broad rollout.

### Parallel Team Strategy
- Engineer A: Ingestion logic + data-quality (T004–T018).
- Engineer B: API layer + config management (T019–T023).
- Engineer C: Dashboard provisioning + evidence capture (T022, T025, polish tasks).

---

## Notes
- [P] tasks = different files, no dependencies.
- [Story] label maps task to specific user story for traceability.
- Each user story should be independently completable and testable.
- Verify tests fail before implementing.
- Capture baseline measurements and attach evidence links as tasks complete.
- Commit after each task or logical group.
- Stop at any checkpoint to validate story independently.
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence.
