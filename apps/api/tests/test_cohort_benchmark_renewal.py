import uuid
from datetime import datetime, timedelta, timezone

import pytest
import sqlalchemy
from apps.api.core.analytics.benchmarks import get_industry_benchmark
from apps.api.core.analytics.cohorts import get_cohort_breakdown
from apps.api.core.analytics.renewals import create_or_update_contract, get_renewals_at_risk
from apps.api.models import Customer, PlanTier, Tenant
from fastapi import HTTPException


@pytest.mark.asyncio
async def test_cohort_breakdown_math_all_dimensions(db_session):
    tenant_id = uuid.uuid4()
    tenant = Tenant(id=tenant_id, name="Cohort Test", subdomain="cohort-test", plan_tier=PlanTier.tier1, is_active=True)
    db_session.add(tenant)
    await db_session.commit()

    await db_session.execute(sqlalchemy.text(f"SET LOCAL app.current_tenant = '{tenant_id}'"))

    now = datetime.now(timezone.utc)

    # Fixture customers with different dimensions
    c1 = Customer(
        id=uuid.uuid4(), tenant_id=tenant_id, plan="enterprise", mrr=2000.0,
        churn_probability=0.8, churn_risk_tier="critical", health_score=30.0,
        industry="fintech", acquisition_channel="outbound", signup_month="2026-01",
        first_seen_at=now - timedelta(days=200)
    )
    c2 = Customer(
        id=uuid.uuid4(), tenant_id=tenant_id, plan="enterprise", mrr=1000.0,
        churn_probability=0.1, churn_risk_tier="low", health_score=90.0,
        industry="fintech", acquisition_channel="outbound", signup_month="2026-01",
        first_seen_at=now - timedelta(days=200)
    )
    c3 = Customer(
        id=uuid.uuid4(), tenant_id=tenant_id, plan="starter", mrr=300.0,
        churn_probability=0.6, churn_risk_tier="high", health_score=40.0,
        industry="healthcare", acquisition_channel="inbound", signup_month="2026-02",
        first_seen_at=now - timedelta(days=100)
    )

    db_session.add_all([c1, c2, c3])
    await db_session.commit()

    # Test dimension = plan_tier
    cohorts_plan = await get_cohort_breakdown(db_session, tenant_id, "plan_tier")
    assert len(cohorts_plan) == 2
    ent = next(c for c in cohorts_plan if c["dimension_value"] == "enterprise")
    assert ent["customer_count"] == 2
    assert ent["churn_rate"] == 50.0
    assert ent["avg_health_score"] == 60.0
    assert pytest.approx(ent["revenue_at_risk"], abs=1e-2) == 1700.0  # (2000*0.8 + 1000*0.1)

    # Test dimension = industry
    cohorts_ind = await get_cohort_breakdown(db_session, tenant_id, "industry")
    assert len(cohorts_ind) == 2
    fin = next(c for c in cohorts_ind if c["dimension_value"] == "fintech")
    assert fin["customer_count"] == 2

    # Test dimension = channel
    cohorts_chan = await get_cohort_breakdown(db_session, tenant_id, "channel")
    out = next(c for c in cohorts_chan if c["dimension_value"] == "outbound")
    assert out["customer_count"] == 2

    # Test dimension = signup_month
    cohorts_m = await get_cohort_breakdown(db_session, tenant_id, "signup_month")
    jan = next(c for c in cohorts_m if c["dimension_value"] == "2026-01")
    assert jan["customer_count"] == 2

@pytest.mark.asyncio
async def test_benchmark_opt_in_guard(db_session):
    tenant_id = uuid.uuid4()
    # benchmarking_opt_in = False
    tenant = Tenant(id=tenant_id, name="OptOut Tenant", subdomain="opt-out", plan_tier=PlanTier.tier1, is_active=True, benchmarking_opt_in=False)
    db_session.add(tenant)
    await db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        await get_industry_benchmark(db_session, tenant_id, "fintech")
    assert exc_info.value.status_code == 403
    assert "opt-in required" in exc_info.value.detail.lower()

@pytest.mark.asyncio
async def test_benchmark_minimum_cohort_size_guard(db_session):
    # Create only 2 opted-in tenants (< 3 threshold)
    t1_id = uuid.uuid4()
    t2_id = uuid.uuid4()
    t1 = Tenant(id=t1_id, name="OptIn T1", subdomain="optin-1", plan_tier=PlanTier.tier1, is_active=True, benchmarking_opt_in=True, industry_vertical="fintech")
    t2 = Tenant(id=t2_id, name="OptIn T2", subdomain="optin-2", plan_tier=PlanTier.tier1, is_active=True, benchmarking_opt_in=True, industry_vertical="fintech")
    db_session.add_all([t1, t2])
    await db_session.commit()

    await db_session.execute(sqlalchemy.text(f"SET LOCAL app.current_tenant = '{t1_id}'"))

    # Add 5 customers per tenant (total 10 < 15 threshold)
    custs = []
    for _ in range(5):
        custs.append(Customer(id=uuid.uuid4(), tenant_id=t1_id, industry="fintech", churn_probability=0.2, health_score=75.0))
        custs.append(Customer(id=uuid.uuid4(), tenant_id=t2_id, industry="fintech", churn_probability=0.3, health_score=70.0))
    db_session.add_all(custs)
    await db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        await get_industry_benchmark(db_session, t1_id, "fintech")

    assert exc_info.value.status_code == 422
    assert "minimum anonymization threshold" in exc_info.value.detail.lower()

