# Implementation Plan: Version Selector Modal

**Branch**: `004-version-selector-modal` | **Date**: 2025-11-28 | **Spec**: /Users/chenwensheng/Documents/Codes/bollinmore/service-perf-metric/specs/004-version-selector-modal/spec.md
**Input**: Feature specification from `/specs/004-version-selector-modal/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Replace the Analytics page Dataset dropdown with a gear-triggered settings modal that lists all version identifiers aggregated from datasets under the configured data folder, enforces a maximum of three selections with clear feedback, and applies the chosen versions to the comparison view on confirm. Existing backend flows currently assume exactly three versions under a single dataset path, so the plan accommodates accepting 1–3 `<dataset>/<version>` identifiers and refreshing lists per modal open.

## Technical Context

**Language/Version**: Python 3.11  
**Primary Dependencies**: Flask app serving a React/htm-based front-end, pandas/plotly for analytics views  
**Storage**: Local filesystem datasets under the configured `--data-folder`  
**Testing**: pytest suite (unit/integration/contract) plus manual UI checks for the Analytics page  
**Target Platform**: Web UI served from Flask on typical Linux/macOS dev environments  
**Project Type**: Web application (single backend with static front-end assets)  
**Performance Goals**: Apply confirmed selections to the comparison view within ~2 seconds; limit-select feedback within ~1 second (per spec success criteria)  
**Constraints**: Max three versions selectable; modal refreshes version list on open from data folder; avoid unrelated styling changes  
**Scale/Scope**: Moderate local datasets with multiple versions per dataset; expected dozens of versions aggregated, not large-scale multi-tenant traffic

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Constitution file currently contains placeholders with no enforceable principles; no gating violations identified. Proceeding with standard test and documentation expectations.

## Project Structure

### Documentation (this feature)

```text
specs/004-version-selector-modal/
├── plan.md              # This file (/speckit.plan output)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
├── checklists/
└── tasks.md             # Created by /speckit.tasks (later)
```

### Source Code (repository root)

```text
src/
├── webapp.py            # Flask app wiring routes/template data
├── ui/views/comparison.py
├── services/            # Dataset/version handling
├── api/                 # API endpoints
├── cli/                 # CLI entrypoints
├── config/
├── extract.py, report.py
└── lib/

templates/
└── index.html           # Main page template

static/
├── css/
└── js/app.js           # React/htm front-end bundle for Analytics UI

tests/
├── contract/
├── integration/
├── regression/
└── unit/
```

**Structure Decision**: Single Flask-backed web app serving a static React/htm UI; feature work touches `static/js/app.js` (Dataset dropdown/gear), related template wiring in `templates/index.html` and data provisioning in `src/webapp.py`/`src/ui/views/comparison.py`, with tests under `tests`.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |

## Post-Design Constitution Check

Re-validated after Phase 1 design: constitution remains placeholder-only; no additional gates triggered. Proceeding under standard testing and documentation expectations.
