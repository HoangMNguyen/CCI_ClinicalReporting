"""AWS Lambda handler for Clinical Reporting save-usage events."""

from __future__ import annotations

import json
import os
import secrets
import time
import uuid
from datetime import datetime, timezone
from typing import Any

_dynamodb_client = None
_VALID_EVENT_TYPES = frozenset({"report_saved", "setting_saved"})
_EVENT_NAME_FIELDS = {
    "report_saved": "report_name",
    "setting_saved": "setting_name",
}


def _response(status_code: int) -> dict[str, Any]:
    """Return an empty API Gateway HTTP API response."""

    return {"statusCode": status_code, "body": ""}


def _client():
    """Create the DynamoDB client lazily so the handler remains testable."""

    global _dynamodb_client
    if _dynamodb_client is None:
        import boto3  # Available in the managed Lambda Python runtime.

        _dynamodb_client = boto3.client("dynamodb")
    return _dynamodb_client


def _authorized(event: dict[str, Any]) -> bool:
    expected = os.environ.get("COUNTER_TOKEN", "")
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


def _valid_username(username: str) -> bool:
    """Accept common local/domain login names while rejecting key delimiters."""

    allowed_punctuation = frozenset("._-@\\")
    return (
        0 < len(username) <= 128
        and all(
            character.isalnum() or character in allowed_punctuation
            for character in username
        )
    )


def _valid_saved_name(saved_name: str) -> bool:
    """Allow human-readable names while bounding event size."""

    return (
        0 < len(saved_name) <= 255
        and all(character.isprintable() for character in saved_name)
    )


def _event_payload(
    event: dict[str, Any],
) -> tuple[str, str, str, str | None] | None:
    try:
        body = json.loads(event.get("body") or "{}")
        value = str(body["event_id"])
        parsed = uuid.UUID(value)
        event_type = str(body["event_type"])
        username = str(body["username"]).strip()
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None
    if value.lower() != str(parsed):
        return None
    if event_type not in _VALID_EVENT_TYPES or not _valid_username(username):
        return None

    name_field = _EVENT_NAME_FIELDS[event_type]
    saved_name = body.get(name_field)
    # Keep accepting clients released before name tracking was added. Deploying
    # this Lambda first therefore does not interrupt telemetry during rollout.
    if saved_name is not None:
        if not isinstance(saved_name, str):
            return None
        saved_name = saved_name.strip()
        if not _valid_saved_name(saved_name):
            return None
    return str(parsed), event_type, username, saved_name


def _already_recorded(client, table_name: str, event_id: str) -> bool:
    result = client.get_item(
        TableName=table_name,
        Key={"pk": {"S": "EVENT"}, "sk": {"S": event_id}},
        ConsistentRead=True,
    )
    return "Item" in result


def lambda_handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    """Record an authenticated, idempotent report/setting save event."""

    if not _authorized(event):
        return _response(401)

    payload = _event_payload(event)
    if payload is None:
        return _response(400)
    event_id, event_type, username, saved_name = payload

    table_name = os.environ.get("TABLE_NAME", "")
    if not table_name:
        return _response(503)

    now = datetime.now(timezone.utc)
    now_text = now.isoformat()
    daily_key = f"DAILY#{now:%Y-%m-%d}"
    counter_partition = f"COUNTER#{event_type.upper()}"
    user_key = f"USER#{username}"
    expires_at = str(int(time.time()) + (90 * 24 * 60 * 60))
    number_values = {
        ":zero": {"N": "0"},
        ":one": {"N": "1"},
        ":now": {"S": now_text},
    }
    event_item = {
        "pk": {"S": "EVENT"},
        "sk": {"S": event_id},
        "event_type": {"S": event_type},
        "username": {"S": username},
        "recorded_at": {"S": now_text},
        "expires_at": {"N": expires_at},
    }
    if saved_name is not None:
        event_item[_EVENT_NAME_FIELDS[event_type]] = {"S": saved_name}

    client = _client()
    try:
        client.transact_write_items(
            TransactItems=[
                {
                    "Put": {
                        "TableName": table_name,
                        "Item": event_item,
                        "ConditionExpression": "attribute_not_exists(pk)",
                    }
                },
                {
                    "Update": {
                        "TableName": table_name,
                        "Key": {"pk": {"S": counter_partition}, "sk": {"S": daily_key}},
                        "UpdateExpression": (
                            "SET run_count = if_not_exists(run_count, :zero) + :one, "
                            "updated_at = :now"
                        ),
                        "ExpressionAttributeValues": number_values,
                    }
                },
                {
                    "Update": {
                        "TableName": table_name,
                        "Key": {"pk": {"S": counter_partition}, "sk": {"S": "TOTAL"}},
                        "UpdateExpression": (
                            "SET run_count = if_not_exists(run_count, :zero) + :one, "
                            "updated_at = :now"
                        ),
                        "ExpressionAttributeValues": number_values,
                    }
                },
                {
                    "Update": {
                        "TableName": table_name,
                        "Key": {"pk": {"S": counter_partition}, "sk": {"S": user_key}},
                        "UpdateExpression": (
                            "SET run_count = if_not_exists(run_count, :zero) + :one, "
                            "updated_at = :now"
                        ),
                        "ExpressionAttributeValues": number_values,
                    }
                },
            ]
        )
    except Exception as exc:  # boto3 exceptions are generated dynamically.
        error = getattr(exc, "response", {}).get("Error", {}).get("Code")
        if error == "TransactionCanceledException":
            try:
                if _already_recorded(client, table_name, event_id):
                    return _response(204)
            except Exception:
                pass
        return _response(503)

    return _response(204)
