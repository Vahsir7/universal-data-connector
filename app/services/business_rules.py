from typing import Dict, List

from app.config import settings

def apply_voice_limits(data: List[Dict], limit: int = settings.MAX_RESULTS) -> List[Dict]:
    effective_limit = min(limit, settings.MAX_RESULTS)
    return data[:effective_limit]