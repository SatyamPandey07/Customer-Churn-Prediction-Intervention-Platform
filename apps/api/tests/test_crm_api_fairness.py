import pytest
import uuid
import sqlalchemy
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch

from apps.api.models import Tenant, Customer, ApiKey, PlanTier
from apps.api.core.api_keys import create_api_key, verify_api_key, revoke_api_key, _hash_key
from apps.api.core.crm.adapters import SalesforceAdapter, HubSpotAdapter, get_crm_adapter
from apps.api.core.crm.engine import sync_customer_to_crm, sync_all_customers_to_crm
from apps.api.core.ml.fairness import run_fairness_monitoring, PARITY_THRESHOLD
from apps.api.routers.public_api import _check_rate_limit, _rate_store


# ============================================================
# Test 1: CRM adapter field mapping (Salesforce + HubSpot)
# ============================================================

@pytest.mark.asyncio
async def test_salesforce_adapter_pushes_correct_fields():
    adapter = SalesforceAdapter()
    fields = {
        "churn_risk_tier": "critical",
        "churn_probability": 0.87,
        "health_score": 28.5,
        "open_interventions": 2
    }
    result = await adapter.push_customer_fields(crm_id="001XXXTEST", fields=fields)

    assert result["status"] == "success"
    pushed = result["pushed_fields"]
    assert "ChurnGuard_Risk_Tier__c" in pushed
    assert pushed["ChurnGuard_Risk_Tier__c"] == "critical"
    assert "ChurnGuard_Probability__c" in pushed
    assert pushed["ChurnGuard_Probability__c"] == 0.87
    assert "ChurnGuard_Health_Score__c" in pushed


@pytest.mark.asyncio
async def test_hubspot_adapter_pushes_correct_fields():
    adapter = HubSpotAdapter()
    fields = {
        "churn_risk_tier": "high",
        "churn_probability": 0.6,
        "health_score": 45.0,
        "open_interventions": 1
    }
    result = await adapter.push_customer_fields(crm_id="HS-123456", fields=fields)

    assert result["status"] == "success"
    pushed = result["pushed_fields"]
    assert "churnguard_risk_tier" in pushed
    assert pushed["churnguard_risk_tier"] == "high"
    assert "churnguard_churn_probability" in pushed
    assert "churnguard_health_score" in pushed


@pytest.mark.asyncio
async def test_crm_sync_scheduled_and_manual_trigger(db_session):
    tenant_id = uuid.uuid4()
    tenant = Tenant(id=tenant_id, name="CRM Test", subdomain="crm-test", plan_tier=PlanTier.tier1, is_active=True)
    db_session.add(tenant)
    await db_session.commit()

    await db_session.execute(sqlalchemy.text(f"SET LOCAL app.current_tenant = '{tenant_id}'"))

    c = Customer(
        id=uuid.uuid4(), tenant_id=tenant_id,
        external_ids={"salesforce": "001AABBCC"},
        plan="enterprise", mrr=3000.0,
        churn_probability=0.7, churn_risk_tier="critical", health_score=30.0
    )
    db_session.add(c)
    await db_session.commit()

    # Manual trigger for individual customer
    log = await sync_customer_to_crm(db_session, tenant_id, c, "salesforce")
    assert log.status == "success"
    assert "ChurnGuard_Risk_Tier__c" in log.fields_pushed

    # Scheduled batch sync for all customers
    result = await sync_all_customers_to_crm(db_session, tenant_id, "hubspot")
    assert result["total"] == 1
    # customer has no hubspot external_id, expect skipped
    assert result["skipped"] == 1


# ============================================================
# Test 2: API key auth — valid key succeeds, revoked/invalid rejected
# ============================================================

@pytest.mark.asyncio
async def test_api_key_valid_and_revoked(db_session):
    tenant_id = uuid.uuid4()
    tenant = Tenant(id=tenant_id, name="Key Test", subdomain="key-test", plan_tier=PlanTier.tier1, is_active=True)
    db_session.add(tenant)
    await db_session.commit()

    # Create a valid API key
    result = await create_api_key(db_session, tenant_id, name="Test Key", scope="read")
    raw_key = result["key"]
    assert raw_key.startswith("cgk_")

    # Valid key verifies successfully
    api_key = await verify_api_key(db_session, raw_key)
    assert api_key is not None
    assert api_key.scope == "read"
    assert api_key.is_active is True

    # Invalid key returns None
    bad_key = await verify_api_key(db_session, "cgk_totally_wrong_key")
    assert bad_key is None

    # Revoke the key
    key_id = uuid.UUID(result["id"])
    revoke_result = await revoke_api_key(db_session, tenant_id, key_id)
    assert revoke_result["revoked"] is True

    # Revoked key should return None
    revoked_key = await verify_api_key(db_session, raw_key)
    assert revoked_key is None


