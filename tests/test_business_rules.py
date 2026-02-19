from app.services.business_rules import (
    apply_business_filters,
    apply_voice_limits,
    paginate_data,
    prioritize_for_voice,
)


def test_apply_voice_limits_caps_results():
    rows = [{"id": index} for index in range(30)]
    limited = apply_voice_limits(rows, limit=5)
    assert len(limited) == 5


def test_apply_business_filters_status_and_priority():
    rows = [
        {"status": "open", "priority": "high"},
        {"status": "closed", "priority": "high"},
        {"status": "open", "priority": "low"},
    ]
    filtered = apply_business_filters(rows, status="open", priority="high")
    assert filtered == [{"status": "open", "priority": "high"}]


def test_prioritize_for_voice_orders_newest_first():
    rows = [
        {"created_at": "2026-01-01T00:00:00", "id": 1},
        {"created_at": "2026-03-01T00:00:00", "id": 2},
        {"created_at": "2026-02-01T00:00:00", "id": 3},
    ]
    ordered = prioritize_for_voice(rows)
    assert [item["id"] for item in ordered] == [2, 3, 1]


def test_paginate_data_returns_expected_page():
    rows = [{"id": index} for index in range(1, 13)]
    page_rows, total_pages, has_next = paginate_data(rows, page=2, page_size=5)

    assert [item["id"] for item in page_rows] == [6, 7, 8, 9, 10]
    assert total_pages == 3
    assert has_next is True
