from datetime import datetime, timezone
from typing import Dict, Any, List
from ..base import SourceAdapter
from ..schema import CustomerEventSchema

class SegmentAdapter(SourceAdapter):
    @property
    def source_name(self) -> str:
        return "segment"

    def normalize_payload(self, payload: Dict[str, Any]) -> List[CustomerEventSchema]:
        # Segment sends track/identify/page/screen calls
        msg_type = payload.get("type", "unknown")
        message_id = payload.get("messageId")
        user_id = payload.get("userId") or payload.get("anonymousId")
        timestamp_str = payload.get("timestamp")
        
        if not message_id or not user_id or not timestamp_str:
            return []

        if msg_type == "track":
            event_type = payload.get("event", "track")
            properties = payload.get("properties", {})
        elif msg_type == "identify":
            event_type = "identify"
            properties = payload.get("traits", {})
        else:
            event_type = msg_type
            properties = payload.get("properties", {})

        try:
            occurred_at = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except ValueError:
            occurred_at = datetime.now(timezone.utc)

        return [
            CustomerEventSchema(
                source=self.source_name,
                external_event_id=message_id,
                external_customer_id=user_id,
                event_type=event_type,
                properties=properties,
                occurred_at=occurred_at
            )
        ]
