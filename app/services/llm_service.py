import json
import importlib
import re
from typing import Any, Dict, List, Tuple

from app.config import settings
from app.models.assistant import (
    AssistantQueryRequest,
    AssistantQueryResponse,
    AssistantToolCall,
    LLMProvider,
    ToolFetchDataArgs,
)
from app.models.common import DataResponse
from app.services.data_service import DataSource, get_unified_data


SYSTEM_PROMPT = (
    "You are a data assistant for a SaaS company. "
    "Use the fetch_data tool whenever user asks for CRM, support, or analytics information. "
    "Always prefer precise filtered retrieval and respond concisely for voice interactions."
)


def _secret_is_configured(secret: Any) -> bool:
    if secret is None:
        return False
    if hasattr(secret, "get_secret_value"):
        return bool(str(secret.get_secret_value()).strip())
    return bool(str(secret).strip())


def _tool_schema_openai() -> List[Dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": "fetch_data",
                "description": "Fetch filtered business data from crm/support/analytics.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "source": {"type": "string", "enum": ["crm", "support", "analytics"]},
                        "data_source": {"type": "string", "enum": ["crm", "support", "analytics"]},
                        "query": {"type": "string"},
                        "ticket_id": {"type": "integer", "minimum": 1},
                        "customer_id": {"type": "integer", "minimum": 1},
                        "page": {"type": "integer", "minimum": 1, "default": 1},
                        "page_size": {"type": "integer", "minimum": 1, "maximum": 50, "default": 10},
                        "status": {"type": "string"},
                        "priority": {"type": "string"},
                        "metric": {"type": "string"},
                        "start_date": {"type": "string"},
                        "end_date": {"type": "string"},
                    },
                    "required": ["source"],
                    "additionalProperties": False,
                },
            },
        }
    ]


def _tool_schema_anthropic() -> List[Dict[str, Any]]:
    return [
        {
            "name": "fetch_data",
            "description": "Fetch filtered business data from crm/support/analytics.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "source": {"type": "string", "enum": ["crm", "support", "analytics"]},
                    "data_source": {"type": "string", "enum": ["crm", "support", "analytics"]},
                    "query": {"type": "string"},
                    "ticket_id": {"type": "integer", "minimum": 1},
                    "customer_id": {"type": "integer", "minimum": 1},
                    "page": {"type": "integer", "minimum": 1, "default": 1},
                    "page_size": {"type": "integer", "minimum": 1, "maximum": 50, "default": 10},
                    "status": {"type": "string"},
                    "priority": {"type": "string"},
                    "metric": {"type": "string"},
                    "start_date": {"type": "string"},
                    "end_date": {"type": "string"},
                },
                "required": ["source"],
                "additionalProperties": False,
            },
        }
    ]


