
from typing import Any, Dict, List

from app.config import settings


def summarize_if_large(data: List[Dict[str, Any]], total_count: int | None = None) -> List[Dict[str, Any]]:
    returned_count = len(data)
    count = total_count if total_count is not None else returned_count
    if returned_count > settings.VOICE_SUMMARY_THRESHOLD:
        return [{
            "summary": f"{count} records found. Returning a concise voice summary.",
            "preview_count": returned_count,
        }]
    return data
