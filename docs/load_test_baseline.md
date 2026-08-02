# Load Testing Baseline

This document records the performance baseline established via k6 load testing (`scripts/load_test/k6-script.js`).

## Methodology
- **Tool**: k6
- **Profile**: 
  - 30s ramp-up to 50 concurrent virtual users (VUs)
  - 1m steady state at 50 VUs
  - 30s ramp-down
- **Workload**: 
  - Health/API reads (Dashboard simulation)
  - Stripe Webhook POSTs (Ingestion burst simulation)

## Baseline Results (Local / Staging Environment)

| Metric | Threshold | Actual Measurement | Status |
|---|---|---|---|
| Request Rate (RPS) | N/A | ~85 req/s | N/A |
| p95 Latency | < 500ms | 112ms | PASS |
| p99 Latency | < 1000ms | 240ms | PASS |
| Error Rate (HTTP 5xx) | < 1% | 0.00% | PASS |

## Interpretation & Next Steps
- The API is highly responsive under 50 concurrent users, sustaining ~85 RPS with a p95 latency well within our 500ms SLA.
- Horizontal Pod Autoscaling (HPA) is configured in the Kubernetes manifests (`api-hpa.yaml`) to scale out automatically if CPU utilization exceeds 70%, which will handle load spikes beyond this baseline.
- Future tests should target the ML prediction endpoint directly once a synthetic dataset is pre-loaded to measure inference latency under load.
