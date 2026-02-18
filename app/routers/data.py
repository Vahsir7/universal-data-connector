import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.config import settings
from app.connectors.analytics_connector import AnalyticsConnector
from app.connectors.crm_connector import CRMConnector
from app.connectors.support_connector import SupportConnector
from app.models.common import DataResponse, Metadata
from app.services.business_rules import apply_voice_limits
from app.services.data_identifier import identify_data_type
from app.services.voice_optimizer import summarize_if_large
from app.services.business_rules import apply_business_filters, prioritize_for_voice, paginate_data, apply_voice_limits

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/data/{source}", response_model=DataResponse)
def get_data(
    source: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=settings.MAX_RESULTS),
    status: Optional[str] = Query(default=None),
    priority: Optional[str] = Query(default=None),
    metric: Optional[str] = Query(default=None),
    start_date: Optional[str] = Query(default=None),
    end_date: Optional[str] = Query(default=None),
    ):


    connector_map = {
        "crm": CRMConnector(),
        "support": SupportConnector(),
        "analytics": AnalyticsConnector(),
    }

    connector = connector_map.get(source)
    if connector is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "SOURCE_NOT_FOUND",
                "message": f"Unknown source '{source}'. Valid values: {list(connector_map.keys())}",
            },
        )

    try:
        raw_data = connector.fetch()
    except Exception as exc:
        logger.exception("Connector error for source '%s': %s", source, exc)
        raise HTTPException(
            status_code=503,
            detail={
                "code": "DATA_SOURCE_UNAVAILABLE",
                "message": f"Data source '{source}' is temporarily unavailable",
            },
        ) from exc

    filtered = apply_business_filters(
    data=raw_data,
    status=status,
    priority=priority,
    metric=metric,
    start_date=start_date,
    end_date=end_date,
)
    prioritized = prioritize_for_voice(filtered)
    paged, total_pages, has_next = paginate_data(prioritized, page=page, page_size=page_size)
    limited = apply_voice_limits(paged, limit=page_size)
    optimized = summarize_if_large(limited)
    _data_type = identify_data_type(raw_data)
    total = len(filtered)

    metadata = Metadata(
        total_results=total,
        returned_results=len(optimized),
        data_freshness=f"Data as of {datetime.now().isoformat()}",
        data_type=_data_type,
    )

    return DataResponse(data=optimized, metadata=metadata)