# Data Model: Service Latency Dashboard

## Entities

### Service
- **service_id** (string, required): Canonical slug used across observability systems.
- **name** (string, required): Display name for dashboard panels.
- **team_owner** (string, required): Owning team identifier; drives access control grouping.
- **default_p95_threshold_ms** (integer, required): Baseline alert threshold (defaults to 350 ms if not overridden).
- **alert_runbook_url** (string, required): Link to the owning team’s PagerDuty/Grafana runbook.

### LatencySnapshot
- **service_id** (string, required): Foreign key to `Service.service_id`.
- **timestamp** (datetime, required): Aggregation boundary (5-minute buckets).
- **p95_latency_ms** (float, required): Computed from parsed application logs.
- **request_count** (integer, required): Total requests in bucket (used to contextualize spikes).
- **source_log_version** (string, required): Schema version of parsed log format for lineage tracking.

### AlertThresholdOverride
- **service_id** (string, required): Foreign key to `Service.service_id`.
- **environment** (enum: prod|staging, required): Scope where override applies.
- **p95_threshold_ms** (integer, required): Override value.
- **effective_from** (datetime, required): When the override becomes active.
- **notes** (string, optional): Justification recorded for audits.

### AlertEvaluation
- **service_id** (string, required): Foreign key to `Service.service_id`.
- **window_start** (datetime, required): Start of evaluation window (15 minutes rolling).
- **window_end** (datetime, required): End of evaluation window.
- **status** (enum: normal|breach|acknowledged|resolved, required): Evaluation outcome shared with alerting system.
- **breach_duration_minutes** (integer, optional): Duration above threshold.
- **notified_at** (datetime, optional): When PagerDuty notification was emitted.

### EngineerAccess
- **user_email** (string, required): Engineer identity.
- **team_owner** (string, required): Owning team, aligns with `Service.team_owner`.
- **allowed_service_ids** (array<string>, optional): Narrowed scope; null implies all services for the team.
- **grafana_team_slug** (string, required): Grafana team used for role-based access control.

## Relationships
- `Service (1) ——> (many) LatencySnapshot` via `service_id`.
- `Service (1) ——> (many) AlertThresholdOverride` via `service_id` and `environment`.
- `Service (1) ——> (many) AlertEvaluation` via `service_id`.
- `EngineerAccess (many) ——> (many) Service` via `team_owner` and optional `allowed_service_ids`.

## Validation Rules
- `LatencySnapshot.request_count` MUST be ≥0; data-quality gate rejects buckets with missing counts.
- `LatencySnapshot.source_log_version` MUST match registered schema version; mismatches trigger ingestion failure.
- `AlertThresholdOverride.p95_threshold_ms` MUST be between 50 and 1000 ms; values outside range rejected during config validation.
- `AlertEvaluation.breach_duration_minutes` required when `status=breach` or `status=acknowledged`.
- `EngineerAccess` entries MUST reference existing Grafana team slugs; provisioning script validates before apply.

## State Transitions (AlertEvaluation.status)
- `normal` → `breach` when average P95 across three consecutive buckets exceeds threshold.
- `breach` → `acknowledged` when an engineer acknowledges the PagerDuty incident.
- `acknowledged` → `resolved` when P95 latency falls below threshold for two consecutive buckets.
- `breach` → `resolved` if automated rollback clears breach before acknowledgment.