def _normalize_tool_arguments(arguments: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(arguments)

    if not normalized.get("source") and normalized.get("data_source"):
        normalized["source"] = normalized["data_source"]

    free_text_query = str(normalized.get("query", "")).lower()

    if "active users" in free_text_query or "active customers" in free_text_query:
        normalized["source"] = "crm"
        normalized.setdefault("status", "active")
        normalized.setdefault("page", 1)
        normalized.setdefault("page_size", 1)

    date_in_query = _extract_iso_date(free_text_query)
    if date_in_query and any(token in free_text_query for token in ["daily users", "daily active users", "dau"]):
        normalized["source"] = "analytics"
        normalized.setdefault("metric", "daily_active_users")
        normalized.setdefault("start_date", date_in_query)
        normalized.setdefault("end_date", date_in_query)
        normalized.setdefault("page", 1)
        normalized.setdefault("page_size", 1)

    if not normalized.get("ticket_id"):
        ticket_match = re.search(r"\bticket\s*#?\s*(\d+)\b", free_text_query, flags=re.IGNORECASE)
        if ticket_match:
            normalized["ticket_id"] = int(ticket_match.group(1))
            normalized.setdefault("source", "support")
            normalized.setdefault("page", 1)
            normalized.setdefault("page_size", 1)

    if not normalized.get("customer_id"):
        customer_match = re.search(r"\bcustomer\s*#?\s*(\d+)\b", free_text_query, flags=re.IGNORECASE)
        if customer_match:
            normalized["customer_id"] = int(customer_match.group(1))
            normalized.setdefault("source", "crm")
            normalized.setdefault("page", 1)
            normalized.setdefault("page_size", 1)

    if not normalized.get("source"):
        raise ValueError("fetch_data requires source (crm/support/analytics)")

    return normalized


def _execute_fetch_data(arguments: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    parsed_args = ToolFetchDataArgs.model_validate(_normalize_tool_arguments(arguments))
    source = DataSource(parsed_args.source)

    result: DataResponse = get_unified_data(
        source=source,
        ticket_id=parsed_args.ticket_id,
        customer_id=parsed_args.customer_id,
        page=parsed_args.page,
        page_size=parsed_args.page_size,
        status=parsed_args.status,
        priority=parsed_args.priority,
        metric=parsed_args.metric,
        start_date=parsed_args.start_date,
        end_date=parsed_args.end_date,
    )

    return parsed_args.model_dump(exclude_none=True), result.model_dump()


def _build_usage_dict(usage: Any) -> Dict[str, Any]:
    if usage is None:
        return {}
    if hasattr(usage, "model_dump"):
        return usage.model_dump()
    if isinstance(usage, dict):
        return usage
    return {}


def _detect_ticket_id_query(user_query: str) -> int | None:
    match = re.search(r"\bticket\s*#?\s*(\d+)\b", user_query, flags=re.IGNORECASE)
    if not match:
        return None
    return int(match.group(1))


def _detect_customer_id_query(user_query: str) -> int | None:
    match = re.search(r"\bcustomer\s*#?\s*(\d+)\b", user_query, flags=re.IGNORECASE)
    if not match:
        return None
    return int(match.group(1))


def _extract_iso_date(user_query: str) -> str | None:
    match = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", user_query)
    if not match:
        return None
    return match.group(1)


def _is_total_active_users_query(user_query: str) -> bool:
    text = user_query.lower()
    has_total = any(token in text for token in ["total", "count", "how many"])
    has_active = any(token in text for token in ["active user", "active users", "active customer", "active customers"])
    return has_total and has_active


def _detect_daily_users_date_query(user_query: str) -> str | None:
    text = user_query.lower()
    if not any(token in text for token in ["daily users", "daily active users", "dau"]):
        return None
    return _extract_iso_date(text)


def _default_model_for_provider(provider: LLMProvider) -> str:
    if provider == LLMProvider.openai:
        return settings.OPENAI_MODEL
    if provider == LLMProvider.anthropic:
        return settings.ANTHROPIC_MODEL
    if provider == LLMProvider.gemini:
        return settings.GEMINI_MODEL
    return "unknown"


def _run_ticket_lookup_fallback(request: AssistantQueryRequest, ticket_id: int) -> AssistantQueryResponse:
    result: DataResponse = get_unified_data(
        source=DataSource.support,
        ticket_id=ticket_id,
        page=1,
        page_size=1,
    )

    model_name = request.model or _default_model_for_provider(request.provider)

    if result.data:
        ticket = result.data[0]
        answer = (
            f"Ticket {ticket_id} is {ticket.get('status', 'unknown')} with "
            f"{ticket.get('priority', 'unknown')} priority, created at {ticket.get('created_at', 'unknown')}."
        )
    else:
        answer = f"Ticket {ticket_id} was not found in support data."

    return AssistantQueryResponse(
        provider=request.provider,
        model=model_name,
        answer=answer,
        tool_calls=[
            AssistantToolCall(
                tool_name="fetch_data",
                arguments={"source": "support", "ticket_id": ticket_id, "page": 1, "page_size": 1},
                result=result.model_dump(),
            )
        ],
        usage={},
    )


def _run_customer_lookup_fallback(request: AssistantQueryRequest, customer_id: int) -> AssistantQueryResponse:
    result: DataResponse = get_unified_data(
        source=DataSource.crm,
        customer_id=customer_id,
        page=1,
        page_size=1,
    )

    model_name = request.model or _default_model_for_provider(request.provider)

    if result.data:
        customer = result.data[0]
        answer = (
            f"Customer {customer_id} is {customer.get('name', 'unknown')} "
            f"({customer.get('email', 'unknown')}) with status {customer.get('status', 'unknown')}."
        )
    else:
        answer = f"Customer {customer_id} was not found in CRM data."

    return AssistantQueryResponse(
        provider=request.provider,
        model=model_name,
        answer=answer,
        tool_calls=[
            AssistantToolCall(
                tool_name="fetch_data",
                arguments={"source": "crm", "customer_id": customer_id, "page": 1, "page_size": 1},
                result=result.model_dump(),
            )
        ],
        usage={},
    )


def _run_total_active_users_fallback(request: AssistantQueryRequest) -> AssistantQueryResponse:
    active_result = get_unified_data(
        source=DataSource.crm,
        status="active",
        page=1,
        page_size=1,
    )
    total_result = get_unified_data(
        source=DataSource.crm,
        page=1,
        page_size=1,
    )

    active_count = active_result.metadata.total_results
    total_count = total_result.metadata.total_results
    model_name = request.model or _default_model_for_provider(request.provider)

    return AssistantQueryResponse(
        provider=request.provider,
        model=model_name,
        answer=f"Total active users: {active_count} out of {total_count} customers.",
        tool_calls=[
            AssistantToolCall(
                tool_name="fetch_data",
                arguments={"source": "crm", "status": "active", "page": 1, "page_size": 1},
                result=active_result.model_dump(),
            )
        ],
        usage={},
    )


def _run_daily_users_for_date_fallback(request: AssistantQueryRequest, target_date: str) -> AssistantQueryResponse:
    result = get_unified_data(
        source=DataSource.analytics,
        metric="daily_active_users",
        start_date=target_date,
        end_date=target_date,
        page=1,
        page_size=1,
    )

    model_name = request.model or _default_model_for_provider(request.provider)

    if result.data:
        day_value = result.data[0].get("value", "unknown")
        answer = f"Total daily users on {target_date}: {day_value}."
    else:
        answer = f"No daily_active_users data found for {target_date}."

    return AssistantQueryResponse(
        provider=request.provider,
        model=model_name,
        answer=answer,
        tool_calls=[
            AssistantToolCall(
                tool_name="fetch_data",
                arguments={
                    "source": "analytics",
                    "metric": "daily_active_users",
                    "start_date": target_date,
                    "end_date": target_date,
                    "page": 1,
                    "page_size": 1,
                },
                result=result.model_dump(),
            )
        ],
        usage={},
    )


def _build_final_answer_from_tool_result(normalized_args: Dict[str, Any], result_payload: Dict[str, Any]) -> str:
    meta = result_payload.get("metadata", {})
    data = result_payload.get("data", [])

    if normalized_args.get("source") == "analytics" and normalized_args.get("metric") == "daily_active_users":
        start_date = normalized_args.get("start_date")
        end_date = normalized_args.get("end_date")
        if start_date and start_date == end_date:
            if data:
                return f"Total daily users on {start_date}: {data[0].get('value', 'unknown')}."
            return f"No daily_active_users data found for {start_date}."

    if normalized_args.get("status") == "active" and normalized_args.get("source") == "crm":
        return f"Total active users: {meta.get('total_results', 0)}."

    return (
        f"Fetched {meta.get('returned_results', 0)} of {meta.get('total_results', 0)} "
        f"records from {normalized_args.get('source', 'unknown')}."
    )


def _extract_tool_args_from_text(answer: str) -> Dict[str, Any] | None:
    match = re.search(r"fetch_data\((.*?)\)", answer, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return None

    raw_args = match.group(1)
    items = re.findall(r"(\w+)\s*=\s*(\".*?\"|'.*?'|\d+)", raw_args)
    if not items:
        return None

    parsed: Dict[str, Any] = {}
    for key, value in items:
        if value.isdigit():
            parsed[key] = int(value)
        else:
            parsed[key] = value.strip("\"'")
    return parsed


def _recover_tool_call_from_text_response(
    provider: LLMProvider,
    model_name: str,
    answer: str,
    usage: Dict[str, Any],
) -> AssistantQueryResponse | None:
    parsed_args = _extract_tool_args_from_text(answer)
    if not parsed_args:
        return None

    normalized_args, result_payload = _execute_fetch_data(parsed_args)
    final_answer = _build_final_answer_from_tool_result(normalized_args, result_payload)

    return AssistantQueryResponse(
        provider=provider,
        model=model_name,
        answer=final_answer,
        tool_calls=[
            AssistantToolCall(
                tool_name="fetch_data",
                arguments=normalized_args,
                result=result_payload,
            )
        ],
        usage=usage,
    )


def _run_openai(request: AssistantQueryRequest) -> AssistantQueryResponse:
    if not _secret_is_configured(settings.OPENAI_API_KEY):
        raise ValueError("OPENAI_API_KEY is not configured")

    openai_module = importlib.import_module("openai")
    client = openai_module.OpenAI(api_key=settings.OPENAI_API_KEY.get_secret_value())
    model_name = request.model or settings.OPENAI_MODEL

    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": request.user_query},
    ]

    first = client.chat.completions.create(
        model=model_name,
        messages=messages,
        tools=_tool_schema_openai(),
        tool_choice="auto",
        temperature=request.temperature,
    )

    message = first.choices[0].message
    tool_calls = message.tool_calls or []
    captured_calls: List[AssistantToolCall] = []

    if tool_calls:
        messages.append(
            {
                "role": "assistant",
                "content": message.content or "",
                "tool_calls": [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {
                            "name": call.function.name,
                            "arguments": call.function.arguments,
                        },
                    }
                    for call in tool_calls
                ],
            }
        )

        for call in tool_calls:
            if call.function.name != "fetch_data":
                continue

            tool_args = json.loads(call.function.arguments or "{}")
            parsed_args, result_payload = _execute_fetch_data(tool_args)

            captured_calls.append(
                AssistantToolCall(
                    tool_name="fetch_data",
                    arguments=parsed_args,
                    result=result_payload,
                )
            )

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "name": "fetch_data",
                    "content": json.dumps(result_payload),
                }
            )

    second = client.chat.completions.create(
        model=model_name,
        messages=messages,
        temperature=request.temperature,
    )

    answer = second.choices[0].message.content or ""
    usage = _build_usage_dict(second.usage)

    if not captured_calls:
        recovered = _recover_tool_call_from_text_response(
            provider=LLMProvider.openai,
            model_name=model_name,
            answer=answer,
            usage=usage,
        )
        if recovered is not None:
            return recovered

    return AssistantQueryResponse(
        provider=LLMProvider.openai,
        model=model_name,
        answer=answer,
        tool_calls=captured_calls,
        usage=usage,
    )


