# Tasks - Version Selector Modal

## Overview
- **Branch**: `004-version-selector-modal`
- **Spec**: /Users/chenwensheng/Documents/Codes/bollinmore/service-perf-metric/specs/004-version-selector-modal/spec.md
- **Plan**: /Users/chenwensheng/Documents/Codes/bollinmore/service-perf-metric/specs/004-version-selector-modal/plan.md
- **Scope**: Replace Dataset dropdown with gear-triggered modal, list all versions across datasets, cap selection at three with feedback, apply selections to comparison.

## Dependencies (Story Order)
1. US1 (P1) → Core selection flow
2. US2 (P2) → Selection cap and feedback
3. US3 (P3) → Reopen and adjust selections

Parallelizable examples:
- Frontend modal UI wiring vs. backend version listing contract alignment (non-conflicting files)
- Sorting/deduping logic vs. modal trigger placement
- Tests for selection cap vs. version list refresh behavior

## Phase 1 - Setup
- [X] T001 Ensure data folder path is configurable for local runs (documented in quickstart.md)
- [X] T002 Confirm dev server runs with Analytics page accessible (`python spm.py serve --data-folder <path>`)

## Phase 2 - Foundational
- [X] T003 Review current Analytics UI entry point and dataset control container in static/js/app.js and templates/index.html
- [X] T004 Identify backend data provisioning for datasets/versions in src/webapp.py and src/ui/views/comparison.py
- [X] T005 Verify existing version listing API/contract (src/api/routes/versions.py) matches `<dataset>/<version>` id needs; note gaps

## Phase 3 - User Story 1 (P1) - Select versions for comparison
- [X] T006 [US1] Replace Dataset dropdown markup with gear icon button in templates/index.html (Analytics control area)
- [X] T007 [P] [US1] Wire gear button handler to open/close settings modal in static/js/app.js
- [X] T008 [P] [US1] Implement modal structure and version list rendering in static/js/app.js
- [X] T009 [P] [US1] Build version list aggregation (dataset + version) sorted by dataset then version in static/js/app.js
- [X] T010 [US1] Refresh version list on each modal open by calling versions API with data folder param
- [X] T011 [US1] Apply confirmed selections (1–3 ids) to comparison state and close modal in static/js/app.js
- [X] T012 [US1] Adjust backend comparison handling to accept 1–3 `<dataset>/<version>` identifiers instead of exactly three in src/services/comparison.py and src/api/routes/comparisons.py
- [X] T013 [US1] Add manual check notes for gear visibility, modal open/close, selection apply path in quickstart.md

## Phase 4 - User Story 2 (P2) - Enforce selection limit with feedback
- [X] T014 [US2] Enforce hard cap of three selections; block fourth while preserving existing selections in static/js/app.js
- [X] T015 [P] [US2] Display inline feedback explaining the three-version limit (copy/location per spec) in static/js/app.js
- [X] T016 [US2] Add test or manual check coverage for cap enforcement and feedback in tests/regression or quickstart.md

## Phase 5 - User Story 3 (P3) - Review or adjust selections later
- [X] T017 [US3] Preselect current active selections when reopening modal in static/js/app.js
- [X] T018 [US3] Handle stale/missing selections gracefully (mark unavailable, prevent confirm) in static/js/app.js
- [X] T019 [US3] Ensure confirm/cancel behaviors align: confirm updates selection; cancel/close leaves prior selection unchanged in static/js/app.js
- [X] T020 [US3] Add manual check notes for reopen/edit flow and stale selection handling in quickstart.md
- [X] T025 [US3] Implement empty-state UI when no versions are returned (messaging + disabled Confirm) in static/js/app.js
- [X] T026 [US3] Document empty-state manual check in quickstart.md

## Phase 6 - Polish & Cross-Cutting
- [X] T021 Validate dedupe/disambiguation: dataset + version labeling and sorting confirmed against data-model.md and research.md
- [X] T022 Align contracts and UI identifiers with `<dataset>/<version>` canonical form in specs/004-version-selector-modal/contracts/*.yaml and frontend calls
- [X] T023 Add accessibility passes: focus trap, aria labels for gear and modal controls in static/js/app.js and templates/index.html
- [X] T024 Update docs/checklists if wording or flows changed (specs/004-version-selector-modal/checklists/ux.md)
- [X] T027 [US1] Enforce Confirm disabled until at least one selection exists in static/js/app.js and note in quickstart.md
- [X] T028 Define validation steps for SC-001–SC-005 (visibility, timing, list completeness, cap feedback timing) in quickstart.md or tests
- [X] T029 Decide and document UX for version-list fetch failure vs true “no versions”; update quickstart.md accordingly

## Independent Test Criteria by Story
- US1: Can open modal via gear, see aggregated version list, select 1–3, confirm applies to comparison.
- US2: With three selected, a fourth attempt is blocked with clear inline feedback; prior selections remain.
- US3: Reopen shows current selections preselected; can adjust; stale items are flagged and cannot be confirmed; cancel leaves state unchanged.

## Implementation Strategy
- Deliver MVP with US1 (modal, list, selection apply).
- Layer in selection cap/feedback (US2) next.
- Add reopen/edit robustness and stale handling (US3), then polish (a11y, docs alignment).
