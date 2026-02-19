"""Voice-specific response optimization.

When a result set is too large for a voice conversation, this module
replaces the raw data with a short summary so the LLM can still give
a concise spoken answer instead of overwhelming the user.
"""

from typing import Any, Dict, List

from app.config import settings


def summarize_if_large(data: List[Dict[str, Any]], total_count: int | None = None) -> List[Dict[str, Any]]:
    """Return a single-item summary if the page exceeds the voice threshold.

    The VOICE_SUMMARY_THRESHOLD setting (default 10) controls when this
    kicks in.  Below the threshold the original data is returned as-is.
    """
    returned_count = len(data)
    count = total_count if total_count is not None else returned_count
    if returned_count > settings.VOICE_SUMMARY_THRESHOLD:
        return [{
            "summary": f"{count} records found. Returning a concise voice summary.",
            "preview_count": returned_count,
        }]
    return data
