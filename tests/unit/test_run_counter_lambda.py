"""Unit tests for the AWS run-counter Lambda handler."""

from __future__ import annotations

import importlib.util
import json
import uuid
from pathlib import Path

import pytest


@pytest.fixture
def lambda_app(monkeypatch):
    path = Path(__file__).parents[2] / "infra" / "run_counter" / "function" / "app.py"
    spec = importlib.util.spec_from_file_location("run_counter_lambda", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    monkeypatch.setenv("TABLE_NAME", "run-counter-test")
    monkeypatch.setenv("COUNTER_TOKEN", "test-token-that-is-long-enough")
    return module


def _event(
    event_id: str,
    token: str = "test-token-that-is-long-enough",
    event_type: str = "report_saved",
    username: str = "hmn39",
    saved_name: str | None = None,
):
    if saved_name is None:
        saved_name = (
            "monthly report.xlsx" if event_type == "report_saved" else "baseline"
        )
    name_field = "report_name" if event_type == "report_saved" else "setting_name"
    return {
        "headers": {"authorization": f"Bearer {token}"},
        "body": json.dumps(
            {
                "event_id": event_id,
                "event_type": event_type,
                "username": username,
                name_field: saved_name,
            }
        ),
    }


class FakeDynamoDB:
    def __init__(self):
        self.transactions = []

    def transact_write_items(self, **kwargs):
        self.transactions.append(kwargs)


def test_valid_event_stores_identity_and_increments_event_counters(lambda_app):
    client = FakeDynamoDB()
    lambda_app._dynamodb_client = client
    event_id = str(uuid.uuid4())

    response = lambda_app.lambda_handler(_event(event_id), None)

    assert response["statusCode"] == 204
    writes = client.transactions[0]["TransactItems"]
    event_item = writes[0]["Put"]["Item"]
    assert event_item["sk"] == {"S": event_id}
    assert event_item["event_type"] == {"S": "report_saved"}
    assert event_item["username"] == {"S": "hmn39"}
    assert event_item["report_name"] == {"S": "monthly report.xlsx"}
    assert writes[1]["Update"]["Key"]["pk"] == {"S": "COUNTER#REPORT_SAVED"}
    assert writes[1]["Update"]["Key"]["sk"]["S"].startswith("DAILY#")
    assert writes[2]["Update"]["Key"]["sk"] == {"S": "TOTAL"}
    assert writes[3]["Update"]["Key"]["sk"] == {"S": "USER#hmn39"}


def test_setting_event_uses_separate_counter_partition(lambda_app):
    client = FakeDynamoDB()
    lambda_app._dynamodb_client = client

    response = lambda_app.lambda_handler(
        _event(str(uuid.uuid4()), event_type="setting_saved"),
        None,
    )

    assert response["statusCode"] == 204
    writes = client.transactions[0]["TransactItems"]
    assert writes[0]["Put"]["Item"]["setting_name"] == {"S": "baseline"}
    assert writes[1]["Update"]["Key"]["pk"] == {"S": "COUNTER#SETTING_SAVED"}


def test_legacy_event_without_a_saved_name_remains_accepted(lambda_app):
    client = FakeDynamoDB()
    lambda_app._dynamodb_client = client
    event = _event(str(uuid.uuid4()))
    body = json.loads(event["body"])
    del body["report_name"]
    event["body"] = json.dumps(body)

    response = lambda_app.lambda_handler(event, None)

    assert response["statusCode"] == 204
    assert (
        "report_name" not in client.transactions[0]["TransactItems"][0]["Put"]["Item"]
    )


def test_invalid_auth_and_payload_are_rejected_without_dynamodb(lambda_app):
    client = FakeDynamoDB()
    lambda_app._dynamodb_client = client

    assert (
        lambda_app.lambda_handler(_event(str(uuid.uuid4()), "wrong"), None)[
            "statusCode"
        ]
        == 401
    )
    assert lambda_app.lambda_handler(_event("not-a-uuid"), None)["statusCode"] == 400
    assert (
        lambda_app.lambda_handler(
            _event(str(uuid.uuid4()), event_type="unsupported"),
            None,
        )["statusCode"]
        == 400
    )
    assert (
        lambda_app.lambda_handler(
            _event(str(uuid.uuid4()), username="invalid user"),
            None,
        )["statusCode"]
        == 400
    )
    assert (
        lambda_app.lambda_handler(
            _event(str(uuid.uuid4()), saved_name="line one\nline two"),
            None,
        )["statusCode"]
        == 400
    )
    assert client.transactions == []


def test_duplicate_event_is_success_without_a_second_increment(lambda_app):
    class TransactionCanceled(Exception):
        response = {"Error": {"Code": "TransactionCanceledException"}}

    class DuplicateClient(FakeDynamoDB):
        def transact_write_items(self, **kwargs):
            raise TransactionCanceled()

        def get_item(self, **_kwargs):
            return {"Item": {"pk": {"S": "EVENT"}}}

    lambda_app._dynamodb_client = DuplicateClient()

    response = lambda_app.lambda_handler(_event(str(uuid.uuid4())), None)

    assert response["statusCode"] == 204
