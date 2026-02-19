from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.config import settings
from app.main import app
from app.services.auth import api_key_service


client = TestClient(app)


def test_ui_endpoint_available():
    response = client.get("/ui")
    assert response.status_code == 200
    assert "Universal Data Connector Dashboard" in response.text

    alt_response = client.get("/home")
    assert alt_response.status_code == 200

    llm_response = client.get("/home/llm")
    assert llm_response.status_code == 200

    data_response = client.get("/home/data")
    assert data_response.status_code == 200

    api_response = client.get("/home/api")
    assert api_response.status_code == 200


def test_api_key_management_lifecycle():
    api_key_service.reset_for_tests()

    create_resp = client.post(
        "/auth/api-keys",
        headers={"X-Admin-Key": "dev-admin-key"},
        json={"name": "integration-test-key"},
    )
    assert create_resp.status_code == 200
    created = create_resp.json()
    assert created["api_key"].startswith("udc_")

    list_resp = client.get("/auth/api-keys", headers={"X-Admin-Key": "dev-admin-key"})
    assert list_resp.status_code == 200
    listed = list_resp.json()
    assert len(listed) == 1
    key_id = listed[0]["key_id"]

    revoke_resp = client.post(f"/auth/api-keys/{key_id}/revoke", headers={"X-Admin-Key": "dev-admin-key"})
    assert revoke_resp.status_code == 200


def test_data_requires_api_key_when_auth_enabled(monkeypatch):
    monkeypatch.setattr(settings, "AUTH_ENABLED", True)
    api_key_service.reset_for_tests()

    created = api_key_service.create_api_key("runtime-key")
    api_key = created["api_key"]

    unauthorized = client.get("/data/crm?page=1&page_size=1")
    assert unauthorized.status_code == 401

    authorized = client.get("/data/crm?page=1&page_size=1", headers={"X-API-Key": api_key})
    assert authorized.status_code == 200

    monkeypatch.setattr(settings, "AUTH_ENABLED", False)


def test_webhook_secret_and_event_listing(monkeypatch):
    monkeypatch.setattr(settings, "WEBHOOK_SHARED_SECRET", SecretStr("webhook-secret"))

    denied = client.post("/webhooks/events", json={"source": "crm", "event_type": "update", "payload": {}})
    assert denied.status_code == 401

    accepted = client.post(
        "/webhooks/events",
        headers={"X-Webhook-Secret": "webhook-secret"},
        json={"source": "crm", "event_type": "update", "payload": {"id": 1}},
    )
    assert accepted.status_code == 200

    events = client.get("/webhooks/events", headers={"X-Admin-Key": "dev-admin-key"})
    assert events.status_code == 200
    assert isinstance(events.json(), list)


def test_export_csv_and_xlsx_endpoints():
    csv_resp = client.get("/export/crm?export_format=csv")
    assert csv_resp.status_code == 200
    assert csv_resp.headers["content-type"].startswith("text/csv")

    xlsx_resp = client.get("/export/analytics?export_format=xlsx")
    assert xlsx_resp.status_code == 200
    assert xlsx_resp.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
