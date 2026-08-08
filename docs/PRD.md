# ChurnGuard AI
## Customer Churn Prediction & Intervention Platform
### Product Requirements Document

**Author**: Satyam Pandey  
**Status**: Draft  
**Last Updated**: August 8, 2026  
**Repository**: github.com/SatyamPandey07/Customer-Churn-Prediction-Intervention-Platform  

---

## 1. Overview
ChurnGuard AI is a multi-tenant SaaS platform that predicts which customers are about to cancel their subscription — and why — before it happens, then automatically reaches out with the right offer or action to retain them. It quantifies the revenue saved by each intervention.
The system ingests billing and product-usage telemetry, computes churn-risk scores with an XGBoost model, explains the drivers behind each score using SHAP, generates natural-language retention strategies with Google Gemini, and executes targeted outreach across multiple messaging channels.

## 2. Problem Statement
Subscription businesses typically discover churn only after a customer cancels, at which point retention options are limited to discounts or exit surveys. Existing tools often surface churn risk without:
- Explaining why a customer is at risk in human-readable terms
- Recommending a specific, context-aware retention action
- Automating outreach at the moment risk crosses a meaningful threshold
- Tying interventions back to measurable, saved revenue

This forces revenue and CS teams into reactive, manual, and inconsistent retention workflows.

## 3. Goals & Objectives
- Predict customer churn probability continuously from billing and usage telemetry
- Explain each prediction with ranked, human-readable risk drivers (SHAP)
- Auto-generate tailored retention strategies and outreach copy (Gemini)
- Trigger multi-channel interventions automatically based on configurable rules
- Quantify and report the revenue saved from interventions (ROI)
- Support multiple tenants with strict data isolation

### Non-Goals
- Building a general-purpose CRM or billing system (the platform ingests from Stripe/Segment/Amplitude rather than replacing them)
- Native mobile applications (web-first for v1)

## 4. Target Users / Personas
| Persona | Needs |
|---------|-------|
| VP of Customer Success / Revenue | Executive visibility into MRR at risk, retention ROI |
| Customer Success Manager (CSM) | Per-account risk drivers, 1-click manual outreach |
| RevOps / Growth Engineer | Configure automated campaign rules and thresholds |
| Data / ML stakeholder | Trust in model explainability and feature versioning |

## 5. Key Use Cases / User Stories
1. As a CS leader, I want a live dashboard of churn risk tiers and MRR at risk so I can prioritize accounts.
2. As a CSM, I want to see why a specific customer is flagged as high-risk (e.g., login drop-off, seat shrinkage) so I know how to respond.
3. As a CSM, I want an AI-generated retention message tailored to the customer's plan and tenure so I can act quickly.
4. As RevOps, I want to define rules that automatically trigger an email/SMS/Slack/in-app offer when a customer crosses a risk threshold.
5. As a CS leader, I want to see saved-revenue and retention-rate metrics per campaign to prove ROI.
6. As a platform admin, I want each tenant's data fully isolated for security and compliance.

## 6. Functional Requirements

### 6.1 Data Ingestion
- Ingest billing and product-usage events via webhooks (Stripe, Segment, Amplitude)
- Normalize external events into a unified `CUSTOMER_EVENTS` schema, deduplicated by `external_event_id`

### 6.2 Feature Engineering & Prediction
- Compute versioned feature sets (`CHURN_FEATURES`) per customer, per `as_of_date`
- Score churn probability using an XGBoost classifier; store `churn_probability` and `churn_risk_tier` on the customer record
- Support risk tiers: Critical (>75%), High (50–75%), and lower tiers for the remainder

### 6.3 Explainability
- Generate SHAP-based feature attribution per prediction, ranked by contribution (e.g., login frequency drop-off, seat shrinkage, billing inquiry spikes)
- Feed SHAP output into the Gemini intervention service to produce a natural-language explanation and recommended retention strategy

### 6.4 Campaigns & Automation
- Allow users to define campaigns with a trigger rule (risk tier / MRR threshold), intervention type, channel, and message template
- Execute interventions asynchronously via a task worker when trigger conditions are met
- Enforce a 24-hour cooldown/debounce per customer to prevent outreach spam
- Support channels: Email, SMS, Slack, and in-app notifications, via pluggable channel adapters