@pytest.mark.asyncio
async def test_api_key_rate_limiting():
    """Test that the rate limiter rejects after exceeding RATE_LIMIT_MAX_REQUESTS."""
    from apps.api.routers.public_api import RATE_LIMIT_MAX_REQUESTS
    from fastapi import HTTPException

    test_key_id = f"rate-test-{uuid.uuid4()}"
    _rate_store[test_key_id] = []

    # Fill up the rate window
    for _ in range(RATE_LIMIT_MAX_REQUESTS):
        _check_rate_limit(test_key_id)

    # The next call should raise 429
    with pytest.raises(HTTPException) as exc_info:
        _check_rate_limit(test_key_id)
    assert exc_info.value.status_code == 429


# ============================================================
# Test 3: API key scope — read-only key cannot hit write endpoint
# ============================================================

@pytest.mark.asyncio
async def test_api_key_read_only_scope_blocks_write(db_session):
    """A read-only key should fail when checked for write scope."""
    from apps.api.routers.public_api import require_write_api_key
    from fastapi import HTTPException

    tenant_id = uuid.uuid4()
    tenant = Tenant(id=tenant_id, name="Scope Test", subdomain="scope-test", plan_tier=PlanTier.tier1, is_active=True)
    db_session.add(tenant)
    await db_session.commit()

    result = await create_api_key(db_session, tenant_id, name="Read Key", scope="read")
    raw_key = result["key"]

    read_api_key = await verify_api_key(db_session, raw_key)
    assert read_api_key is not None
    assert read_api_key.scope == "read"

    # Simulate the require_write_api_key dependency check
    with pytest.raises(HTTPException) as exc_info:
        await require_write_api_key(api_key=read_api_key)
    assert exc_info.value.status_code == 403
    assert "read_write" in exc_info.value.detail


# ============================================================
# Test 4: Fairness report — flags skewed segment, passes clean one
# ============================================================

@pytest.mark.asyncio
async def test_fairness_report_flags_skewed_segment(db_session):
    """
    Intentionally creates a SKEWED segment (predicted 0.9 but only 20% actual high-risk)
    and a CLEAN segment (predicted 0.2, 20% actual). Fairness job must flag the skewed segment.
    """
    tenant_id = uuid.uuid4()
    tenant = Tenant(id=tenant_id, name="Fairness Test", subdomain="fair-test", plan_tier=PlanTier.tier1, is_active=True)
    db_session.add(tenant)
    await db_session.commit()

    await db_session.execute(sqlalchemy.text(f"SET LOCAL app.current_tenant = '{tenant_id}'"))

    # SKEWED segment: 5 "starter" customers all predicted 0.9 but only 1 is actually high-risk
    # calibration_error = |0.9 - 0.2| = 0.70 > threshold
    for i in range(5):
        risk_tier = "critical" if i == 0 else "low"
        db_session.add(Customer(
            id=uuid.uuid4(), tenant_id=tenant_id, plan="starter",
            churn_probability=0.9, churn_risk_tier=risk_tier, health_score=40.0
        ))

    # CLEAN segment: 5 "enterprise" customers predicted 0.2, and only 1 is high-risk
    # calibration_error = |0.2 - 0.2| = 0.0 < threshold
    for i in range(5):
        risk_tier = "critical" if i == 0 else "low"
        db_session.add(Customer(
            id=uuid.uuid4(), tenant_id=tenant_id, plan="enterprise",
            churn_probability=0.2, churn_risk_tier=risk_tier, health_score=75.0
        ))

    await db_session.commit()

    report = await run_fairness_monitoring(db_session, tenant_id, dimension="plan_tier")

    assert report is not None
    flagged = report.flagged_segments

    # Skewed "starter" segment MUST be flagged
    assert "starter" in flagged, f"Expected 'starter' to be flagged, got: {flagged}"

    # Clean "enterprise" segment MUST NOT be flagged
    assert "enterprise" not in flagged, f"Expected 'enterprise' NOT to be flagged, got: {flagged}"

    # Segment details must include calibration_error
    starter_seg = next(s for s in report.segments if s["dimension_value"] == "starter")
    assert starter_seg["calibration_error"] > PARITY_THRESHOLD
    assert starter_seg["is_flagged"] is True

    enterprise_seg = next(s for s in report.segments if s["dimension_value"] == "enterprise")
    assert enterprise_seg["calibration_error"] <= PARITY_THRESHOLD
    assert enterprise_seg["is_flagged"] is False
