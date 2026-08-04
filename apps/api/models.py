import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Enum, UniqueConstraint, Float, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy_utils import StringEncryptedType
from sqlalchemy_utils.types.encrypted.encrypted_type import AesGcmEngine
import os

ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY", "super-secret-encryption-key-1234")

Base = declarative_base()

class PlanTier(str, enum.Enum):
    tier1 = "tier1"
    tier2 = "tier2"
    tier3 = "tier3"

class Role(str, enum.Enum):
    owner = "owner"
    admin = "admin"
    analyst = "analyst"
    viewer = "viewer"

class InterventionOutcome(str, enum.Enum):
    pending = "pending"
    retained = "retained"
    churned = "churned"
    unknown = "unknown"

class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    subdomain = Column(String, unique=True, nullable=False)
    plan_tier = Column(Enum(PlanTier, name='plantier'), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    is_active = Column(Boolean, default=True)
    benchmarking_opt_in = Column(Boolean, nullable=False, default=False)
    industry_vertical = Column(String, nullable=True)  # fintech, saas, healthcare, ecommerce
    company_size_band = Column(String, nullable=True)  # 1-50, 51-200, 201-1000, 1000+

    users = relationship("User", back_populates="tenant")
    audit_logs = relationship("AuditLog", back_populates="tenant")


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    email = Column(StringEncryptedType(String, ENCRYPTION_KEY, AesGcmEngine, 'pkcs5'), nullable=False)
    hashed_password = Column(String, nullable=True)
    role = Column(Enum(Role, name='user_role'), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    tenant = relationship("Tenant", back_populates="users")
    refresh_tokens = relationship("RefreshToken", back_populates="user")

    __table_args__ = (
        UniqueConstraint('tenant_id', 'email', name='uq_tenant_email'),
    )

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    hashed_token = Column(String, nullable=False, unique=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="refresh_tokens")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    actor_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False)
    resource = Column(String, nullable=True)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    ip_address = Column(String, nullable=True)

    tenant = relationship("Tenant", back_populates="audit_logs")
    actor = relationship("User")

class Customer(Base):
    __tablename__ = "customers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    # external_ids maps source -> id (e.g., {"stripe": "cus_123", "segment": "u_456"})
    external_ids = Column(JSONB, nullable=False, default=dict)
    plan = Column(String, nullable=True)
    mrr = Column(Float, nullable=True, default=0.0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    first_seen_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_seen_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    events = relationship("CustomerEvent", back_populates="customer")

    churn_probability = Column(Float, nullable=True)
    churn_risk_tier = Column(String, nullable=True)
    churn_model_version = Column(String, nullable=True)
    churn_computed_at = Column(DateTime(timezone=True), nullable=True)

    expansion_probability = Column(Float, nullable=True)
    expansion_model_version = Column(String, nullable=True)
    expansion_computed_at = Column(DateTime(timezone=True), nullable=True)

    stated_churn_reason = Column(String, nullable=True)
    industry = Column(String, nullable=True)
    acquisition_channel = Column(String, nullable=True)  # inbound, outbound, referral, paid
    signup_month = Column(String, nullable=True)  # YYYY-MM format

    health_score = Column(Float, nullable=True)

    health_score_computed_at = Column(DateTime(timezone=True), nullable=True)

class CustomerEvent(Base):
    __tablename__ = "customer_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    source = Column(String, nullable=False)
    external_event_id = Column(String, nullable=False)
    event_type = Column(String, nullable=False)
    properties = Column(JSONB, nullable=False, default=dict)
    occurred_at = Column(DateTime(timezone=True), nullable=False)
    ingested_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    customer = relationship("Customer", back_populates="events")

    __table_args__ = (
        UniqueConstraint('tenant_id', 'source', 'external_event_id', name='uq_tenant_source_event'),
    )

class ChurnFeature(Base):
    __tablename__ = "churn_features"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    as_of_date = Column(DateTime(timezone=True), nullable=False)
    feature_set_version = Column(String, nullable=False)
    features = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    customer = relationship("Customer")

    __table_args__ = (
        UniqueConstraint('tenant_id', 'customer_id', 'as_of_date', 'feature_set_version', name='uq_tenant_customer_date_version'),
    )

class HealthScoreConfig(Base):
    __tablename__ = "health_score_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, unique=True)
    churn_weight = Column(Float, nullable=False, default=0.35)
    usage_trend_weight = Column(Float, nullable=False, default=0.25)
    payment_health_weight = Column(Float, nullable=False, default=0.20)
    support_sentiment_weight = Column(Float, nullable=False, default=0.0)
    engagement_recency_weight = Column(Float, nullable=False, default=0.20)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    tenant = relationship("Tenant")

class HealthScore(Base):
    __tablename__ = "health_scores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    as_of_date = Column(DateTime(timezone=True), nullable=False)
    score = Column(Float, nullable=False)
    components = Column(JSONB, nullable=False, default=dict)
    version = Column(String, nullable=False, default="v1")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    customer = relationship("Customer")

    __table_args__ = (
        UniqueConstraint('tenant_id', 'customer_id', 'as_of_date', 'version', name='uq_tenant_customer_health_date_version'),
    )

class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    name = Column(String, nullable=False)
    trigger_rule = Column(JSONB, nullable=False, default=dict)
    intervention_type = Column(String, nullable=False)
    channel = Column(String, nullable=False)
    template = Column(String, nullable=True)
    variant_group_id = Column(String, nullable=True)
    status = Column(String, nullable=False, default="draft") # draft, active, paused
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    tenant = relationship("Tenant")
    creator = relationship("User")

class Intervention(Base):
    __tablename__ = "interventions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=True)
    channel = Column(String, nullable=False)
    status = Column(String, nullable=False, default="pending") # pending, sent, failed
    sent_at = Column(DateTime(timezone=True), nullable=True)
    manual_override = Column(Boolean, nullable=False, default=False)
    outcome = Column(Enum(InterventionOutcome, name='intervention_outcome'), nullable=False, default=InterventionOutcome.pending)
    outcome_recorded_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    tenant = relationship("Tenant")
    customer = relationship("Customer")
    campaign = relationship("Campaign")

class InAppNotification(Base):
    __tablename__ = "in_app_notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    message = Column(String, nullable=False)
    is_read = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    tenant = relationship("Tenant")
    customer = relationship("Customer")

class RoiReport(Base):
    __tablename__ = "roi_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    churn_events_prevented = Column(Float, nullable=False)
    revenue_saved = Column(Float, nullable=False)
    roi_multiple = Column(Float, nullable=False)
    methodology = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    tenant = relationship("Tenant")

class RevenueAtRiskSnapshot(Base):
    __tablename__ = "revenue_at_risk_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    as_of_date = Column(DateTime(timezone=True), nullable=False)
    horizon_30d_expected_loss = Column(Float, nullable=False, default=0.0)
    horizon_60d_expected_loss = Column(Float, nullable=False, default=0.0)
    horizon_90d_expected_loss = Column(Float, nullable=False, default=0.0)
    by_plan_breakdown = Column(JSONB, nullable=False, default=dict)
    by_cohort_breakdown = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    tenant = relationship("Tenant")

    __table_args__ = (
        UniqueConstraint('tenant_id', 'as_of_date', name='uq_tenant_rar_snapshot_date'),
    )

class RevenueAtRiskAlertConfig(Base):
    __tablename__ = "revenue_at_risk_alert_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, unique=True)
    threshold_amount = Column(Float, nullable=False, default=10000.0)
    channel = Column(String, nullable=False, default="slack")
    enabled = Column(Boolean, nullable=False, default=True)
    last_alerted_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    tenant = relationship("Tenant")

class AnomalyEvent(Base):
    __tablename__ = "anomaly_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    anomaly_type = Column(String, nullable=False)  # usage_cliff, login_gap, payment_failure_spike, feature_abandonment
    severity = Column(String, nullable=False, default="high")  # low, medium, high, critical
    detected_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    detail = Column(JSONB, nullable=False, default=dict)
    resolved = Column(Boolean, nullable=False, default=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    tenant = relationship("Tenant")
    customer = relationship("Customer")

class SupportSentimentScore(Base):
    __tablename__ = "support_sentiment_scores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    ticket_id = Column(String, nullable=False)
    source = Column(String, nullable=False, default="zendesk")  # zendesk, intercom, nps
    text_content = Column(String, nullable=False)
    sentiment = Column(Float, nullable=False, default=0.0)  # -1.0 to +1.0
    topics = Column(JSONB, nullable=False, default=list)
    urgency_flag = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    tenant = relationship("Tenant")
    customer = relationship("Customer")

class AccountContact(Base):
    __tablename__ = "account_contacts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    role = Column(String, nullable=False, default="Decision Maker")
    is_champion = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    bounced = Column(Boolean, nullable=False, default=False)
    last_confirmed_active = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    tenant = relationship("Tenant")
    customer = relationship("Customer")

class PlaybookDefinition(Base):
    __tablename__ = "playbook_definitions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    graph = Column(JSONB, nullable=False, default=dict)  # {"nodes": [...], "edges": [...]}
    status = Column(String, nullable=False, default="active")  # active, draft, archived
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    tenant = relationship("Tenant")
    creator = relationship("User")

class PlaybookRun(Base):
    __tablename__ = "playbook_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    playbook_id = Column(UUID(as_uuid=True), ForeignKey("playbook_definitions.id"), nullable=False)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    current_node_id = Column(String, nullable=False)
    status = Column(String, nullable=False, default="running")  # running, paused, completed, failed
    state_data = Column(JSONB, nullable=False, default=dict)  # persisted execution history and variables
    next_step_at = Column(DateTime(timezone=True), nullable=True)
    assigned_csm_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    task_status = Column(String, nullable=True)  # unassigned_overflow, assigned, completed
    started_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)

    tenant = relationship("Tenant")
    playbook = relationship("PlaybookDefinition")
    customer = relationship("Customer")
    assigned_csm = relationship("User")

class CsmProfile(Base):
    __tablename__ = "csm_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    max_active_accounts = Column(Integer, nullable=False, default=20)
    current_active_count = Column(Integer, nullable=False, default=0)
    specialty_tags = Column(JSONB, nullable=False, default=list)  # ["enterprise", "fintech"]
    is_available = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    tenant = relationship("Tenant")
    user = relationship("User")

    __table_args__ = (
        UniqueConstraint('tenant_id', 'user_id', name='uq_tenant_csm_user'),
    )

class ExitSurvey(Base):
    __tablename__ = "exit_surveys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    reason_category = Column(String, nullable=False)  # price, missing_features, poor_support, usability, competitor, other
    free_text = Column(String, nullable=True)
    submitted_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    tenant = relationship("Tenant")
    customer = relationship("Customer")

class Contract(Base):
    __tablename__ = "contracts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    contract_term_months = Column(Integer, nullable=False, default=12)
    renewal_date = Column(DateTime(timezone=True), nullable=False)
    auto_renew = Column(Boolean, nullable=False, default=True)
    contract_value_mrr = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    tenant = relationship("Tenant")
    customer = relationship("Customer")



class ApiKey(Base):
    """Tenant-scoped API keys for public/external embedding. Keys are hashed at rest."""
    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    name = Column(String, nullable=False)  # human label e.g. "Prod SDK key"
    hashed_key = Column(String, nullable=False, unique=True)
    key_prefix = Column(String, nullable=False)  # first 8 chars for display e.g. "cgk_a1b2"
    scope = Column(String, nullable=False, default="read")  # "read" or "read_write"
    is_active = Column(Boolean, nullable=False, default=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    tenant = relationship("Tenant")
    creator = relationship("User")

    __table_args__ = (
        UniqueConstraint('tenant_id', 'name', name='uq_tenant_apikey_name'),
    )


class CrmSyncLog(Base):
    """Tracks outbound CRM sync events (Salesforce / HubSpot)."""
    __tablename__ = "crm_sync_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    crm_type = Column(String, nullable=False)  # "salesforce" | "hubspot"
    status = Column(String, nullable=False, default="pending")  # pending | success | failed
    fields_pushed = Column(JSONB, nullable=False, default=dict)
    error_message = Column(String, nullable=True)
    synced_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    tenant = relationship("Tenant")
    customer = relationship("Customer")


class ModelFairnessReport(Base):
    """Per-segment model calibration / error-rate parity report."""
    __tablename__ = "model_fairness_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    dimension = Column(String, nullable=False)    # plan_tier, industry, company_size_band
    generated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    segments = Column(JSONB, nullable=False, default=list)  # per-segment calibration metrics
    flagged_segments = Column(JSONB, nullable=False, default=list)  # segments with parity violations
    methodology = Column(String, nullable=False, default="")

    tenant = relationship("Tenant")