@pytest.mark.asyncio
async def test_benchmark_adversarial_cross_tenant_isolation(db_session):
    # Create 3 opted-in tenants with >= 15 customers
    t_ids = [uuid.uuid4() for _ in range(3)]
    tenants = [
        Tenant(id=t_ids[i], name=f"Secret Tenant {i}", subdomain=f"secret-{i}", plan_tier=PlanTier.tier1, is_active=True, benchmarking_opt_in=True, industry_vertical="saas")
        for i in range(3)
    ]
    db_session.add_all(tenants)
    await db_session.commit()

    custs = []
    for i, tid in enumerate(t_ids):
        await db_session.execute(sqlalchemy.text(f"SET LOCAL app.current_tenant = '{tid}'"))
        for j in range(6):  # 3 * 6 = 18 customers >= 15 threshold
            custs.append(Customer(
                id=uuid.uuid4(), tenant_id=tid, industry="saas",
                churn_probability=0.1 * (i + 1), health_score=80.0 - (i * 10)
            ))
    db_session.add_all(custs)
    await db_session.commit()

    report = await get_industry_benchmark(db_session, t_ids[0], "saas")

    assert report["tenant_id"] == str(t_ids[0])
    assert report["anonymized_benchmark"]["opted_in_tenants_count"] == 3
    assert report["anonymized_benchmark"]["total_accounts_analyzed"] == 18
    assert "median" in report["anonymized_benchmark"]
    assert "p25" in report["anonymized_benchmark"]
    assert "p75" in report["anonymized_benchmark"]

    # Explicit Adversarial Privacy Assertions:
    report_str = str(report)
    for other_tid in t_ids[1:]:
        assert str(other_tid) not in report_str
    assert "Secret Tenant" not in report_str
    assert "secret-" not in report_str

@pytest.mark.asyncio
async def test_renewals_at_risk_join_and_prioritization(db_session):
    tenant_id = uuid.uuid4()
    tenant = Tenant(id=tenant_id, name="Renewal Test", subdomain="ren-test", plan_tier=PlanTier.tier1, is_active=True)
    db_session.add(tenant)
    await db_session.commit()

    await db_session.execute(sqlalchemy.text(f"SET LOCAL app.current_tenant = '{tenant_id}'"))

    now = datetime.now(timezone.utc)

    # Customer 1: High risk (0.8), renewal in 20 days (Within 90d)
    c1 = Customer(id=uuid.uuid4(), tenant_id=tenant_id, plan="enterprise", mrr=5000.0, churn_probability=0.8, churn_risk_tier="critical", health_score=35.0)
    # Customer 2: Low risk (0.1), renewal in 40 days (Within 90d)
    c2 = Customer(id=uuid.uuid4(), tenant_id=tenant_id, plan="starter", mrr=500.0, churn_probability=0.1, churn_risk_tier="low", health_score=85.0)
    # Customer 3: High risk (0.9), renewal in 150 days (Outside 90d window)
    c3 = Customer(id=uuid.uuid4(), tenant_id=tenant_id, plan="premium", mrr=2000.0, churn_probability=0.9, churn_risk_tier="critical", health_score=20.0)

    db_session.add_all([c1, c2, c3])
    await db_session.commit()

    # Create Contracts
    await create_or_update_contract(db_session, tenant_id, c1.id, renewal_date=now + timedelta(days=20), contract_term_months=12, auto_renew=True, contract_value_mrr=5000.0)
    await create_or_update_contract(db_session, tenant_id, c2.id, renewal_date=now + timedelta(days=40), contract_term_months=12, auto_renew=False, contract_value_mrr=500.0)
    await create_or_update_contract(db_session, tenant_id, c3.id, renewal_date=now + timedelta(days=150), contract_term_months=12, auto_renew=True, contract_value_mrr=2000.0)

    # Query 90-day renewals at risk
    report = await get_renewals_at_risk(db_session, tenant_id, window_days=90)

    assert report["total_renewals_in_window"] == 2  # c1 and c2 only, c3 excluded
    assert report["renewals"][0]["customer_id"] == str(c1.id)  # c1 prioritized top due to high risk + close renewal date
    assert report["renewals"][0]["days_until_renewal"] == 20
    assert report["renewals"][0]["urgency_priority_score"] > report["renewals"][1]["urgency_priority_score"]
    assert pytest.approx(report["total_mrr_at_risk"], abs=1e-2) == 4050.0  # 5000*0.8 + 500*0.1
