"""Unit tests for the AWS statistics-dashboard Lambda handler."""

from __future__ import annotations

import importlib.util
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

_TOKEN = "stats-token-that-is-long-enough"


@pytest.fixture
def stats_app(monkeypatch):
    path = (
        Path(__file__).parents[2]
        / "infra"
        / "run_counter"
        / "stats_function"
        / "app.py"
    )
    spec = importlib.util.spec_from_file_location("stats_lambda", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    monkeypatch.setenv("TABLE_NAME", "run-counter-test")
    monkeypatch.setenv("STATS_TOKEN", _TOKEN)
    return module


def _request(path: str, token: str | None = _TOKEN):
    headers = {}
    if token is not None:
        headers["authorization"] = f"Bearer {token}"
    return {"rawPath": path, "headers": headers}


def _counter_item(sort_key: str, count: int):
    return {"sk": {"S": sort_key}, "run_count": {"N": str(count)}}


def _event_item(recorded_at: str, event_type: str, username: str, saved_name: str):
    name_field = "report_name" if event_type == "report_saved" else "setting_name"
    return {
        "sk": {"S": "11111111-1111-1111-1111-111111111111"},
        "event_type": {"S": event_type},
        "username": {"S": username},
        "recorded_at": {"S": recorded_at},
        name_field: {"S": saved_name},
    }


class FakeDynamoDB:
    """Serve canned Query pages keyed by partition key."""

    def __init__(self, pages_by_partition):
        self.pages_by_partition = pages_by_partition
        self.queries = []

    def query(self, **kwargs):
        self.queries.append(kwargs)
        partition = kwargs["ExpressionAttributeValues"][":pk"]["S"]
        pages = self.pages_by_partition.get(partition, [{"Items": []}])
        page_index = 0
        if "ExclusiveStartKey" in kwargs:
            page_index = kwargs["ExclusiveStartKey"]["page"]
        return pages[page_index]


def test_stats_page_is_served_without_authentication(stats_app):
    response = stats_app.lambda_handler(_request("/stats", token=None), None)

    assert response["statusCode"] == 200
    assert response["headers"]["Content-Type"].startswith("text/html")
    assert "Clinical Reporting" in response["body"]


def test_data_requires_the_read_token(stats_app):
    stats_app._dynamodb_client = FakeDynamoDB({})

    assert (
        stats_app.lambda_handler(_request("/stats/data", token=None), None)[
            "statusCode"
        ]
        == 401
    )
    assert (
        stats_app.lambda_handler(_request("/stats/data", token="wrong"), None)[
            "statusCode"
        ]
        == 401
    )
    assert stats_app._dynamodb_client.queries == []


def test_write_token_does_not_grant_read_access(stats_app, monkeypatch):
    monkeypatch.setenv("COUNTER_TOKEN", "desktop-write-token-that-is-long")
    stats_app._dynamodb_client = FakeDynamoDB({})

    response = stats_app.lambda_handler(
        _request("/stats/data", token="desktop-write-token-that-is-long"), None
    )

    assert response["statusCode"] == 401


def test_unknown_path_returns_404(stats_app):
    assert stats_app.lambda_handler(_request("/other"), None)["statusCode"] == 404


def test_data_aggregates_counters_and_recent_events(stats_app):
    today = datetime.now(timezone.utc)
    recent_date = f"{today:%Y-%m-%d}"
    old_date = f"{today - timedelta(days=200):%Y-%m-%d}"
    stats_app._dynamodb_client = FakeDynamoDB(
        {
            "COUNTER#REPORT_SAVED": [
                {
                    "Items": [
                        _counter_item("TOTAL", 12),
                        _counter_item(f"DAILY#{recent_date}", 3),
                        _counter_item(f"DAILY#{old_date}", 9),
                        _counter_item("USER#hmn39", 8),
                        _counter_item("USER#abc12", 4),
                    ]
                }
            ],
            "COUNTER#SETTING_SAVED": [
                {
                    "Items": [
                        _counter_item("TOTAL", 2),
                        _counter_item(f"DAILY#{recent_date}", 2),
                        _counter_item("USER#hmn39", 2),
                    ]
                }
            ],
            "EVENT": [
                {
                    "Items": [
                        _event_item(
                            "2026-08-01T10:00:00+00:00",
                            "report_saved",
                            "hmn39",
                            "Enrollment 260801.xlsx",
                        ),
                        _event_item(
                            "2026-09-01T09:00:00+00:00",
                            "setting_saved",
                            "abc12",
                            "baseline",
                        ),
                    ]
                }
            ],
        }
    )

    response = stats_app.lambda_handler(_request("/stats/data"), None)

    assert response["statusCode"] == 200
    assert response["headers"]["Content-Type"] == "application/json"
    statistics = json.loads(response["body"])

    assert statistics["report_saved"]["total"] == 12
    # Daily rows outside the 90-day window are dropped.
    assert statistics["report_saved"]["daily"] == [{"date": recent_date, "count": 3}]
    # Users are sorted by descending count.
    assert statistics["report_saved"]["users"] == [
        {"username": "hmn39", "count": 8},
        {"username": "abc12", "count": 4},
    ]
    assert statistics["setting_saved"]["total"] == 2

    # Events are newest first and keep the type-specific saved name.
    recent = statistics["recent_events"]
    assert [item["recorded_at"] for item in recent] == [
        "2026-09-01T09:00:00+00:00",
        "2026-08-01T10:00:00+00:00",
    ]
    assert recent[0]["saved_name"] == "baseline"
    assert recent[1]["saved_name"] == "Enrollment 260801.xlsx"


def test_data_follows_dynamodb_pagination(stats_app):
    today = f"{datetime.now(timezone.utc):%Y-%m-%d}"
    stats_app._dynamodb_client = FakeDynamoDB(
        {
            "COUNTER#REPORT_SAVED": [
                {
                    "Items": [_counter_item("TOTAL", 5)],
                    "LastEvaluatedKey": {"page": 1},
                },
                {"Items": [_counter_item(f"DAILY#{today}", 5)]},
            ],
        }
    )

    response = stats_app.lambda_handler(_request("/stats/data"), None)

    statistics = json.loads(response["body"])
    assert statistics["report_saved"]["total"] == 5
    assert statistics["report_saved"]["daily"] == [{"date": today, "count": 5}]


def test_data_failure_and_missing_table_return_503(stats_app, monkeypatch):
    class FailingClient:
        def query(self, **_kwargs):
            raise RuntimeError("dynamodb unavailable")

    stats_app._dynamodb_client = FailingClient()
    assert stats_app.lambda_handler(_request("/stats/data"), None)["statusCode"] == 503

    monkeypatch.delenv("TABLE_NAME")
    assert stats_app.lambda_handler(_request("/stats/data"), None)["statusCode"] == 503


def test_recent_events_are_capped(stats_app):
    items = [
        _event_item(
            f"2026-08-{day:02d}T00:00:00+00:00", "report_saved", "hmn39", "r.xlsx"
        )
        for day in range(1, 29)
    ] * 3  # 84 events, above the 50-event cap.
    stats_app._dynamodb_client = FakeDynamoDB({"EVENT": [{"Items": items}]})

    response = stats_app.lambda_handler(_request("/stats/data"), None)

    statistics = json.loads(response["body"])
    assert len(statistics["recent_events"]) == statistics["recent_event_limit"] == 50
    recorded = [item["recorded_at"] for item in statistics["recent_events"]]
    assert recorded == sorted(recorded, reverse=True)
