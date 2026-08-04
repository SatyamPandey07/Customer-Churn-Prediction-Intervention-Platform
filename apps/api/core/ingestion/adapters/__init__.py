from .amplitude import AmplitudeAdapter
from .generic import GenericWebhookAdapter
from .intercom import IntercomAdapter
from .nps import NpsSurveyAdapter
from .segment import SegmentAdapter
from .stripe import StripeAdapter
from .zendesk import ZendeskAdapter


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

