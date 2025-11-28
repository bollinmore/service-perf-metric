# Implementation Plan: Three-Version Comparison Mode

**Branch**: `003-three-version-compare` | **Date**: 2025-11-28 | **Spec**: specs/003-three-version-compare/spec.md  
**Input**: Feature specification from `/specs/003-three-version-compare/spec.md`

## Summary

Shift to an on-demand three-version comparison model: keep the data folder as a version pool that only produces per-version summaries by default, require users to pick exactly three versions via CLI/API/UI to generate temporary cross-version reports, isolate temporary outputs to avoid overwriting per-version data, and update download/visualization flows to use those temporary reports. Add clear validation/error messages, logging, and documentation/tests covering selection rules, missing inputs (e.g., PerformanceLog), and temp report lifecycle.

## Technical Context

**Language/Version**: Python 3.11  
**Primary Dependencies**: Flask, pandas, plotly  
**Storage**: Local filesystem data pool and results (per-version summaries, temp cross-version outputs)  
**Testing**: pytest  
**Target Platform**: CLI + web UI on typical Linux/macOS environments  
**Project Type**: Single-service app with CLI/API/UI surfaces  
**Performance Goals**: Temp cross-version report generation completes within a couple of minutes for typical dataset sizes (per success criteria)  
**Constraints**: Exactly three distinct versions required for comparison; temporary outputs must not overwrite per-version summaries  
**Scale/Scope**: Version pool expected to hold multiple versions; comparison operations scoped to three-version selections

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Constitution file currently contains placeholders with no enforceable principles; proceeding with standard quality gates (testability, clarity, scope bounds) and noting absence of ratified rules.

## Project Structure

### Documentation (this feature)

```text
specs/003-three-version-compare/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/
├── models/
├── services/
├── cli/
└── lib/

tests/
├── contract/
├── integration/
└── unit/
```

**Structure Decision**: Use single-project layout rooted at `src/` with CLI/API/UI surfaces and `tests/` organized by contract/integration/unit.

## Phase 0: Research

- Resolve unknowns: temp report path/cleanup policy, CLI/API triggers and parameters, validation messaging, handling of missing artifacts (e.g., absent PerformanceLog), concurrency/isolation approach for repeated comparisons.
- Produce `research.md` with decisions (decision, rationale, alternatives).

## Phase 1: Design & Contracts

- Data model for version pool, per-version summary, and temporary comparison report set.
- API/CLI contract updates for listing versions and running three-version comparisons; clarify outputs/paths and error cases.
- Quickstart covering generate vs compare flow, selection rules, and temp outputs.
- Update agent context after artifacts are produced.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
