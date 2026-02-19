from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class Metadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_results: int = Field(..., description="Total records after filters")
    returned_results: int = Field(..., description="Records returned in this response")
    data_freshness: str = Field(..., description="Freshness indicator")
    staleness_indicator: Optional[str] = Field(default=None, description="fresh/stale/very_stale/unknown")
    data_type: Optional[str] = Field(default=None, description="Detected data type")
    voice_context: Optional[str] = Field(default=None, description="Voice-friendly context summary")
    page: int = Field(default=1, ge=1, description="Current page number")
    page_size: int = Field(default=10, ge=1, description="Records per page")
    total_pages: int = Field(default=1, ge=1, description="Total number of pages")
    has_next: bool = Field(default=False, description="Whether another page exists")


class DataResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: List[Any]
    metadata: Metadata


class ErrorBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    details: Optional[Any] = None


class ErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    error: ErrorBody