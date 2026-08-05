"""
CRM outbound sync adapters: SalesforceAdapter and HubSpotAdapter.
Follow the same SourceAdapter-style abstraction as PR-03, but for OUTBOUND sync.
Mocked against fixture CRM APIs initially — swap in real keys later.
"""
import logging
from typing import Any

logger = logging.getLogger(__name__)

SALESFORCE_FIELD_MAP = {
    "churn_risk_tier": "ChurnGuard_Risk_Tier__c",
    "churn_probability": "ChurnGuard_Probability__c",
    "health_score": "ChurnGuard_Health_Score__c",
    "open_interventions": "ChurnGuard_Open_Interventions__c"
}

HUBSPOT_PROPERTY_MAP = {
    "churn_risk_tier": "churnguard_risk_tier",
    "churn_probability": "churnguard_churn_probability",
    "health_score": "churnguard_health_score",
    "open_interventions": "churnguard_open_interventions"
}


class CrmAdapter:
    """Base class for outbound CRM sync adapters."""
    crm_type: str = "base"

    async def push_customer_fields(self, crm_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError


class SalesforceAdapter(CrmAdapter):
    """
    Outbound sync adapter for Salesforce.
    Pushes ChurnGuard risk/health fields onto the Account or Contact record.
    Mocked against fixture APIs; swap SALESFORCE_INSTANCE_URL + credentials in prod.
    """
    crm_type = "salesforce"

    def __init__(self, instance_url: str | None = None, access_token: str | None = None):
        self.instance_url = instance_url or "https://mock.salesforce.com"
        self.access_token = access_token or "mock_sf_token"

    async def push_customer_fields(self, crm_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        """
        Pushes mapped custom fields onto Salesforce Account record.
        Returns the fields pushed for audit logging.
        """
        sf_fields = {
            SALESFORCE_FIELD_MAP[k]: v
            for k, v in fields.items()
            if k in SALESFORCE_FIELD_MAP
        }

        # Mock PATCH call; in prod this would be:
        # PATCH {instance_url}/services/data/v60.0/sobjects/Account/{crm_id}
        logger.info(
            "SalesforceAdapter: PATCH Account/%s fields=%s [MOCK]",
            crm_id, sf_fields
        )
        # Simulate success response
        return {"crm_id": crm_id, "status": "success", "pushed_fields": sf_fields}

    async def push_contact_fields(self, crm_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        """Same as push_customer_fields but targets Contact object."""
        sf_fields = {
            SALESFORCE_FIELD_MAP[k]: v
            for k, v in fields.items()
            if k in SALESFORCE_FIELD_MAP
        }
        logger.info("SalesforceAdapter: PATCH Contact/%s fields=%s [MOCK]", crm_id, sf_fields)
        return {"crm_id": crm_id, "status": "success", "pushed_fields": sf_fields}


class HubSpotAdapter(CrmAdapter):
    """
    Outbound sync adapter for HubSpot.
    Pushes ChurnGuard risk/health properties onto the Company or Contact record.
    Mocked against fixture APIs; swap HUBSPOT_API_KEY in prod.
    """
    crm_type = "hubspot"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or "mock_hs_api_key"

    async def push_customer_fields(self, crm_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        """
        Pushes mapped custom properties onto HubSpot Company record.
        Returns the fields pushed for audit logging.
        """
        hs_props = {
            HUBSPOT_PROPERTY_MAP[k]: v
            for k, v in fields.items()
            if k in HUBSPOT_PROPERTY_MAP
        }
        # Mock PATCH call; in prod this would be:
        # PATCH https://api.hubapi.com/crm/v3/objects/companies/{crm_id}
        logger.info(
            "HubSpotAdapter: PATCH Company/%s properties=%s [MOCK]",
            crm_id, hs_props
        )
        return {"crm_id": crm_id, "status": "success", "pushed_fields": hs_props}

    async def push_contact_fields(self, crm_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        hs_props = {
            HUBSPOT_PROPERTY_MAP[k]: v
            for k, v in fields.items()
            if k in HUBSPOT_PROPERTY_MAP
        }
        logger.info("HubSpotAdapter: PATCH Contact/%s properties=%s [MOCK]", crm_id, hs_props)
        return {"crm_id": crm_id, "status": "success", "pushed_fields": hs_props}


def get_crm_adapter(crm_type: str, **kwargs) -> CrmAdapter:
    """Factory: returns the correct outbound CRM adapter."""
    if crm_type == "salesforce":
        return SalesforceAdapter(**kwargs)
    elif crm_type == "hubspot":
        return HubSpotAdapter(**kwargs)
    else:
        raise ValueError(f"Unknown CRM type: {crm_type}")
