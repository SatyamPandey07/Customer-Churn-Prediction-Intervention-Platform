from .stripe import StripeAdapter
from .segment import SegmentAdapter
from .amplitude import AmplitudeAdapter
from .generic import GenericWebhookAdapter

def get_adapter(source_name: str):
    adapters = {
        "stripe": StripeAdapter(),
        "segment": SegmentAdapter(),
        "amplitude": AmplitudeAdapter(),
        "generic": GenericWebhookAdapter(),
    }
    return adapters.get(source_name)
