"""Unified data service — single entry point for all data retrieval.

This is the heart of the connector: it picks the right data source,
applies filtering and business rules, paginates, detects data types,
and builds the final response with voice-friendly metadata.

Pipeline:
  1. Fetch raw data from the correct connector
  2. Apply query filters (status, priority, date range, etc.)
  3. Sort newest-first for voice relevance
  4. Paginate
  5. Cap results to voice-safe limits
  6. Detect data type and apply transformations
  7. Summarize if too large for voice
  8. Attach freshness & context metadata
"""

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
    """Supported data source identifiers (used in URL path and tool args)."""
    crm = "crm"
    support = "support"
    analytics = "analytics"


# Maps each DataSource to its concrete connector class
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
    """Fetch, filter, paginate, and return data with voice-optimized metadata."""

    # Step 1: Load raw data from the appropriate connector
    connector_cls = CONNECTOR_MAP[source]
    raw_data = connector_cls().fetch()

    # Step 2: Apply user-supplied filters (status, priority, date range, etc.)
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

    # Step 3–5: Sort newest-first, paginate, then cap to voice-safe limit
    prioritized = prioritize_for_voice(filtered)
    paged, total_pages, has_next = paginate_data(prioritized, page=page, page_size=page_size)
    limited = apply_voice_limits(paged, limit=page_size)

    # Step 6: Detect data shape and apply type-specific transformations
    data_type = identify_data_type(raw_data)
    transformed = apply_data_transformation(limited, data_type)

    # Step 7: If result set is still too large for voice, return a summary instead
    optimized = summarize_if_large(transformed, total_count=len(filtered))

    # Step 8: Build metadata with freshness indicators and voice context
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
