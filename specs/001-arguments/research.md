# Research: Service Latency Dashboard

- Decision: Query Loki for log-derived latency and push aggregates to Prometheus via Pushgateway every 5 minutes.  
  Rationale: Keeps ingestion job stateless and leverages existing log retention while delivering metric time series compatible with Grafana alerting.  
  Alternatives considered: Instrument services directly (would miss historical backfill); store aggregates in ClickHouse (adds new storage maintenance overhead).

- Decision: Provision Grafana dashboard panels using JSON dashboards committed in `observability/dashboards`.  
  Rationale: Version-controlled dashboards satisfy audit requirements and enable repeatable environments.  
  Alternatives considered: Manual Grafana edits (non-repeatable); Terraform Grafana provider (overkill for single dashboard change set).

- Decision: Manage P95 latency thresholds via per-service configuration file checked into `observability/config/alert-rules.yaml`.  
  Rationale: Enables team-specific overrides while keeping defaults accessible to ingestion job and alert rules.  
  Alternatives considered: Hard-coded defaults inside job (difficult to tune per team); storing thresholds in external database (adds access management and latency).

- Decision: Restrict dashboard access using Grafana teams mapped to feature ownership metadata.  
  Rationale: Ensures feature engineers only view services they own without inventing new auth mechanisms.  
  Alternatives considered: Global visibility (risks noisy dashboard for teams); per-service API tokens (high operational overhead).
