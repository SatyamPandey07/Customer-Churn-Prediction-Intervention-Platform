from .stripe import StripeAdapter
from .segment import SegmentAdapter
from .amplitude import AmplitudeAdapter
from .generic import GenericWebhookAdapter
from .zendesk import ZendeskAdapter
from .intercom import IntercomAdapter
from .nps import NpsSurveyAdapter

def get_adapter(source_name: str):
    adapters = {
        "stripe": StripeAdapter(),
        "segment": SegmentAdapter(),
        "amplitude": AmplitudeAdapter(),
        "generic": GenericWebhookAdapter(),
        "zendesk": ZendeskAdapter(),
        "intercom": IntercomAdapter(),
        "nps": NpsSurveyAdapter(),
    }
    return adapters.get(source_name)

