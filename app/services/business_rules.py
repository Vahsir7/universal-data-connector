"""Business rules engine for voice-optimized data filtering.

Implements four key rules from the assignment:
  1. apply_voice_limits  — cap results to MAX_RESULTS for voice brevity
  2. apply_business_filters — filter by status, priority, date range, etc.
  3. prioritize_for_voice — sort newest-first so the most relevant data is returned
  4. paginate_data — slice the full result set into pages
"""

from datetime import datetime
from math import ceil
from typing import Any, Dict, List, Optional, Tuple

from app.config import settings


def apply_voice_limits(data: List[Dict[str, Any]], limit: int = settings.MAX_RESULTS) -> List[Dict[str, Any]]:
    """Enforce the hard cap on voice results so responses stay concise."""
    effective_limit = min(limit, settings.MAX_RESULTS)
    return data[:effective_limit]


def _parse_iso(value: Optional[str]) -> Optional[datetime]:
    """Parse an ISO-8601 string into a datetime, tolerating 'Z' and date-only formats."""
    if not value:
        return None
    # Replace trailing 'Z' with the explicit UTC offset that fromisoformat expects
    text = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        # Fall back to treating the value as a date-only string
        try:
            return datetime.fromisoformat(f"{text}T00:00:00")
        except ValueError:
            return None


def _record_dt(row: Dict[str, Any]) -> Optional[datetime]:
    """Extract the best available timestamp from a record (created_at or date)."""
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
    """Progressively narrow the dataset using caller-supplied filter criteria.

    Each non-None parameter is applied as an AND filter.  Date filters
    use the record's created_at or date field.
    """
    out = data

    # Exact-match filters — each one further narrows the result set
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

    # Date range filter — drop records outside [start_date, end_date]
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
    """Sort records newest-first so the most relevant items appear first in voice responses."""
    return sorted(data, key=lambda r: _record_dt(r) or datetime.min, reverse=True)


def paginate_data(data: List[Dict[str, Any]], page: int, page_size: int) -> Tuple[List[Dict[str, Any]], int, bool]:
    """Return a single page of results plus pagination metadata.

    Returns:
        (page_rows, total_pages, has_next)
    """
    safe_page = max(1, page)
    safe_size = max(1, page_size)

    total = len(data)
    total_pages = ceil(total / safe_size) if total > 0 else 1

    start = (safe_page - 1) * safe_size
    end = start + safe_size
    chunk = data[start:end]

    has_next = safe_page < total_pages
    return chunk, total_pages, has_next