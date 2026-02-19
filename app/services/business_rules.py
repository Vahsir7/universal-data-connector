from datetime import datetime
from math import ceil
from typing import Any, Dict, List, Optional, Tuple

from app.config import settings


def apply_voice_limits(data: List[Dict[str, Any]], limit: int = settings.MAX_RESULTS) -> List[Dict[str, Any]]:
    effective_limit = min(limit, settings.MAX_RESULTS)
    return data[:effective_limit]


def _parse_iso(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    text = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        try:
            return datetime.fromisoformat(f"{text}T00:00:00")
        except ValueError:
            return None


def _record_dt(row: Dict[str, Any]) -> Optional[datetime]:
    raw = row.get("created_at") or row.get("date")
    if raw is None:
        return None
    return _parse_iso(str(raw))


def apply_business_filters(
    data: List[Dict[str, Any]],
    ticket_id: Optional[int] = None,
    customer_id: Optional[int] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    metric: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> List[Dict[str, Any]]:
    out = data

    if ticket_id is not None:
        out = [r for r in out if int(r.get("ticket_id", -1)) == ticket_id]

    if customer_id is not None:
        out = [r for r in out if int(r.get("customer_id", -1)) == customer_id]

    if status is not None:
        out = [r for r in out if str(r.get("status", "")).lower() == status.lower()]

    if priority is not None:
        out = [r for r in out if str(r.get("priority", "")).lower() == priority.lower()]

    if metric is not None:
        out = [r for r in out if str(r.get("metric", "")).lower() == metric.lower()]

    start_dt = _parse_iso(start_date)
    end_dt = _parse_iso(end_date)

    if start_dt or end_dt:
        ranged: List[Dict[str, Any]] = []
        for row in out:
            dt = _record_dt(row)
            if dt is None:
                continue
            if start_dt and dt < start_dt:
                continue
            if end_dt and dt > end_dt:
                continue
            ranged.append(row)
        out = ranged

    return out


def prioritize_for_voice(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(data, key=lambda r: _record_dt(r) or datetime.min, reverse=True)


def paginate_data(data: List[Dict[str, Any]], page: int, page_size: int) -> Tuple[List[Dict[str, Any]], int, bool]:
    safe_page = max(1, page)
    safe_size = max(1, page_size)

    total = len(data)
    total_pages = ceil(total / safe_size) if total > 0 else 1

    start = (safe_page - 1) * safe_size
    end = start + safe_size
    chunk = data[start:end]

    has_next = safe_page < total_pages
    return chunk, total_pages, has_next