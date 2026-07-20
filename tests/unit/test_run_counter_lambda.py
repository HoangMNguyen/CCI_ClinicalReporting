"""Unit tests for the AWS run-counter Lambda handler."""

from __future__ import annotations

import importlib.util
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


def _event(event_id: str, token: str = "test-token-that-is-long-enough"):
    return {
        "headers": {"authorization": f"Bearer {token}"},
        "body": f'{{"event_id": "{event_id}"}}',
    }


class FakeDynamoDB:
    def __init__(self):
        self.transactions = []

    def transact_write_items(self, **kwargs):
        self.transactions.append(kwargs)


def test_valid_event_increments_daily_and_total_counts(lambda_app):
    client = FakeDynamoDB()
    lambda_app._dynamodb_client = client
    event_id = str(uuid.uuid4())

    response = lambda_app.lambda_handler(_event(event_id), None)

    assert response["statusCode"] == 204
    writes = client.transactions[0]["TransactItems"]
    assert writes[0]["Put"]["Item"]["sk"] == {"S": event_id}
    assert writes[1]["Update"]["Key"]["sk"]["S"].startswith("DAILY#")
    assert writes[2]["Update"]["Key"]["sk"] == {"S": "TOTAL"}


def test_invalid_auth_and_payload_are_rejected_without_dynamodb(lambda_app):
    client = FakeDynamoDB()
    lambda_app._dynamodb_client = client

    assert lambda_app.lambda_handler(_event(str(uuid.uuid4()), "wrong"), None)["statusCode"] == 401
    assert lambda_app.lambda_handler(_event("not-a-uuid"), None)["statusCode"] == 400
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
