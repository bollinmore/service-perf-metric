# Quickstart: Service Latency Dashboard

## Prerequisites
- Python 3.11 with `pipx` or virtualenv available.
- Access to Loki API endpoint and Prometheus Pushgateway credentials.
- Grafana admin token with permissions to apply dashboard JSON and manage teams.

## 1. Bootstrap the environment
```bash
make ingest-latency-metrics deps
```
- Installs Python dependencies recorded in `observability/jobs/log_parser_requirements/requirements.txt`.
- Verifies checksum against `log-parser.lock`.

## 2. Run the ingestion job locally
```bash
LOG_WINDOW=7d make ingest-latency-metrics run
```
- Pulls the last 7 days of parsed application logs from Loki.
- Computes per-service P95 latency and pushes results to the Prometheus Pushgateway sandbox.
- Outputs Great Expectations data-quality report under `artifacts/data-quality/latest/index.html`.

## 3. Provision the Grafana dashboard
```bash
make grafana-sync DASHBOARD=observability/dashboards/service-latency-dashboard.json
```
- Applies dashboard JSON via Grafana HTTP API.
- Ensures panels default to the 7-day window and filter by authenticated engineer’s teams.

## 4. Configure alert thresholds
```bash
python observability/jobs/tools/update_thresholds.py --config observability/config/alert-rules.yaml
```
- Validates threshold bounds (50–1000 ms) and writes overrides via the dashboard API.
- Records change summary for audit under `artifacts/threshold-updates/YYYYMMDD.md`.

## 5. Validate alerts end-to-end
```bash
pytest tests/integration/observability/test_p95_pipeline.py -k alert
```
- Simulates a threshold breach using synthetic log data.
- Confirms PagerDuty routing and dashboard annotation behavior.

## 6. Capture evidence for compliance
- Export dashboard screenshot highlighting P95 panels and store under `artifacts/evidence/dashboard.png`.
- Save pytest and data-quality reports alongside the feature’s `tasks.md` once generated.

## 7. Tear down (optional)
```bash
make ingest-latency-metrics clean
```
- Removes temporary datasets and local Prometheus samples.
