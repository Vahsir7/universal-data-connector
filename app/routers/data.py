import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Path, Query

from app.config import settings
from app.models.common import DataResponse, ErrorResponse
from app.services.data_service import DataSource, get_unified_data


router = APIRouter()
logger = logging.getLogger(__name__)


@router.get(
    "/data/{source}",
    response_model=DataResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Unknown source"},
        422: {"model": ErrorResponse, "description": "Validation error"},
        503: {"model": ErrorResponse, "description": "Data source unavailable"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="Fetch unified data for LLM tool calling",
    description="Returns filtered, paginated, voice-optimized data with metadata.",
    tags=["Data"],
)
def get_data(
    source: DataSource = Path(..., description="Data source", examples=["crm"]),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(settings.DEFAULT_PAGE_SIZE, ge=1, le=settings.MAX_PAGE_SIZE, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter by status (crm/support)"),
    priority: Optional[str] = Query(None, description="Filter by priority (support)"),
    metric: Optional[str] = Query(None, description="Filter by metric name (analytics)"),
    start_date: Optional[str] = Query(None, description="ISO date/datetime start"),
    end_date: Optional[str] = Query(None, description="ISO date/datetime end"),
):
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
    return response_payload