# Architecture Overview

## Multi-Tenancy Strategy
We use a single database instance with Row-Level Security (RLS) to enforce tenant isolation.
Every table that holds tenant-specific data MUST have a `tenant_id` column and an RLS policy that restricts access based on a session setting.

### RLS Policy Pattern
```sql
ALTER TABLE your_table ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_policy ON your_table
    USING (tenant_id = current_setting('app.current_tenant')::uuid);
```
The FastAPI application must set `app.current_tenant` for every authenticated request before querying the database.

## System Components
- **Frontend**: Next.js 14 App Router
- **Core API**: FastAPI (Python 3.12)
- **Realtime Gateway**: Node.js + WebSocket
- **Database**: PostgreSQL 16
- **Cache/Queue**: Redis 7
- **ML**: XGBoost + SHAP (to be added)
