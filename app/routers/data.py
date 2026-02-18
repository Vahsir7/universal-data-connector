import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query

from app.config import settings
from app.connectors.analytics_connector import AnalyticsConnector
from app.connectors.crm_connector import CRMConnector
from app.connectors.support_connector import SupportConnector
from app.models.common import DataResponse, Metadata
from app.services.business_rules import apply_voice_limits
from app.services.data_identifier import identify_data_type
from app.services.voice_optimizer import summarize_if_large

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/data/{source}", response_model=DataResponse)
def get_data(
    source: str,
    limit: int = Query(default=10, ge=1, le=settings.MAX_RESULTS),
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

    total = len(raw_data)
    filtered = apply_voice_limits(raw_data, limit=limit)
    optimized = summarize_if_large(filtered)
    _data_type = identify_data_type(raw_data)

    metadata = Metadata(
        total_results=total,
        returned_results=len(optimized),
        data_freshness=f"Data as of {datetime.now().isoformat()}",
    )

    return DataResponse(data=optimized, metadata=metadata)