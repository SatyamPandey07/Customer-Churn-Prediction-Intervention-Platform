from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class CustomerEventSchema(BaseModel):
    source: str
    external_event_id: str
    external_customer_id: str
    event_type: str
    properties: dict[str, Any] = Field(default_factory=dict)
    occurred_at: datetime
