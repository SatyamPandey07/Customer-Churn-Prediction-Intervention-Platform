from datetime import datetime
from apps.api.core.ingestion.adapters.stripe import StripeAdapter
from apps.api.core.ingestion.adapters.segment import SegmentAdapter
from apps.api.core.ingestion.adapters.amplitude import AmplitudeAdapter

def test_stripe_adapter():
    payload = {
        "id": "evt_123",
        "type": "invoice.paid",
        "created": 1690000000,
        "data": {
            "object": {
                "customer": "cus_123",
                "amount_paid": 1000
            }
        }
    }
    adapter = StripeAdapter()
    events = adapter.normalize_payload(payload)
    
    assert len(events) == 1
    evt = events[0]
    assert evt.source == "stripe"
    assert evt.external_event_id == "evt_123"
    assert evt.external_customer_id == "cus_123"
    assert evt.event_type == "invoice.paid"
    assert evt.properties["amount_paid"] == 1000

def test_segment_adapter():
    payload = {
        "type": "track",
        "messageId": "msg_123",
        "userId": "u_456",
        "event": "Item Purchased",
        "properties": {"revenue": 10},
        "timestamp": "2023-01-01T00:00:00Z"
    }
    adapter = SegmentAdapter()
    events = adapter.normalize_payload(payload)
    
    assert len(events) == 1
    evt = events[0]
    assert evt.source == "segment"
    assert evt.external_event_id == "msg_123"
    assert evt.external_customer_id == "u_456"
    assert evt.event_type == "Item Purchased"
    assert evt.occurred_at.year == 2023

def test_amplitude_adapter():
    payload = {
        "events": [
            {
                "event_type": "login",
                "user_id": "u_789",
                "time": 1690000000000,
                "insert_id": "ins_123",
                "event_properties": {"source": "web"}
            }
        ]
    }
    adapter = AmplitudeAdapter()
    events = adapter.normalize_payload(payload)
    
    assert len(events) == 1
    evt = events[0]
    assert evt.source == "amplitude"
    assert evt.external_event_id == "ins_123"
    assert evt.external_customer_id == "u_789"
    assert evt.event_type == "login"
    assert evt.properties["source"] == "web"
