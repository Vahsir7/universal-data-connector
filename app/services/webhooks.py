"""Webhook event store – persists inbound webhook payloads in SQLite.

The webhook router appends events here; the events endpoint reads
them back in reverse-chronological order.
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List

from app.services.db import get_db_service


class WebhookEventStore:
    """Append-only log of received webhook events (SQLite-backed)."""
    def __init__(self) -> None:
        self._db = get_db_service()

    def append(self, event: Dict[str, Any]) -> None:
        received_at = datetime.now(timezone.utc).isoformat()
        source = str(event.get("source", ""))
        event_type = str(event.get("event_type", "update"))
        payload = event.get("payload", {})

        self._db.execute(
            """
            INSERT INTO webhook_events (received_at, source, event_type, payload)
            VALUES (?, ?, ?, ?)
            """,
            (received_at, source, event_type, json.dumps(payload)),
        )

    def list_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        if limit <= 0:
            return []
        rows = self._db.fetchall(
            """
            SELECT received_at, source, event_type, payload
            FROM webhook_events
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [
            {
                "received_at": str(row["received_at"]),
                "source": str(row["source"] or ""),
                "event_type": str(row["event_type"] or "update"),
                "payload": json.loads(str(row["payload"] or "{}")),
            }
            for row in rows
        ]


webhook_event_store = WebhookEventStore()