def _run_gemini(request: AssistantQueryRequest) -> AssistantQueryResponse:
    if not _secret_is_configured(settings.GEMINI_API_KEY):
        raise ValueError("GEMINI_API_KEY is not configured")

    openai_module = importlib.import_module("openai")
    client = openai_module.OpenAI(
        api_key=settings.GEMINI_API_KEY.get_secret_value(),
        base_url=settings.GEMINI_BASE_URL,
    )
    model_name = request.model or settings.GEMINI_MODEL

    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": request.user_query},
    ]

    first = client.chat.completions.create(
        model=model_name,
        messages=messages,
        tools=_tool_schema_openai(),
        tool_choice="auto",
        temperature=request.temperature,
    )

    message = first.choices[0].message
    tool_calls = message.tool_calls or []
    captured_calls: List[AssistantToolCall] = []

    if tool_calls:
        messages.append(
            {
                "role": "assistant",
                "content": message.content or "",
                "tool_calls": [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {
                            "name": call.function.name,
                            "arguments": call.function.arguments,
                        },
                    }
                    for call in tool_calls
                ],
            }
        )

        for call in tool_calls:
            if call.function.name != "fetch_data":
                continue

            tool_args = json.loads(call.function.arguments or "{}")
            parsed_args, result_payload = _execute_fetch_data(tool_args)

            captured_calls.append(
                AssistantToolCall(
                    tool_name="fetch_data",
                    arguments=parsed_args,
                    result=result_payload,
                )
            )

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "name": "fetch_data",
                    "content": json.dumps(result_payload),
                }
            )

    second = client.chat.completions.create(
        model=model_name,
        messages=messages,
        temperature=request.temperature,
    )

    answer = second.choices[0].message.content or ""
    usage = _build_usage_dict(second.usage)

    if not captured_calls:
        recovered = _recover_tool_call_from_text_response(
            provider=LLMProvider.gemini,
            model_name=model_name,
            answer=answer,
            usage=usage,
        )
        if recovered is not None:
            return recovered

    return AssistantQueryResponse(
        provider=LLMProvider.gemini,
        model=model_name,
        answer=answer,
        tool_calls=captured_calls,
        usage=usage,
    )


