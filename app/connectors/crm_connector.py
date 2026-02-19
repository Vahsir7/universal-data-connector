"""CRM data connector — loads customer records from a local JSON file."""

import json
from pathlib import Path
from typing import Any, Dict, List

from app.connectors.base import BaseConnector


class CRMConnector(BaseConnector):
    """Reads customer records from data/customers.json."""

    def fetch(self, **_kwargs) -> List[Dict[str, Any]]:
        # Resolve path relative to project root (two parents up from connectors/)
        file_path = Path(__file__).resolve().parents[2] / "data" / "customers.json"
        try:
            with file_path.open("r", encoding="utf-8") as file_obj:
                payload = json.load(file_obj)
        except FileNotFoundError as exc:
            raise RuntimeError(f"CRM data file not found: {file_path}") from exc
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"CRM data file is invalid JSON: {file_path}") from exc

        # Safeguard: the file must contain a JSON array of customer dicts
        if not isinstance(payload, list):
            raise RuntimeError("CRM data payload must be a list")

        return payload
