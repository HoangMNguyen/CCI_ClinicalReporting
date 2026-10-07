"""AWS Lambda handler serving the read-only usage statistics dashboard.

Routes:

- ``GET /stats`` returns the dashboard HTML shell. It contains no usage data,
  so it is served without authentication.
- ``GET /stats/data`` returns the aggregated statistics as JSON and requires
  the read-only ``STATS_TOKEN`` bearer token, which is distinct from the
  desktop write token.
"""

from __future__ import annotations

import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

_dynamodb_client = None
_COUNTER_PARTITIONS = {
    "report_saved": "COUNTER#REPORT_SAVED",
    "setting_saved": "COUNTER#SETTING_SAVED",
}
_EVENT_NAME_FIELDS = {
    "report_saved": "report_name",
    "setting_saved": "setting_name",
}
_DAILY_WINDOW_DAYS = 90
_RECENT_EVENT_LIMIT = 50
# Each page returns up to 1 MB; the cap bounds cost if the table ever grows
# far beyond the expected handful of users.
_MAX_QUERY_PAGES = 20
_DASHBOARD_HTML = Path(__file__).with_name("index.html").read_text(encoding="utf-8")


def _response(
    status_code: int,
    body: str = "",
    content_type: str | None = None,
) -> dict[str, Any]:
    headers = {"Cache-Control": "no-store"}
    if content_type:
        headers["Content-Type"] = content_type
    return {"statusCode": status_code, "headers": headers, "body": body}


def _client():
    """Create the DynamoDB client lazily so the handler remains testable."""

    global _dynamodb_client
    if _dynamodb_client is None:
        import boto3  # Available in the managed Lambda Python runtime.

        _dynamodb_client = boto3.client("dynamodb")
    return _dynamodb_client


def _request_path(event: dict[str, Any]) -> str:
    path = event.get("rawPath")
    if isinstance(path, str) and path:
        return path
    path = (event.get("requestContext") or {}).get("http", {}).get("path", "")
    return path if isinstance(path, str) else ""


def _authorized(event: dict[str, Any]) -> bool:
    expected = os.environ.get("STATS_TOKEN", "")
    if not expected:
        return False

    headers = {
        str(key).lower(): str(value)
        for key, value in (event.get("headers") or {}).items()
    }
    authorization = headers.get("authorization", "")
    prefix = "Bearer "
    if not authorization.startswith(prefix):
        return False
    return secrets.compare_digest(authorization[len(prefix) :], expected)


def _query_partition(client, table_name: str, partition_key: str) -> list[dict]:
    items: list[dict] = []
    kwargs: dict[str, Any] = {
        "TableName": table_name,
        "KeyConditionExpression": "pk = :pk",
        "ExpressionAttributeValues": {":pk": {"S": partition_key}},
    }
    for _ in range(_MAX_QUERY_PAGES):
        result = client.query(**kwargs)
        items.extend(result.get("Items", []))
        last_key = result.get("LastEvaluatedKey")
        if not last_key:
            break
        kwargs["ExclusiveStartKey"] = last_key
    return items


def _counter_summary(items: list[dict], earliest_daily_date: str) -> dict[str, Any]:
    total = 0
    daily = []
    users = []
    for item in items:
        sort_key = item.get("sk", {}).get("S", "")
        try:
            count = int(item.get("run_count", {}).get("N", "0"))
        except (TypeError, ValueError):
            continue
        if sort_key == "TOTAL":
            total = count
        elif sort_key.startswith("DAILY#"):
            # Zero-padded ISO dates compare correctly as strings.
            date_text = sort_key[len("DAILY#") :]
            if date_text >= earliest_daily_date:
                daily.append({"date": date_text, "count": count})
        elif sort_key.startswith("USER#"):
            users.append({"username": sort_key[len("USER#") :], "count": count})
    daily.sort(key=lambda row: row["date"])
    users.sort(key=lambda row: (-row["count"], row["username"]))
    return {"total": total, "daily": daily, "users": users}


def _recent_events(items: list[dict]) -> list[dict[str, str]]:
    events = []
    for item in items:
        event_type = item.get("event_type", {}).get("S", "")
        name_field = _EVENT_NAME_FIELDS.get(event_type)
        saved_name = item.get(name_field, {}).get("S", "") if name_field else ""
        events.append(
            {
                "recorded_at": item.get("recorded_at", {}).get("S", ""),
                "event_type": event_type,
                "username": item.get("username", {}).get("S", ""),
                "saved_name": saved_name,
            }
        )
    events.sort(key=lambda row: row["recorded_at"], reverse=True)
    return events[:_RECENT_EVENT_LIMIT]


def _collect_statistics(client, table_name: str) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    earliest_daily_date = f"{now - timedelta(days=_DAILY_WINDOW_DAYS - 1):%Y-%m-%d}"
    statistics: dict[str, Any] = {
        "generated_at": now.isoformat(),
        "daily_window_days": _DAILY_WINDOW_DAYS,
        "recent_event_limit": _RECENT_EVENT_LIMIT,
    }
    for event_type, partition_key in _COUNTER_PARTITIONS.items():
        items = _query_partition(client, table_name, partition_key)
        statistics[event_type] = _counter_summary(items, earliest_daily_date)
    statistics["recent_events"] = _recent_events(
        _query_partition(client, table_name, "EVENT")
    )
    return statistics


def lambda_handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    """Serve the dashboard page and its authenticated JSON data."""

    path = _request_path(event).rstrip("/")

    if path == "/stats":
        return _response(200, _DASHBOARD_HTML, "text/html; charset=utf-8")

    if path == "/stats/data":
        if not _authorized(event):
            return _response(401)
        table_name = os.environ.get("TABLE_NAME", "")
        if not table_name:
            return _response(503)
        try:
            statistics = _collect_statistics(_client(), table_name)
        except Exception:  # boto3 exceptions are generated dynamically.
            return _response(503)
        return _response(200, json.dumps(statistics), "application/json")

    return _response(404)