def _anthropic_block_to_dict(block: Any) -> Dict[str, Any]:
    if block.type == "text":
        return {"type": "text", "text": block.text}
    if block.type == "tool_use":
        return {
            "type": "tool_use",
            "id": block.id,
            "name": block.name,
            "input": block.input,
        }
    return {"type": block.type}


def _extract_text_from_blocks(blocks: List[Any]) -> str:
    return "\n".join(block.text for block in blocks if getattr(block, "type", None) == "text")


def _run_anthropic(request: AssistantQueryRequest) -> AssistantQueryResponse:
    if not _secret_is_configured(settings.ANTHROPIC_API_KEY):
        raise ValueError("ANTHROPIC_API_KEY is not configured ")

    anthropic_module = importlib.import_module("anthropic")
    client = anthropic_module.Anthropic(api_key=settings.ANTHROPIC_API_KEY.get_secret_value())
    model_name = request.model or settings.ANTHROPIC_MODEL

    first = client.messages.create(
        model=model_name,
        max_tokens=settings.LLM_MAX_TOKENS,
        temperature=request.temperature,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": request.user_query}],
        tools=_tool_schema_anthropic(),
    )

    captured_calls: List[AssistantToolCall] = []
    tool_uses = [block for block in first.content if block.type == "tool_use"]

    if not tool_uses:
        first_answer = _extract_text_from_blocks(first.content)
        first_usage = _build_usage_dict(first.usage)
        recovered = _recover_tool_call_from_text_response(
            provider=LLMProvider.anthropic,
            model_name=model_name,
            answer=first_answer,
            usage=first_usage,
        )
        if recovered is not None:
            return recovered

        return AssistantQueryResponse(
            provider=LLMProvider.anthropic,
            model=model_name,
            answer=first_answer,
            tool_calls=[],
            usage=first_usage,
        )

    tool_results_blocks: List[Dict[str, Any]] = []

    for block in tool_uses:
        if block.name != "fetch_data":
            continue

        parsed_args, result_payload = _execute_fetch_data(block.input)
        captured_calls.append(
            AssistantToolCall(
                tool_name="fetch_data",
                arguments=parsed_args,
                result=result_payload,
            )
        )

        tool_results_blocks.append(
            {
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": json.dumps(result_payload),
            }
        )

    second = client.messages.create(
        model=model_name,
        max_tokens=settings.LLM_MAX_TOKENS,
        temperature=request.temperature,
        system=SYSTEM_PROMPT,
        tools=_tool_schema_anthropic(),
        messages=[
            {"role": "user", "content": request.user_query},
            {"role": "assistant", "content": [_anthropic_block_to_dict(block) for block in first.content]},
            {"role": "user", "content": tool_results_blocks},
        ],
    )

    return AssistantQueryResponse(
        provider=LLMProvider.anthropic,
        model=model_name,
        answer=_extract_text_from_blocks(second.content),
        tool_calls=captured_calls,
        usage=_build_usage_dict(second.usage),
    )


def run_assistant_query(request: AssistantQueryRequest) -> AssistantQueryResponse:
    daily_users_date = _detect_daily_users_date_query(request.user_query)
    if daily_users_date is not None:
        return _run_daily_users_for_date_fallback(request, daily_users_date)

    if _is_total_active_users_query(request.user_query):
        return _run_total_active_users_fallback(request)

    ticket_id = _detect_ticket_id_query(request.user_query)
    if ticket_id is not None:
        return _run_ticket_lookup_fallback(request, ticket_id)

    customer_id = _detect_customer_id_query(request.user_query)
    if customer_id is not None:
        return _run_customer_lookup_fallback(request, customer_id)

    if request.provider == LLMProvider.openai:
        return _run_openai(request)
    if request.provider == LLMProvider.anthropic:
        return _run_anthropic(request)
    if request.provider == LLMProvider.gemini:
        return _run_gemini(request)
    raise ValueError(f"Unsupported provider: {request.provider}")
