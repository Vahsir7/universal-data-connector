"""Pydantic models for the /assistant LLM endpoint.

Covers the request/response schemas and the tool-call intermediate
representation used to show how the LLM interacted with data sources.
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    openai = "openai"
    anthropic = "anthropic"
    gemini = "gemini"


class AssistantResponseFormat(str, Enum):
    """Supported output formats for assistant query responses."""
    raw = "raw"
    pretty = "pretty"


class ToolFetchDataArgs(BaseModel):
    """Arguments the LLM passes when calling the fetch_data tool."""

    model_config = ConfigDict(extra="forbid")

    source: str = Field(..., description="Data source: crm, support, analytics")
    data_source: Optional[str] = None
    query: Optional[str] = None
    ticket_id: Optional[int] = Field(default=None, ge=1)
    customer_id: Optional[int] = Field(default=None, ge=1)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1, le=50)
    status: Optional[str] = None
    priority: Optional[str] = None
    metric: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class AssistantQueryRequest(BaseModel):
    """Incoming request body for /assistant/query."""

    model_config = ConfigDict(extra="forbid")

    provider: LLMProvider
    user_query: str = Field(..., min_length=1, description="Natural-language user query")
    model: Optional[str] = Field(default=None, description="Optional model override")
    temperature: float = Field(default=0.2, ge=0.0, le=1.0)
    api_key_id: Optional[str] = Field(default=None, description="Stored provider API key identifier")
    api_key: Optional[str] = Field(default=None, description="Manual provider API key for this request")
    response_format: AssistantResponseFormat = Field(default=AssistantResponseFormat.raw)


class AssistantToolCall(BaseModel):
    """Record of a single tool invocation made by the LLM."""

    model_config = ConfigDict(extra="forbid")

    tool_name: str
    arguments: Dict[str, Any]
    result: Dict[str, Any]


class AssistantQueryResponse(BaseModel):
    """Response body for /assistant/query."""

    model_config = ConfigDict(extra="forbid")

    provider: LLMProvider
    model: str
    answer: str
    tool_calls: List[AssistantToolCall] = Field(default_factory=list)
    usage: Optional[Dict[str, Any]] = None


class AssistantPrettySummary(BaseModel):
    """Compact summary for pretty-format assistant responses."""

    model_config = ConfigDict(extra="forbid")

    total_results: int = 0
    returned_results: int = 0
    page: int = 1
    total_pages: int = 1
    has_next: bool = False
    data_type: Optional[str] = None
    filters: Dict[str, Any] = Field(default_factory=dict)


class AssistantPrettyResponse(BaseModel):
    """Human-friendly response format for /assistant/query."""

    model_config = ConfigDict(extra="forbid")

    provider: LLMProvider
    model: str
    answer: str
    summary: AssistantPrettySummary
    usage: Dict[str, Any] = Field(default_factory=dict)
    top_records: List[Dict[str, Any]] = Field(default_factory=list)
    debug: Optional[Dict[str, Any]] = None
