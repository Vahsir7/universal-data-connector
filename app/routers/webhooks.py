"""Webhook router — receive real-time update notifications from external systems.

When a data source changes, the external system POSTs to /webhooks/events.
If the event references a known source (crm/support/analytics), relevant
cache entries are invalidated so subsequent requests fetch fresh data.

Optionally protected by a shared secret in the X-Webhook-Secret header.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from app.config import settings
from app.services.auth import require_admin_key
from app.services.cache import cache_service
from app.services.webhooks import webhook_event_store


router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


class WebhookEventRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    source: Optional[str] = Field(default=None, description="Optional data source impacted by update")
    event_type: str = Field(default="update")
    payload: Dict[str, Any] = Field(default_factory=dict)


class WebhookEventResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    invalidated_cache_keys: int


def _verify_webhook_secret(x_webhook_secret: Optional[str]) -> None:
    expected = settings.WEBHOOK_SHARED_SECRET.get_secret_value() if settings.WEBHOOK_SHARED_SECRET else ""
    if expected and x_webhook_secret != expected:
        raise HTTPException(
            status_code=401,
            detail={
                "code": "WEBHOOK_INVALID_SECRET",
                "message": "Invalid webhook secret",
            },
        )


@router.post("/events", response_model=WebhookEventResponse)
def ingest_webhook_event(
    payload: WebhookEventRequest,
    x_webhook_secret: Optional[str] = Header(default=None, alias="X-Webhook-Secret"),
) -> WebhookEventResponse:
    _verify_webhook_secret(x_webhook_secret)

    # If the event names a known data source, bust the cache for that prefix
    source = (payload.source or "").strip().lower()
    invalidated = 0
    if source in {"crm", "support", "analytics"}:
        invalidated = cache_service.delete_prefix("udc:data:")

    webhook_event_store.append(payload.model_dump())
    return WebhookEventResponse(status="accepted", invalidated_cache_keys=invalidated)


@router.get("/events", dependencies=[Depends(require_admin_key)])
def list_webhook_events(limit: int = Query(20, ge=1, le=200)) -> List[Dict[str, Any]]:
    return webhook_event_store.list_events(limit=limit)
