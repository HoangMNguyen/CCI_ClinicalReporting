"""AWS Lambda handler for the Clinical Reporting successful-run counter."""

from __future__ import annotations

import json
import os
import secrets
import time
import uuid
from datetime import datetime, timezone
from typing import Any

_dynamodb_client = None


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


def _event_id(event: dict[str, Any]) -> str | None:
    try:
        body = json.loads(event.get("body") or "{}")
        value = str(body["event_id"])
        parsed = uuid.UUID(value)
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None
    return str(parsed) if value.lower() == str(parsed) else None


def _already_recorded(client, table_name: str, event_id: str) -> bool:
    result = client.get_item(
        TableName=table_name,
        Key={"pk": {"S": "EVENT"}, "sk": {"S": event_id}},
        ConsistentRead=True,
    )
    return "Item" in result


def lambda_handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    """Record an authenticated, idempotent successful-export event."""

    if not _authorized(event):
        return _response(401)

    event_id = _event_id(event)
    if event_id is None:
        return _response(400)

    table_name = os.environ.get("TABLE_NAME", "")
    if not table_name:
        return _response(503)

    now = datetime.now(timezone.utc)
    now_text = now.isoformat()
    daily_key = f"DAILY#{now:%Y-%m-%d}"
    expires_at = str(int(time.time()) + (90 * 24 * 60 * 60))
    number_values = {
        ":zero": {"N": "0"},
        ":one": {"N": "1"},
        ":now": {"S": now_text},
    }

    client = _client()
    try:
        client.transact_write_items(
            TransactItems=[
                {
                    "Put": {
                        "TableName": table_name,
                        "Item": {
                            "pk": {"S": "EVENT"},
                            "sk": {"S": event_id},
                            "recorded_at": {"S": now_text},
                            "expires_at": {"N": expires_at},
                        },
                        "ConditionExpression": "attribute_not_exists(pk)",
                    }
                },
                {
                    "Update": {
                        "TableName": table_name,
                        "Key": {"pk": {"S": "COUNTER"}, "sk": {"S": daily_key}},
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
                        "Key": {"pk": {"S": "COUNTER"}, "sk": {"S": "TOTAL"}},
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
