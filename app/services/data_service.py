from enum import Enum
from typing import Optional

from app.connectors.analytics_connector import AnalyticsConnector
from app.connectors.crm_connector import CRMConnector
from app.connectors.support_connector import SupportConnector
from app.models.common import DataResponse, Metadata
from app.services.business_rules import (
    apply_business_filters,
    apply_voice_limits,
    paginate_data,
    prioritize_for_voice,
)
from app.services.data_identifier import (
    apply_data_transformation,
    get_freshness_info,
    identify_data_type,
)
from app.services.voice_optimizer import summarize_if_large


class DataSource(str, Enum):
    crm = "crm"
    support = "support"
    analytics = "analytics"


CONNECTOR_MAP = {
    DataSource.crm: CRMConnector,
    DataSource.support: SupportConnector,
    DataSource.analytics: AnalyticsConnector,
}


def get_unified_data(
    source: DataSource,
    page: int,
    page_size: int,
    ticket_id: Optional[int] = None,
    customer_id: Optional[int] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    metric: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> DataResponse:
    connector_cls = CONNECTOR_MAP[source]
    raw_data = connector_cls().fetch()

    filtered = apply_business_filters(
        data=raw_data,
        ticket_id=ticket_id,
        customer_id=customer_id,
        status=status,
        priority=priority,
        metric=metric,
        start_date=start_date,
        end_date=end_date,
    )

    prioritized = prioritize_for_voice(filtered)
    paged, total_pages, has_next = paginate_data(prioritized, page=page, page_size=page_size)
    limited = apply_voice_limits(paged, limit=page_size)

    data_type = identify_data_type(raw_data)
    transformed = apply_data_transformation(limited, data_type)
    optimized = summarize_if_large(transformed, total_count=len(filtered))

    freshness_info = get_freshness_info(raw_data)
    total = len(filtered)

    metadata = Metadata(
        total_results=total,
        returned_results=len(optimized),
        data_freshness=freshness_info["data_freshness"],
        staleness_indicator=freshness_info["staleness_indicator"],
        data_type=data_type,
        voice_context=f"Showing {len(optimized)} of {total} results",
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=has_next,
    )

    return DataResponse(data=optimized, metadata=metadata)
