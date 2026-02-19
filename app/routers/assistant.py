import logging

from fastapi import APIRouter, HTTPException

from app.models.assistant import AssistantQueryRequest, AssistantQueryResponse
from app.models.common import ErrorResponse
from app.services.llm_service import run_assistant_query


router = APIRouter(prefix="/assistant", tags=["Assistant"])
logger = logging.getLogger(__name__)


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
def assistant_query(payload: AssistantQueryRequest) -> AssistantQueryResponse:
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
