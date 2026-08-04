import datetime
from typing import Dict, Any, List
from ..base import SourceAdapter
from ..schema import CustomerEventSchema

class IntercomAdapter(SourceAdapter):
    @property
    def source_name(self) -> str:
        return "intercom"

    def normalize_payload(self, payload: Dict[str, Any]) -> List[CustomerEventSchema]:
        conv_id = str(payload.get("conversation_id") or payload.get("id") or "")
        user_id = str(payload.get("user_id") or payload.get("customer_id") or "")
        if not conv_id or not user_id:
            return []

        ts = payload.get("created_at")
        if isinstance(ts, (int, float)):
            occurred_at = datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc)
        elif isinstance(ts, str):
            try:
                occurred_at = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except Exception:
                occurred_at = datetime.datetime.now(datetime.timezone.utc)
        else:
            occurred_at = datetime.datetime.now(datetime.timezone.utc)

        msg = payload.get("message") or payload.get("body") or ""

        return [
            CustomerEventSchema(
                source=self.source_name,
                external_event_id=f"ic_{conv_id}",
                external_customer_id=user_id,
                event_type="support_ticket.created",
                properties={
                    "ticket_id": conv_id,
                    "message": msg,
                    "text_content": msg
                },
                occurred_at=occurred_at
            )
        ]
