# Implementation Plan: Service Latency Dashboard

**Branch**: `001-arguments` | **Date**: 2025-10-07 | **Spec**: [/Users/chenwensheng/Documents/Codes/bollinmore/service-perf-metric/specs/001-arguments/spec.md]
**Input**: Feature specification from `/specs/001-arguments/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Build a Grafana-based dashboard that surfaces per-service P95 latency derived from parsed application logs so feature engineers can spot regressions quickly. Delivery covers hardening the `make ingest-latency-metrics` ingestion job, provisioning dashboard panels with a default 7-day window, wiring PagerDuty alerts on sustained P95 breaches, and documenting evidence outputs that satisfy observability governance.

## Technical Context

**Language/Version**: Python 3.11 (ingestion job), Grafana 10 provisioning  
**Primary Dependencies**: Grafana, Loki log API, Prometheus Pushgateway SDK, Pandas 2.x  
**Storage**: Loki (raw logs), Prometheus/Thanos (aggregated latency series)  
**Testing**: pytest with snapshot fixtures, Great Expectations for data-quality gates  
**Target Platform**: Kubernetes CronJob + ConfigMaps for Grafana dashboard provisioning  
**Project Type**: single (observability assets and jobs stored within repo)  
**Performance Goals**: Dashboard 7-day view loads under 5 s; ingestion job computes P95 for 200 services within 4 minutes  
**Constraints**: End-to-end data freshness ≤10 minutes; ingestion container memory budget ≤2 GiB  
**Scale/Scope**: ~200 production services, ~5M log lines per hour across fleet

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- ✅ Data sources, ownership, and extraction cadence documented (parsed application logs via Observability Platform every 5 minutes).
- ✅ Reproducible execution path defined: `make ingest-latency-metrics` builds `obs/log-parser:latest` with `log-parser.lock` dependencies.
- ✅ Observability plan includes dashboard panels, PagerDuty alert, and runbook `docs/runbooks/latency.md`.
- ✅ Baseline and targets captured (7-day rolling P95 baseline, default breach threshold ≤350 ms, variance alert expectations).
- ✅ Incremental delivery slices identified starting with feature-engineer dashboard story; future stories extend comparisons and team roll-ups.

## Project Structure

### Documentation (this feature)

```
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```
observability/
├── dashboards/
│   └── service-latency-dashboard.json
├── jobs/
│   ├── ingest_latency_metrics.py
│   └── log_parser_requirements/
└── config/
    └── alert-rules.yaml

tests/
├── unit/
│   └── observability/test_ingest_latency_metrics.py
├── integration/
│   └── observability/test_p95_pipeline.py
└── data-quality/
    └── expectations/log_latency_suite.json
```

**Structure Decision**: Keep all observability automation and provisioning under a single `observability/` subtree with mirrored test directories so data-quality expectations and runtime jobs evolve together without cross-project coupling.

## Complexity Tracking

*Fill ONLY if Constitution Check has violations that must be justified*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| _None_ | — | — |
