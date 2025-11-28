# Implementation Plan: User-Defined Version Comparison for Test Data

**Branch**: `002-user-version-compare` | **Date**: 2025-11-28 | **Spec**: specs/002-user-version-compare/spec.md
**Input**: Feature specification from `/specs/002-user-version-compare/spec.md`

## Summary

Enable users to choose which test-data versions to compare by auto-scanning a configurable base folder and letting users select 2–4 versions per run, with validation, refresh on selection change, and clear handling of missing or mismatched data. CLI `spm.py` requires `--data-folder` and optional `--versions` list for preselection. Uploads accept one zip at a time, enforcing `<tool-version>/PerformanceLog/*.log` structure. Implementation will use Python 3.11 with existing Flask/pandas stack; filesystem discovery of immediate subfolders under an admin-configured base path; comparisons refreshed within 5 seconds for standard datasets; logging of selections and errors for traceability.

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: Python 3.11  
**Primary Dependencies**: Flask, pandas, plotly  
**Storage**: Local filesystem (test-data base folder, read-only to users)  
**Testing**: pytest + ruff  
**Target Platform**: Local/CI execution on supported OS (CLI/Flask service)  
**Project Type**: Single backend/CLI service  
**Performance Goals**: Refresh updated comparisons within 5 seconds for standard datasets (2–4 versions)  
**Constraints**: Compare 2–4 versions per run; base path configurable by admins only; avoid loading outside configured base path; uploads must be single zip with `<tool-version>/PerformanceLog/*.log`  
**Scale/Scope**: Moderate dataset sizes per version; concurrency limited to typical local/CI usage

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- Current constitution file is placeholder/empty; no enforceable principles specified. Proceeding under default engineering standards. If a real constitution is added later, re-verify gates.
- Post-Phase-1 recheck: no new constitution content; still no explicit gates to violate.

## Project Structure

### Documentation (this feature)

```text
specs/002-user-version-compare/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks, later)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```text
src/
├── cli/
├── services/
├── models/
└── lib/

tests/
├── unit/
├── integration/
└── contract/
```

**Structure Decision**: Single-project structure already present (`src/`, `tests/`); implement discovery/comparison logic under `src/services` with CLI/Flask entry points in `src/cli`, and add corresponding tests under `tests/`.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
