from datetime import datetime
from pydantic import BaseModel, Field
from typing import Any, Dict

class CustomerEventSchema(BaseModel):
    source: str
    external_event_id: str
    external_customer_id: str
    event_type: str
    properties: Dict[str, Any] = Field(default_factory=dict)
    occurred_at: datetime
