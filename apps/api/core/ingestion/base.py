from abc import ABC, abstractmethod
from typing import Any

from .schema import CustomerEventSchema


class SourceAdapter(ABC):
    @property
    @abstractmethod
    def source_name(self) -> str:
        """The identifier for this source (e.g., 'stripe')"""

    @abstractmethod
    def normalize_payload(self, payload: dict[str, Any]) -> list[CustomerEventSchema]:
        """Convert a webhook payload into one or more normalized CustomerEvents."""
