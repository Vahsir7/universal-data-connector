import logging
import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from fastapi.responses import StreamingResponse

from app.config import settings
from app.models.common import DataResponse, ErrorResponse
from app.services.cache import build_data_cache_key, cache_service
from app.services.auth import require_api_key
from app.services.data_service import DataSource, get_unified_data
from app.services.rate_limiter import rate_limiter


router = APIRouter()
logger = logging.getLogger(__name__)


@router.get(
    "/data/{source}",
    response_model=DataResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Unknown source"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
        422: {"model": ErrorResponse, "description": "Validation error"},
        503: {"model": ErrorResponse, "description": "Data source unavailable"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="Fetch unified data for LLM tool calling",
    description="Returns filtered, paginated, voice-optimized data with metadata.",
    tags=["Data"],
)
def get_data(
    request: Request,
    source: DataSource = Path(..., description="Data source", examples=["crm"]),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(settings.DEFAULT_PAGE_SIZE, ge=1, le=settings.MAX_PAGE_SIZE, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter by status (crm/support)"),
    priority: Optional[str] = Query(None, description="Filter by priority (support)"),
    metric: Optional[str] = Query(None, description="Filter by metric name (analytics)"),
    start_date: Optional[str] = Query(None, description="ISO date/datetime start"),
    end_date: Optional[str] = Query(None, description="ISO date/datetime end"),
    stream: bool = Query(False, description="Stream large responses as NDJSON"),
    _auth: None = Depends(require_api_key),
):
    client_id = request.client.host if request.client and request.client.host else "anonymous"
    allowed, retry_after = rate_limiter.allow(source=source.value, client_id=client_id)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail={
                "code": "RATE_LIMIT_EXCEEDED",
                "message": f"Rate limit exceeded for source '{source.value}'. Retry after {retry_after}s",
                "details": {"retry_after_seconds": retry_after},
            },
        )

    cache_key = build_data_cache_key(
        path=f"/data/{source.value}",
        params={
            "page": page,
            "page_size": page_size,
            "status": status,
            "priority": priority,
            "metric": metric,
            "start_date": start_date,
            "end_date": end_date,
        },
    )

    cached = cache_service.get(cache_key)
    if cached is not None:
        response_payload = DataResponse.model_validate(cached)
    else:
        try:
            response_payload = get_unified_data(
                source=source,
                page=page,
                page_size=page_size,
                status=status,
                priority=priority,
                metric=metric,
                start_date=start_date,
                end_date=end_date,
            )
        except Exception as exc:
            logger.exception("Connector error for source '%s': %s", source.value, exc)
            raise HTTPException(
                status_code=503,
                detail={
                    "code": "DATA_SOURCE_UNAVAILABLE",
                    "message": f"Data source '{source.value}' is temporarily unavailable",
                    "details": str(exc),
                },
            ) from exc

        cache_service.set(
            key=cache_key,
            value=response_payload.model_dump(),
            ttl_seconds=settings.CACHE_TTL_SECONDS,
        )

    should_stream = (
        stream
        and settings.ENABLE_STREAMING
        and response_payload.metadata.total_results >= settings.STREAM_MIN_TOTAL_RESULTS
    )

    if should_stream:
        chunk_size = settings.STREAM_CHUNK_SIZE

        def _iter_ndjson():
            yield json.dumps({"type": "metadata", "metadata": response_payload.metadata.model_dump()}) + "\n"
            for index in range(0, len(response_payload.data), chunk_size):
                chunk = response_payload.data[index:index + chunk_size]
                for row in chunk:
                    yield json.dumps({"type": "record", "data": row}) + "\n"
            yield json.dumps({"type": "end", "count": len(response_payload.data)}) + "\n"

        return StreamingResponse(_iter_ndjson(), media_type="application/x-ndjson")

    return response_payload