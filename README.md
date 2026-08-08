# Customer Churn Prediction and Intervention Platform

A multi-tenant SaaS platform built to predict customer churn risks and automate retention interventions before subscription cancellation occurs. The system ingests billing and usage telemetry, computes predictive risk scores with XGBoost, generates natural language explanations using Google Gemini, and executes targeted outreach across multiple messaging channels.

🚀 **Live Demo Application**: [https://thechurnguard.netlify.app/login/](https://thechurnguard.netlify.app/login/)

📄 **Product Requirements Document**: [PRD Document](docs/PRD.pdf)
> The Product Requirements Document (PRD) outlines the core architecture, functional requirements, and success metrics for ChurnGuard AI. It details the platform's ability to ingest billing telemetry, explain churn risk using SHAP, and automate multi-channel interventions via Gemini. Dive into the complete PDF preview above to explore user personas, the XGBoost predictive pipeline, and our reporting logic for tracking saved revenue.

---

## System Architecture

The platform follows a modular microservices architecture, separating event ingestion, feature computation, machine learning inference, and campaign execution.

```mermaid
graph TD
    subgraph Client Layer
        WebUI[Next.js App Router]
        Webhooks[External Webhook Sources: Stripe / Segment / Amplitude]
    end

    subgraph API & Gateway Layer
        Gateway[FastAPI Gateway]
        Realtime[Node.js WebSocket Gateway]
        Auth[OAuth2 / JWT Manager]
    end

    subgraph Data & Queue Layer
        DB[(PostgreSQL)]
        Cache[(Redis Cache & PubSub)]
    end

    subgraph Machine Learning Pipeline
        FeatureStore[Feature Engineering Engine]
        XGBoost[XGBoost Prediction Model]
        SHAP[SHAP Driver Analyzer]
        LLM[Gemini Intervention Service]
    end

    subgraph Worker & Outreach Layer
        Worker[Celery / Async Task Worker]
        Outreach[Channel Adapters: Email / SMS / Slack / In-App]
    end

    Webhooks -->|HTTP POST| Gateway
    WebUI <-->|HTTP / REST| Gateway
    WebUI <-->|WebSockets| Realtime
    Gateway --> Auth
    Gateway --> DB
    Gateway --> Cache
    Gateway --> Worker
    Worker --> FeatureStore
    FeatureStore --> DB
    Worker --> XGBoost
    Worker --> SHAP
    SHAP --> LLM
    Worker --> Outreach
    Outreach --> DB
    Realtime <--> Cache
```

## Entity Relationship Diagram

The PostgreSQL database enforces tenant isolation across all entities using tenant IDs and structured primary/foreign keys.

```mermaid
erDiagram
    TENANTS ||--o{ USERS : "has"
    TENANTS ||--o{ CUSTOMERS : "owns"
    TENANTS ||--o{ CAMPAIGNS : "configures"
    TENANTS ||--o{ AUDIT_LOGS : "logs"

    USERS ||--o{ REFRESH_TOKENS : "authenticates"
    USERS ||--o{ CAMPAIGNS : "creates"

    CUSTOMERS ||--o{ CUSTOMER_EVENTS : "generates"
    CUSTOMERS ||--o{ CHURN_FEATURES : "computes"
    CUSTOMERS ||--o{ INTERVENTIONS : "receives"
    CUSTOMERS ||--o{ IN_APP_NOTIFICATIONS : "notified_via"

    CAMPAIGNS ||--o{ INTERVENTIONS : "triggers"

    TENANTS {
        uuid id PK
        string name
        string subdomain
        string plan_tier
        boolean is_active
        datetime created_at
    }

    USERS {
        uuid id PK
        uuid tenant_id FK
        string email
        string hashed_password
        string role
        datetime created_at
    }

    CUSTOMERS {
        uuid id PK
        uuid tenant_id FK
        jsonb external_ids
        string plan
        float mrr
        float churn_probability
        string churn_risk_tier
        datetime first_seen_at
        datetime last_seen_at
    }

    CUSTOMER_EVENTS {
        uuid id PK
        uuid tenant_id FK
        uuid customer_id FK
        string source
        string external_event_id
        string event_type
        jsonb properties
        datetime occurred_at
    }

    CHURN_FEATURES {
        uuid id PK
        uuid tenant_id FK
        uuid customer_id FK
        datetime as_of_date
        string feature_set_version
        jsonb features
    }

    CAMPAIGNS {
        uuid id PK
        uuid tenant_id FK
        string name
        jsonb trigger_rule
        string intervention_type
        string channel
        string template
        string status
        uuid created_by FK
    }

    INTERVENTIONS {
        uuid id PK
        uuid tenant_id FK
        uuid customer_id FK
        uuid campaign_id FK
        string channel
        string status
        string outcome
        datetime sent_at
        datetime outcome_recorded_at
    }
```

## Tech Stack

- **Frontend**: Next.js (App Router), TypeScript, Tailwind CSS, Lucide React, Playwright.
- **API Core**: Python 3.12, FastAPI, Async SQLAlchemy 2.0, Pydantic v2, Alembic.
- **Realtime Server**: Node.js, Express, Socket.io, Redis Pub/Sub.
- **Machine Learning**: XGBoost, Scikit-learn, Pandas, SHAP, Google Gemini API (`google-genai`).
- **Data & Caching**: PostgreSQL 16, Redis 7.
- **Security & Infrastructure**: AES-GCM column encryption, PyJWT, Docker, Docker Compose, OpenTelemetry, Prometheus, Grafana.

## Application Previews (3 Major Operating Scenarios)

### Scenario 1: Real-Time Churn Risk Telemetry & Monitoring
*Real-time monitoring of customer churn probability, risk tier distribution, and MRR at risk.*

![Real-Time Churn Telemetry](docs/screenshots/dashboard_dark.png)

- **Predictive Risk Scoring**: Ingests billing and product telemetry to score customer churn probability using an XGBoost classifier model.
- **MRR at Risk Visibility**: Instantly aggregates total revenue exposed to risk across `Critical` (>75%) and `High` (50–75%) risk tiers for immediate executive visibility.
- **Velocity Trend Telemetry**: Visualizes 30-day login and usage activity trends per account, streaming live score updates via a Node.js Socket.io WebSocket gateway.

---

### Scenario 2: SHAP Risk Inspection & Gemini AI Intervention Reasoning
*Deep-dive risk driver attribution with SHAP explainability and Gemini AI-generated retention strategies.*

![SHAP Inspection & Gemini AI Reasoning](docs/screenshots/dashboard.png)

- **SHAP Feature Attribution**: Deconstructs complex risk scores into ranked, human-readable feature drivers (e.g., login frequency drop-offs, seat shrinkage, billing inquiry spikes).
- **Gemini 2.5 AI Retention Strategy**: Generates customized, context-aware intervention strategies and email/message copy tailored to customer plan tier and tenure.
- **1-Click Executive Outreach**: Provides immediate manual outreach override actions across Email, Slack, and In-App notification channels.

---

### Scenario 3: Automated Retention Campaign Builder & Multi-Channel Outreach
*Rule-based campaign automation triggering multi-channel interventions when risk thresholds are met.*

![Automated Retention Campaign Builder](docs/screenshots/campaigns.png)

- **Automated Workflow Engine**: Configures rules that trigger when customers cross defined risk tier and MRR thresholds.
- **Multi-Channel Channel Adapters**: Dispatches automated save offers via Email, Slack Webhooks, SMS, or In-App dialogs with built-in 24-hour cooldown debouncing.
- **Outcome & ROI Tracking**: Tracks campaign delivery rates, saved revenue counterfactuals, and Wilson score interval retention percentages over time.


## Local Development & Setup

### Prerequisites
- Docker and Docker Compose installed on your system.
- Node.js 18+ and Python 3.12+ (if running outside Docker).

### Step 1: Clone the Repository
```bash
git clone https://github.com/SatyamPandey07/Customer-Churn-Prediction-Intervention-Platform.git
cd Customer-Churn-Prediction-Intervention-Platform
```

### Step 2: Environment Configuration
Copy the sample environment file to `.env`:
```bash
cp .env.example .env
```
Ensure `GEMINI_API_KEY` is configured if you intend to generate Gemini-powered risk explanations.

### Step 3: Run the Application Suite
Start the full stack (Database, Redis, API Gateway, Realtime Gateway, and Frontend Web App):
```bash
docker-compose up -d --build
```

### Step 4: Seed Synthetic Training & Demo Data
Populate the database with customer histories, events, and model predictions:
```bash
docker-compose exec api python /app/apps/api/scripts/generate_synthetic_churn_data.py
```

### Step 5: Access the Web Services
- **Web Dashboard**: [http://localhost:3000](http://localhost:3000) (Login credentials: `admin@example.com` / `Password123!`)
- **API Documentation**: [http://localhost:8001/docs](http://localhost:8001/docs)
- **Realtime Gateway**: `ws://localhost:3001`