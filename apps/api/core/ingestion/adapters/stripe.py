import datetime
from typing import Any

from ..base import SourceAdapter
from ..schema import CustomerEventSchema


class StripeAdapter(SourceAdapter):
    @property
    def source_name(self) -> str:
        return "stripe"

    def normalize_payload(self, payload: dict[str, Any]) -> list[CustomerEventSchema]:
        event_type = payload.get("type", "unknown")
        event_id = payload.get("id")
        created = payload.get("created")
        data = payload.get("data", {}).get("object", {})
        
        customer = data.get("customer")
        
        if not event_id or not customer or not created:
            # Skip invalid payload
            return []

        occurred_at = datetime.datetime.fromtimestamp(created, tz=datetime.UTC)

        return [
            CustomerEventSchema(
                source=self.source_name,
                external_event_id=event_id,
                external_customer_id=customer,
                event_type=event_type,
                properties=data,
                occurred_at=occurred_at
            )
        ]
