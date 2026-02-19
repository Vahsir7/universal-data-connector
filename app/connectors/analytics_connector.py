"""Analytics / metrics connector — loads time-series data from a local JSON file.

Provides metrics like daily_active_users, page_views, error_rate, etc.
In production this would query a metrics store (e.g. Prometheus, Datadog).
"""

import json
from pathlib import Path
from typing import Any, Dict, List

from app.connectors.base import BaseConnector


class AnalyticsConnector(BaseConnector):
    """Reads analytics/metrics records from data/analytics.json."""

    def fetch(self, **_kwargs) -> List[Dict[str, Any]]:
        file_path = Path(__file__).resolve().parents[2] / "data" / "analytics.json"
        try:
            with file_path.open("r", encoding="utf-8") as file_obj:
                payload = json.load(file_obj)
        except FileNotFoundError as exc:
            raise RuntimeError(f"Analytics data file not found: {file_path}") from exc
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Analytics data file is invalid JSON: {file_path}") from exc

        if not isinstance(payload, list):
            raise RuntimeError("Analytics data payload must be a list")

        return payload
