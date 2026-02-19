
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _parse_datetime(value: Any) -> Optional[datetime]:
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    normalized = text.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _is_hierarchical_record(record: Dict[str, Any]) -> bool:
    return any(isinstance(value, (dict, list)) for value in record.values())


def identify_data_type(data: List[Dict[str, Any]]) -> str:
    if not data:
        return "empty"

    first = data[0]

    if _is_hierarchical_record(first):
        return "hierarchical"

    if "date" in first:
        return "time_series"

    if "customer_id" in first or "ticket_id" in first:
        return "tabular"

    return "unknown"


def _flatten_hierarchical_record(row: Dict[str, Any]) -> Dict[str, Any]:
    flattened: Dict[str, Any] = {}
    for key, value in row.items():
        if isinstance(value, dict):
            for nested_key, nested_value in value.items():
                flattened[f"{key}.{nested_key}"] = nested_value
            continue
        flattened[key] = value
    return flattened


def apply_data_transformation(data: List[Dict[str, Any]], data_type: str) -> List[Dict[str, Any]]:
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
    if not data:
        return {
            "data_freshness": "No data available",
            "staleness_indicator": "unknown",
        }

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
