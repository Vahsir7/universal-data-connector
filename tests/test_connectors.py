from app.connectors.analytics_connector import AnalyticsConnector
from app.connectors.crm_connector import CRMConnector
from app.connectors.support_connector import SupportConnector


def test_crm_connector_fetch_returns_list():
    rows = CRMConnector().fetch()
    assert isinstance(rows, list)
    assert len(rows) > 0
    assert "customer_id" in rows[0]


def test_support_connector_fetch_returns_list():
    rows = SupportConnector().fetch()
    assert isinstance(rows, list)
    assert len(rows) > 0
    assert "ticket_id" in rows[0]


def test_analytics_connector_fetch_returns_list():
    rows = AnalyticsConnector().fetch()
    assert isinstance(rows, list)
    assert len(rows) > 0
    assert "metric" in rows[0]
