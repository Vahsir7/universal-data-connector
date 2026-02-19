from fastapi.testclient import TestClient

from app.main import app
from app.models.assistant import AssistantQueryResponse, AssistantToolCall, LLMProvider
import app.routers.assistant as assistant_router
from app.services.llm_service import _recover_tool_call_from_text_response

client = TestClient(app)


def test_assistant_query_success_with_monkeypatched_runner(monkeypatch):
    def _fake_runner(_payload):
        return AssistantQueryResponse(
            provider=LLMProvider.openai,
            model="gpt-test",
            answer="Here is your summary.",
            tool_calls=[
                AssistantToolCall(
                    tool_name="fetch_data",
                    arguments={"source": "crm", "page": 1, "page_size": 5},
                    result={"data": [], "metadata": {"total_results": 0}},
                )
            ],
            usage={"prompt_tokens": 10, "completion_tokens": 20},
        )

    monkeypatch.setattr(assistant_router, "run_assistant_query", _fake_runner)

    response = client.post(
        "/assistant/query",
        json={
            "provider": "openai",
            "user_query": "show me recent crm records",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == "openai"
    assert payload["model"] == "gpt-test"
    assert payload["tool_calls"][0]["tool_name"] == "fetch_data"


def test_assistant_query_returns_400_on_configuration_error(monkeypatch):
    def _raise_config_error(_payload):
        raise ValueError("OPENAI_API_KEY is not configured")

    monkeypatch.setattr(assistant_router, "run_assistant_query", _raise_config_error)

    response = client.post(
        "/assistant/query",
        json={
            "provider": "openai",
            "user_query": "show me support ticket summary",
        },
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "ASSISTANT_CONFIG_ERROR"


def test_assistant_openapi_path_exists():
    schema = client.get("/openapi.json").json()
    assert "/assistant/query" in schema["paths"]


def test_assistant_ticket_lookup_routes_to_support_without_llm_calls():
    response = client.post(
        "/assistant/query",
        json={
            "provider": "gemini",
            "user_query": "Show me ticket 48",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == "gemini"
    assert payload["tool_calls"][0]["arguments"]["source"] == "support"
    assert payload["tool_calls"][0]["arguments"]["ticket_id"] == 48


def test_assistant_customer_lookup_routes_to_crm_without_llm_calls():
    response = client.post(
        "/assistant/query",
        json={
            "provider": "gemini",
            "user_query": "Who is customer 2",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == "gemini"
    assert payload["tool_calls"][0]["arguments"]["source"] == "crm"
    assert payload["tool_calls"][0]["arguments"]["customer_id"] == 2


def test_assistant_total_active_users_uses_deterministic_fallback():
    response = client.post(
        "/assistant/query",
        json={
            "provider": "gemini",
            "user_query": "Total active users throughout the data",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == "gemini"
    assert "Total active users:" in payload["answer"]
    assert payload["tool_calls"][0]["arguments"]["source"] == "crm"
    assert payload["tool_calls"][0]["arguments"]["status"] == "active"


def test_recover_tool_call_from_text_response_executes_fetch_data():
    response = _recover_tool_call_from_text_response(
        provider=LLMProvider.gemini,
        model_name="gemini-2.0-flash",
        answer='```tool_code\nfetch_data(data_source="analytics", query="total active users")\n```',
        usage={"total_tokens": 1},
    )

    assert response is not None
    assert response.tool_calls[0].arguments["source"] == "crm"
    assert response.tool_calls[0].arguments["status"] == "active"
    assert "Total active users:" in response.answer


def test_assistant_daily_users_for_date_uses_deterministic_fallback():
    response = client.post(
        "/assistant/query",
        json={
            "provider": "gemini",
            "user_query": "Total daily users for 2026-02-08",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == "gemini"
    assert "Total daily users on 2026-02-08:" in payload["answer"]
    assert payload["tool_calls"][0]["arguments"]["source"] == "analytics"
    assert payload["tool_calls"][0]["arguments"]["metric"] == "daily_active_users"
    assert payload["tool_calls"][0]["arguments"]["start_date"] == "2026-02-08"


def test_recover_tool_call_from_text_response_handles_daily_users_by_date():
    response = _recover_tool_call_from_text_response(
        provider=LLMProvider.gemini,
        model_name="gemini-2.0-flash",
        answer='```tool_code\nfetch_data(data_source="analytics", query="total daily users for 2026-02-08")\n```',
        usage={"total_tokens": 1},
    )

    assert response is not None
    assert response.tool_calls[0].arguments["source"] == "analytics"
    assert response.tool_calls[0].arguments["metric"] == "daily_active_users"
    assert response.tool_calls[0].arguments["start_date"] == "2026-02-08"
    assert "Total daily users on 2026-02-08:" in response.answer
