from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class LLMProvider(str, Enum):
    openai = "openai"
    anthropic = "anthropic"
    gemini = "gemini"


class ToolFetchDataArgs(BaseModel):
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
    model_config = ConfigDict(extra="forbid")

    provider: LLMProvider
    user_query: str = Field(..., min_length=1, description="Natural-language user query")
    model: Optional[str] = Field(default=None, description="Optional model override")
    temperature: float = Field(default=0.2, ge=0.0, le=1.0)
    api_key_id: Optional[str] = Field(default=None, description="Stored provider API key identifier")
    api_key: Optional[str] = Field(default=None, description="Manual provider API key for this request")


class AssistantToolCall(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_name: str
    arguments: Dict[str, Any]
    result: Dict[str, Any]


class AssistantQueryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: LLMProvider
    model: str
    answer: str
    tool_calls: List[AssistantToolCall] = Field(default_factory=list)
    usage: Optional[Dict[str, Any]] = None
