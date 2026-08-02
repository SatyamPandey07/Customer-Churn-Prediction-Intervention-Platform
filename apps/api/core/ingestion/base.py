from abc import ABC, abstractmethod
from typing import Dict, Any, List
from .schema import CustomerEventSchema

class SourceAdapter(ABC):
    @property
    @abstractmethod
    def source_name(self) -> str:
        """The identifier for this source (e.g., 'stripe')"""
        pass

    @abstractmethod
    def normalize_payload(self, payload: Dict[str, Any]) -> List[CustomerEventSchema]:
        """Convert a webhook payload into one or more normalized CustomerEvents."""
        pass