### 6.5 Manual Outreach
- Allow CSMs to trigger a 1-click manual outreach override (Email, Slack, in-app) outside of automated campaigns

### 6.6 Reporting & ROI
- Track intervention delivery status and outcome (retained/churned) per customer/campaign
- Compute saved-revenue counterfactuals and retention-rate statistics (using Wilson score intervals) over time
- Provide real-time dashboard updates via a WebSocket gateway

### 6.7 Multi-Tenancy & Access Control
- Isolate all data by `tenant_id` across every core entity (users, customers, events, features, campaigns, interventions, audit logs)
- Support role-based access via OAuth2/JWT authentication, with refresh tokens per user
- Maintain an audit log per tenant for compliance

## 7. Non-Functional Requirements
| Category | Requirement |
|----------|-------------|
| Security | AES-GCM column-level encryption for sensitive fields; JWT-based auth; tenant data isolation enforced at the query layer |
| Scalability | Async task processing (Celery/async worker) to decouple scoring/outreach from the request path |
| Observability | OpenTelemetry instrumentation; Prometheus metrics; Grafana dashboards |
| Realtime | Sub-second dashboard updates via Redis Pub/Sub + Socket.io |
| Reliability | Idempotent event ingestion (dedup by `external_event_id`); cooldown debouncing to avoid duplicate outreach |
| Portability | Full local dev environment via Docker Compose |

## 10. Tech Stack
| Layer | Technologies |
|-------|--------------|
| Frontend | Next.js (App Router), TypeScript, Tailwind CSS, Lucide React, Playwright |
| API Core | Python 3.12, FastAPI, Async SQLAlchemy 2.0, Pydantic v2, Alembic |
| Realtime Server | Node.js, Express, Socket.io, Redis Pub/Sub |
| Machine Learning | XGBoost, Scikit-learn, Pandas, SHAP, Google Gemini API (google-genai) |
| Data & Caching | PostgreSQL 16, Redis 7 |
| Security & Infra | AES-GCM encryption, PyJWT, Docker/Docker Compose, OpenTelemetry, Prometheus, Grafana |

## 11. Success Metrics
- **Model quality**: Precision/recall and AUC of churn predictions against realized outcomes
- **Explainability adoption**: % of flagged accounts where CSMs view the SHAP driver breakdown
- **Intervention effectiveness**: Retention rate (with confidence interval) of customers who received an intervention vs. control
- **Revenue impact**: Total MRR saved (counterfactual) attributed to campaigns
- **Operational**: Dashboard update latency, campaign delivery success rate, false-positive outreach rate (cooldown violations)

## 12. Assumptions & Constraints
- Billing/usage data is available via Stripe, Segment, and/or Amplitude webhooks
- A `GEMINI_API_KEY` is required for AI-generated intervention copy; without it, explanations fall back to raw SHAP output only
- Model retraining/versioning cadence is not yet formally defined (see Open Questions)

## 13. Open Questions
- What is the retraining cadence and drift-monitoring strategy for the XGBoost model?
- What SLAs apply to outreach latency after a risk-tier crossing?
- Is there a plan for additional outreach channels (e.g., WhatsApp, phone/IVR)?
- What tenant-level customization is allowed for risk-tier thresholds (currently fixed at 50%/75%)?
- What is the data retention policy for `CUSTOMER_EVENTS` and audit logs?

## 14. Milestones (Suggested)
| Phase | Scope |
|-------|-------|
| M1 – Core Ingestion & Scoring | Webhook ingestion, feature store, XGBoost scoring, tenant isolation |
| M2 – Explainability | SHAP driver analysis, Gemini-generated explanations |
| M3 – Campaigns & Outreach | Rule-based campaign engine, channel adapters, cooldown logic |
| M4 – Reporting & Realtime | ROI/retention reporting, WebSocket live dashboard |
| M5 – Hardening | Observability (OTel/Prometheus/Grafana), security audit, load testing |
