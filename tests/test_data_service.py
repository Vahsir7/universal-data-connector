from app.models.common import DataResponse
from app.services.data_service import DataSource, get_unified_data


def test_get_unified_data_returns_typed_response():
    response = get_unified_data(source=DataSource.crm, page=1, page_size=5)

    assert isinstance(response, DataResponse)
    assert response.metadata.page == 1
    assert response.metadata.page_size == 5
    assert response.metadata.total_results >= response.metadata.returned_results


def test_get_unified_data_applies_filters_for_support():
    response = get_unified_data(
        source=DataSource.support,
        page=1,
        page_size=10,
        status="open",
    )

    for item in response.data:
        if "status" in item:
            assert str(item["status"]).lower() == "open"
