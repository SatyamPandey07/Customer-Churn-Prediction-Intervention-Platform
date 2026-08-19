from datetime import UTC, datetime
from typing import Any

from ..base import SourceAdapter
from ..schema import CustomerEventSchema


class GenericWebhookAdapter(SourceAdapter):
    def __init__(self, source_name: str = "generic", mapping_rules: dict[str, str] | None = None):
        self._source_name = source_name
        self.mapping_rules = mapping_rules or {}

    @property
    def source_name(self) -> str:
        return self._source_name

    def _get_field(self, payload: dict[str, Any], field_name: str, default_key: str) -> Any:
        # Use mapped key if it exists in rules, otherwise use default
        key = self.mapping_rules.get(field_name, default_key)
        return payload.get(key)

    def normalize_payload(self, payload: dict[str, Any]) -> list[CustomerEventSchema]:
        external_customer_id = self._get_field(payload, "customer_id", "external_customer_id")
        event_type = self._get_field(payload, "event_type", "event_type")
        external_event_id = self._get_field(payload, "event_id", "external_event_id")
        
        # If external_event_id is missing but we have the other two, generate one for the user
        if not external_event_id and external_customer_id and event_type:
            import uuid
            external_event_id = f"evt_{uuid.uuid4().hex[:12]}"
            
        if not external_event_id or not external_customer_id or not event_type:
            raise ValueError(f"Malformed payload: missing required mapped fields (customer_id, event_type). Keys present: {list(payload.keys())}")
            
        occurred_at_str = self._get_field(payload, "occurred_at", "occurred_at")
        if occurred_at_str:
            try:
                occurred_at = datetime.fromisoformat(occurred_at_str)
            except ValueError:
                occurred_at = datetime.now(UTC)
        else:
            occurred_at = datetime.now(UTC)
            
        properties = self._get_field(payload, "properties", "properties") or {}
        if not isinstance(properties, dict):
            properties = {"raw_value": properties}
        
        return [
            CustomerEventSchema(
                source=self.source_name,
                external_event_id=external_event_id,
                external_customer_id=external_customer_id,
                event_type=event_type,
                properties=properties,
                occurred_at=occurred_at
            )
        ]
