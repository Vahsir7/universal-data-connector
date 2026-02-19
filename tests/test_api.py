from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
import app.routers.data as data_router

client = TestClient(app)


def test_health_live():
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "alive"


def test_health_ready_or_unavailable_shape():
    response = client.get("/health/ready")
    assert response.status_code in {200, 503}
    payload = response.json()
    assert "status" in payload


def test_health_summary_endpoint_exists():
    response = client.get("/health")
    assert response.status_code in {200, 503}


def test_data_endpoint_success_metadata_shape():
    response = client.get("/data/crm?page=1&page_size=5")
    assert response.status_code == 200
    payload = response.json()

    assert "data" in payload
    assert "metadata" in payload
    metadata = payload["metadata"]
    for key in [
        "total_results",
        "returned_results",
        "data_freshness",
        "staleness_indicator",
        "data_type",
        "page",
        "page_size",
        "total_pages",
        "has_next",
    ]:
        assert key in metadata


def test_data_unknown_source_returns_structured_error():
    response = client.get("/data/unknown")
    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] in {"VALIDATION_ERROR", "SOURCE_NOT_FOUND"}


def test_data_validation_error_for_invalid_page_size():
    response = client.get("/data/crm?page=1&page_size=999")
    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "VALIDATION_ERROR"


def test_filtering_support_open_status():
    response = client.get("/data/support?status=open&page=1&page_size=5")
    assert response.status_code == 200
    payload = response.json()
    assert "metadata" in payload


def test_openapi_contains_data_source_enum_and_response_models():
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()

    data_path = schema["paths"]["/data/{source}"]["get"]
    source_param = next(param for param in data_path["parameters"] if param["name"] == "source")
    source_schema = source_param["schema"]
    if "$ref" in source_schema:
        assert source_schema["$ref"].endswith("DataSource")
    elif "allOf" in source_schema and source_schema["allOf"]:
        assert source_schema["allOf"][0].get("$ref", "").endswith("DataSource")
    else:
        assert source_schema.get("type") == "string"
        assert set(source_schema.get("enum", [])) == {"crm", "support", "analytics"}

    responses = data_path["responses"]
    assert "200" in responses
    assert "422" in responses
    assert "503" in responses


def test_data_endpoint_streaming_returns_ndjson(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_STREAMING", True)
    monkeypatch.setattr(settings, "STREAM_MIN_TOTAL_RESULTS", 1)
    monkeypatch.setattr(settings, "STREAM_CHUNK_SIZE", 2)

    response = client.get("/data/analytics?stream=true&page=1&page_size=5")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/x-ndjson")
    body = response.text.strip().splitlines()
    assert len(body) >= 2


def test_data_endpoint_rate_limit_exceeded(monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_PER_SOURCE", 1)
    monkeypatch.setattr(settings, "RATE_LIMIT_WINDOW_SECONDS", 60)
    data_router.rate_limiter._buckets.clear()

    first = client.get("/data/crm?page=1&page_size=1")
    second = client.get("/data/crm?page=1&page_size=1")

    assert first.status_code == 200
    assert second.status_code == 429
    payload = second.json()
    assert payload["error"]["code"] == "RATE_LIMIT_EXCEEDED"
