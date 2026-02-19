from datetime import datetime, timezone
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, Path, Query
from fastapi.responses import Response

from app.config import settings
from app.services.auth import require_api_key
from app.services.data_service import DataSource, get_unified_data
from app.services.exporter import build_export


router = APIRouter(prefix="/export", tags=["Export"])


def _collect_all_rows(
    source: DataSource,
    status: Optional[str],
    priority: Optional[str],
    metric: Optional[str],
    start_date: Optional[str],
    end_date: Optional[str],
) -> List[Dict[str, object]]:
    page = 1
    rows: List[Dict[str, object]] = []

    while True:
        response = get_unified_data(
            source=source,
            page=page,
            page_size=settings.MAX_PAGE_SIZE,
            status=status,
            priority=priority,
            metric=metric,
            start_date=start_date,
            end_date=end_date,
        )
        rows.extend(response.data)
        if not response.metadata.has_next:
            break
        page += 1

    return rows


@router.get("/{source}")
def export_data(
    source: DataSource = Path(..., description="Data source", examples=["crm"]),
    export_format: str = Query("csv", pattern="^(csv|xlsx)$"),
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    metric: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    _auth: None = Depends(require_api_key),
):
    rows = _collect_all_rows(
        source=source,
        status=status,
        priority=priority,
        metric=metric,
        start_date=start_date,
        end_date=end_date,
    )

    filename_base = f"{source.value}_export_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    filename, content_type, payload = build_export(filename_base=filename_base, export_format=export_format, rows=rows)

    return Response(
        content=payload,
        media_type=content_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
