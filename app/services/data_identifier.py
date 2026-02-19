"""Data type detection and transformation service.

Identifies whether a dataset is tabular, time-series, or hierarchical,
then applies the appropriate transformation.  Also computes freshness
indicators so the LLM (and the user) know how recent the data is.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _parse_datetime(value: Any) -> Optional[datetime]:
    """Best-effort ISO-8601 parsing, normalizing to UTC."""
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    # Python's fromisoformat() doesn't accept 'Z'; replace with explicit offset
    normalized = text.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None

    # Ensure every returned datetime carries a UTC timezone
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _is_hierarchical_record(record: Dict[str, Any]) -> bool:
    """A record is hierarchical if any value is a nested dict or list."""
    return any(isinstance(value, (dict, list)) for value in record.values())


def identify_data_type(data: List[Dict[str, Any]]) -> str:
    """Inspect the first record to classify the dataset shape.

    Returns one of: 'empty', 'hierarchical', 'time_series', 'tabular', 'unknown'.
    """
    if not data:
        return "empty"

    first = data[0]

    if _is_hierarchical_record(first):
        return "hierarchical"

    # Analytics records always have a 'date' field
    if "date" in first:
        return "time_series"

    # CRM/support records have identifying ID fields
    if "customer_id" in first or "ticket_id" in first:
        return "tabular"

    return "unknown"


def _flatten_hierarchical_record(row: Dict[str, Any]) -> Dict[str, Any]:
    """Convert nested dicts into dot-notation keys (e.g. metrics.cpu -> 'metrics.cpu').

    Only one level of nesting is flattened —  deeper structures would need
    recursive handling.  Lists are left as-is.
    """
    flattened: Dict[str, Any] = {}
    for key, value in row.items():
        if isinstance(value, dict):
            for nested_key, nested_value in value.items():
                flattened[f"{key}.{nested_key}"] = nested_value
            continue
        flattened[key] = value
    return flattened


def apply_data_transformation(data: List[Dict[str, Any]], data_type: str) -> List[Dict[str, Any]]:
    """Apply type-specific transformations.

    - time_series: sort newest-first so the LLM sees the most recent data points
    - hierarchical: flatten nested dicts for a tabular-friendly shape
    - everything else: pass through unchanged
    """
    if not data:
        return data

    if data_type == "time_series":
        return sorted(
            data,
            key=lambda row: _parse_datetime(row.get("date")) or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )

    if data_type == "hierarchical":
        return [_flatten_hierarchical_record(row) for row in data]

    return data


def get_freshness_info(data: List[Dict[str, Any]]) -> Dict[str, str]:
    """Compute how fresh the data is based on the newest timestamp found.

    Staleness tiers:
      - fresh:      ≤ 24 hours old
      - stale:      ≤ 7 days old
      - very_stale: > 7 days old
      - unknown:    no parseable timestamps in the data
    """
    if not data:
        return {
            "data_freshness": "No data available",
            "staleness_indicator": "unknown",
        }

    # Check common timestamp field names in priority order
    timestamp_fields = ("updated_at", "created_at", "date", "timestamp")
    timestamps: List[datetime] = []

    for row in data:
        for field in timestamp_fields:
            parsed = _parse_datetime(row.get(field))
            if parsed is not None:
                timestamps.append(parsed)
                break

    if not timestamps:
        return {
            "data_freshness": "Timestamp unavailable",
            "staleness_indicator": "unknown",
        }

    latest = max(timestamps)
    now = datetime.now(timezone.utc)
    age_hours = (now - latest).total_seconds() / 3600

    if age_hours <= 24:
        staleness = "fresh"
    elif age_hours <= 7 * 24:
        staleness = "stale"
    else:
        staleness = "very_stale"

    freshness = f"Data as of {latest.isoformat()}"

    return {
        "data_freshness": freshness,
        "staleness_indicator": staleness,
    }
