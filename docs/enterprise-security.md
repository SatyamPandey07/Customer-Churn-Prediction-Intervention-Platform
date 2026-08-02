# Enterprise Security Overview

This document outlines the security architecture and compliance-readiness of the Customer Churn Prediction and Intervention Platform. It serves as a reference for enterprise security teams evaluating the platform.

## 1. Tenant Isolation
The platform uses a strict Row-Level Security (RLS) model within PostgreSQL to enforce logical tenant isolation at the database layer.
- Every API request is authenticated via JWT, which extracts the `tenant_id`.
- The database connection explicitly executes `SET LOCAL app.current_tenant = '{tenant_id}'`.
- PostgreSQL RLS policies drop any queries (reads or writes) that attempt to access rows belonging to a different tenant.

## 2. Encryption
- **In Transit**: All traffic must route through TLS 1.2+ (terminated at the Kubernetes Ingress/LoadBalancer layer).
- **At Rest**: 
  - Database volumes (e.g., AWS EBS, GCP PD) are encrypted at the block level.
  - **Field-Level Encryption**: Highly sensitive Personally Identifiable Information (PII) such as `User.email` is encrypted at the application layer using AES-GCM (via `sqlalchemy-utils`). Even if a database dump is compromised, these fields remain secure without the application's symmetric encryption key.

## 3. Secrets Management
The application does not use plaintext `.env` files for secrets in production.
- A central `SecretsManager` abstraction integrates with **HashiCorp Vault** (or cloud-native equivalents like AWS Secrets Manager).
- Secrets (JWT signing keys, Gemini API keys, Database credentials) are injected dynamically at runtime.

## 4. Access Control
- **Authentication**: JWT-based stateless authentication with `HttpOnly` cookies to prevent XSS exfiltration.
- **Role-Based Access Control (RBAC)**: Users are assigned roles (`owner`, `admin`, `analyst`, `viewer`). 
- **Account Lockout**: After 10 failed login attempts, an account is locked for 15 minutes to prevent brute-force attacks.

## 5. Network Security & Kubernetes
- **Network Policies**: Pod-to-pod communication is heavily restricted. Only necessary traffic (e.g., API to Redis, Worker to Postgres) is allowed. Default-deny policies prevent lateral movement.
- **Rate Limiting**: Global rate limiting (IP-based) protects against volumetric DDoS attacks, while specific endpoints (like authentication) have stricter per-minute limits.
- **Security Headers**: Standard headers (CSP, HSTS, X-Frame-Options, X-XSS-Protection) are enforced globally via API middleware.

## 6. Audit Logging
- All significant actions (login, campaign creation, user invited, data exported) generate an `AuditLog` record.
- These records contain the `actor_user_id`, `action`, `resource`, `timestamp`, and `ip_address`, and are retained per the tenant's data retention policy.

## 7. GDPR / CCPA Compliance
- **Data Export**: `GET /tenants/{tenant_id}/data/export` allows a tenant owner to export all customer and event data into a portable JSON format.
- **Right to be Forgotten**: `DELETE /tenants/{tenant_id}/data/delete` issues a hard-delete cascade across all customer, event, prediction, and intervention data for the tenant.

## 8. Incident Response
For any security-related disclosures or incident response coordination, please contact: `security@churn-platform.com`.
