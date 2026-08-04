import datetime
from typing import Any

from ..base import SourceAdapter
from ..schema import CustomerEventSchema


class AmplitudeAdapter(SourceAdapter):
    @property
    def source_name(self) -> str:
        return "amplitude"

    def normalize_payload(self, payload: dict[str, Any]) -> list[CustomerEventSchema]:
        # Amplitude usually sends a batch of events
        events = payload.get("events", [])
        if not events and "event_type" in payload:
            # Handle single event payload
            events = [payload]
            
        normalized = []
        for evt in events:
            user_id = evt.get("user_id")
            event_type = evt.get("event_type")
            insert_id = evt.get("insert_id") # Unique ID for idempotency
            time_ms = evt.get("time") # Milliseconds epoch
            
            if not user_id or not event_type or not insert_id or not time_ms:
                continue
                
            occurred_at = datetime.datetime.fromtimestamp(time_ms / 1000.0, tz=datetime.UTC)
            properties = evt.get("event_properties", {})
            
            normalized.append(
                CustomerEventSchema(
                    source=self.source_name,
                    external_event_id=insert_id,
                    external_customer_id=user_id,
                    event_type=event_type,
                    properties=properties,
                    occurred_at=occurred_at
                )
            )
            
        return normalized
