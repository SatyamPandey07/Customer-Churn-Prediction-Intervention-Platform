import datetime
from typing import Any

from ..base import SourceAdapter
from ..schema import CustomerEventSchema


class ZendeskAdapter(SourceAdapter):
    @property
    def source_name(self) -> str:
        return "zendesk"

    def normalize_payload(self, payload: dict[str, Any]) -> list[CustomerEventSchema]:
        ticket_id = str(payload.get("ticket_id") or payload.get("id") or "")
        customer_id = str(payload.get("customer_id") or payload.get("requester_id") or "")
        if not ticket_id or not customer_id:
            return []

        ts_str = payload.get("created_at") or payload.get("timestamp")
        if ts_str:
            try:
                occurred_at = datetime.datetime.fromisoformat(str(ts_str))
            except Exception:
                occurred_at = datetime.datetime.now(datetime.UTC)
        else:
            occurred_at = datetime.datetime.now(datetime.UTC)

        subject = payload.get("subject", "")
        comment = payload.get("comment") or payload.get("description") or ""
        full_text = f"{subject}\n{comment}".strip()

        return [
            CustomerEventSchema(
                source=self.source_name,
                external_event_id=f"zd_{ticket_id}",
                external_customer_id=customer_id,
                event_type="support_ticket.created",
                properties={
                    "ticket_id": ticket_id,
                    "subject": subject,
                    "comment": comment,
                    "text_content": full_text
                },
                occurred_at=occurred_at
            )
        ]
