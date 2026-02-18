from typing import Any, List, Optional

from pydantic import BaseModel


class Metadata(BaseModel):
    total_results: int
    returned_results: int
    data_freshness: str
    data_type: Optional[str] = None
    voice_context: Optional[str] = None
    page: int = 1
    page_size: int = 10
    total_pages: int = 1
    has_next: bool = False


class DataResponse(BaseModel):
    data: List[Any]
    metadata: Metadata