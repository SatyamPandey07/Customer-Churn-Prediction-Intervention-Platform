import datetime
from typing import Dict, Any, List
from ..base import SourceAdapter
from ..schema import CustomerEventSchema

class NpsSurveyAdapter(SourceAdapter):
    @property
    def source_name(self) -> str:
        return "nps"

    def normalize_payload(self, payload: Dict[str, Any]) -> List[CustomerEventSchema]:
        survey_id = str(payload.get("survey_id") or payload.get("id") or "")
        customer_id = str(payload.get("customer_id") or payload.get("user_id") or "")
        if not survey_id or not customer_id:
            return []

        ts_str = payload.get("submitted_at") or payload.get("timestamp")
        if ts_str:
            try:
                occurred_at = datetime.datetime.fromisoformat(str(ts_str).replace("Z", "+00:00"))
            except Exception:
                occurred_at = datetime.datetime.now(datetime.timezone.utc)
        else:
            occurred_at = datetime.datetime.now(datetime.timezone.utc)

        score = float(payload.get("score", 5))
        feedback = payload.get("feedback") or payload.get("comment") or ""

        return [
            CustomerEventSchema(
                source=self.source_name,
                external_event_id=f"nps_{survey_id}",
                external_customer_id=customer_id,
                event_type="nps_survey.submitted",
                properties={
                    "survey_id": survey_id,
                    "score": score,
                    "feedback": feedback,
                    "text_content": feedback
                },
                occurred_at=occurred_at
            )
        ]
