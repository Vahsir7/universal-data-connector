"""Abstract base class for all data connectors."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any


class BaseConnector(ABC):
    """Interface that every data-source connector must implement."""

    @abstractmethod
    def fetch(self, **kwargs) -> List[Dict[str, Any]]:
        """Return all records from the data source as a list of dicts."""
        pass
