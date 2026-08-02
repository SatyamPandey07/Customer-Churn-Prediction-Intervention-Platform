from datetime import datetime, timezone
from typing import Dict, Any, List
from ..base import SourceAdapter
from ..schema import CustomerEventSchema

class GenericWebhookAdapter(SourceAdapter):
    @property
    def source_name(self) -> str:
        return "generic"

    def normalize_payload(self, payload: Dict[str, Any]) -> List[CustomerEventSchema]:
        external_event_id = payload.get("external_event_id")
        external_customer_id = payload.get("external_customer_id")
        event_type = payload.get("event_type")
        
        if not external_event_id or not external_customer_id or not event_type:
            return []
            
        occurred_at_str = payload.get("occurred_at")
        if occurred_at_str:
            try:
                occurred_at = datetime.fromisoformat(occurred_at_str.replace('Z', '+00:00'))
            except ValueError:
                occurred_at = datetime.now(timezone.utc)
        else:
            occurred_at = datetime.now(timezone.utc)
            
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
