# Implementation Plan: Dev/Production Mode Toggle

**Branch**: `001-dev-prod-toggle` | **Date**: 2025-11-27 | **Spec**: specs/001-dev-prod-toggle/spec.md
**Input**: Feature specification from `/specs/001-dev-prod-toggle/spec.md`

## Summary

Add an environment variable in `.env` to toggle Development vs Production behavior; the toggle only affects local runs (`python spm.py serve`), while Docker deployments remain forced to Production. Update README with usage instructions and ensure documentation and contracts reflect the mode toggle and readiness expectations.

## Technical Context

**Language/Version**: Python 3.11 (assumed from typical Flask/pandas stack)  
**Primary Dependencies**: Flask, pandas, plotly  
**Storage**: File-based/local data (no explicit DB usage observed)  
**Testing**: pytest (assumed; none specified)  
**Target Platform**: Local development via `python spm.py serve`; Docker deployment for production  
**Project Type**: Single backend/CLI-style Python service  
**Performance Goals**: Responsive local serve suitable for dashboards (no specific SLA stated)  
**Constraints**: Docker deployments must always run Production mode regardless of `.env` toggle  
**Scale/Scope**: Single service with local dashboard usage; limited concurrent users expected

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Constitution file is placeholder with no enforceable principles; no gates identified. Proceeding with standard quality checks and auditability of mode changes. Post-design review: still no conflicts detected.

## Project Structure

### Documentation (this feature)

```text
specs/001-dev-prod-toggle/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
└── checklists/
```

### Source Code (repository root)
```text
src/
├── __init__.py
├── ... (service modules)

spm.py
templates/
static/
docs/
README.md
docker-compose.yml
Dockerfile
```

**Structure Decision**: Single Python service with CLI/serve entrypoint (`spm.py`), templates/static for UI, docs and specs housed under `specs/001-dev-prod-toggle`.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |
