"""Assistant router — LLM tool-calling endpoint and provider API key management.

POST /assistant/query accepts a natural-language question, forwards it
to the selected LLM provider (OpenAI / Anthropic / Gemini), lets the
model call the fetch_data tool, and returns data + a natural-language answer.

The /assistant/api-keys sub-endpoints let users store, list, and
revoke provider API keys so they don't have to pass them every request.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.models.assistant import AssistantQueryRequest, AssistantQueryResponse, LLMProvider
from app.models.common import ErrorResponse
from app.services.auth import require_api_key
from app.services.llm_service import run_assistant_query
from app.services.llm_api_keys import llm_api_key_service


router = APIRouter(prefix="/assistant", tags=["Assistant"])
logger = logging.getLogger(__name__)


# ---- Pydantic request/response schemas for the API-key sub-endpoints ----


class LlmApiKeyCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: LLMProvider
    name: str = Field(..., min_length=1, max_length=120)
    model: Optional[str] = Field(default=None, max_length=120)
    api_key: str = Field(..., min_length=1)


class LlmApiKeyInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key_id: str
    name: str
    provider: str
    model: str
    api_key_masked: str
    source: str
    revoked: bool
    created_at: str
    last_used_at: str


class LlmApiKeyCreateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key_id: str
    name: str
    provider: str
    model: str


@router.post(
    "/query",
    response_model=AssistantQueryResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Provider/API key/configuration error"},
        422: {"model": ErrorResponse, "description": "Validation error"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="Run GPT/Claude/Gemini tool-calling over connector data",
    description="Accepts natural-language query, lets selected LLM call fetch_data tool, applies business rules, and returns final answer.",
)
def assistant_query(
    payload: AssistantQueryRequest,
    _auth: None = Depends(require_api_key),
) -> AssistantQueryResponse:
    try:
        return run_assistant_query(payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "ASSISTANT_CONFIG_ERROR",
                "message": str(exc),
            },
        ) from exc
    except Exception as exc:
        logger.exception("Assistant query failed: %s", exc)
        raise HTTPException(
            status_code=500,
            detail={
                "code": "ASSISTANT_RUNTIME_ERROR",
                "message": "Assistant processing failed",
                "details": str(exc),
            },
        ) from exc


@router.get("/api-keys", response_model=List[LlmApiKeyInfo])
def list_llm_api_keys(provider: Optional[LLMProvider] = None) -> List[LlmApiKeyInfo]:
    records = llm_api_key_service.list_keys(provider=provider)
    return [LlmApiKeyInfo.model_validate(item) for item in records]


@router.post("/api-keys", response_model=LlmApiKeyCreateResponse)
def create_llm_api_key(payload: LlmApiKeyCreateRequest) -> LlmApiKeyCreateResponse:
    created = llm_api_key_service.create_key(
        provider=payload.provider,
        name=payload.name,
        key_value=payload.api_key,
        model=payload.model,
    )
    return LlmApiKeyCreateResponse.model_validate(created)


@router.post("/api-keys/{key_id}/revoke")
def revoke_llm_api_key(key_id: str):
    ok = llm_api_key_service.revoke_key(key_id)
    if not ok:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "LLM_API_KEY_NOT_FOUND",
                "message": f"No LLM API key found for id '{key_id}'",
            },
        )
    return {"status": "revoked", "key_id": key_id}
