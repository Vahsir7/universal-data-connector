from fastapi.testclient import TestClient

from app.main import app

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
    assert source_schema["$ref"].endswith("DataSource")

    responses = data_path["responses"]
    assert "200" in responses
    assert "422" in responses
    assert "503" in responses
