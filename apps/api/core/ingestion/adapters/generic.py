from datetime import UTC, datetime
from typing import Any

from ..base import SourceAdapter
from ..schema import CustomerEventSchema


class GenericWebhookAdapter(SourceAdapter):
    @property
    def source_name(self) -> str:
        return "generic"

    def normalize_payload(self, payload: dict[str, Any]) -> list[CustomerEventSchema]:
        external_event_id = payload.get("external_event_id")
        external_customer_id = payload.get("external_customer_id")
        event_type = payload.get("event_type")
        
        if not external_event_id or not external_customer_id or not event_type:
            return []
            
        occurred_at_str = payload.get("occurred_at")
        if occurred_at_str:
            try:
                occurred_at = datetime.fromisoformat(occurred_at_str)
            except ValueError:
                occurred_at = datetime.now(UTC)
        else:
            occurred_at = datetime.now(UTC)
            
        properties = payload.get("properties", {})
        
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
