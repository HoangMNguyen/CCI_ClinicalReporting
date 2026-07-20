"""Tests for silent successful-export counting."""

from __future__ import annotations

import json

from clinical_reporting import telemetry


def test_counter_is_disabled_without_configuration(monkeypatch):
    monkeypatch.delenv(telemetry.RUN_COUNTER_URL_ENV, raising=False)
    monkeypatch.delenv(telemetry.RUN_COUNTER_TOKEN_ENV, raising=False)

    def unexpected_thread(**_kwargs):
        raise AssertionError("a worker should not be created")

    monkeypatch.setattr(telemetry.threading, "Thread", unexpected_thread)
    telemetry.record_successful_export()


def test_counter_uses_a_daemon_worker(monkeypatch):
    monkeypatch.setenv(telemetry.RUN_COUNTER_URL_ENV, "https://example.test/run")
    monkeypatch.setenv(telemetry.RUN_COUNTER_TOKEN_ENV, "secret-token")
    captured = {}

    class FakeThread:
        def __init__(self, **kwargs):
            captured.update(kwargs)

        def start(self):
            captured["started"] = True

    monkeypatch.setattr(telemetry.threading, "Thread", FakeThread)
    telemetry.record_successful_export()

    assert captured["target"] is telemetry._post_run
    assert captured["args"][:2] == ("https://example.test/run", "secret-token")
    assert captured["daemon"] is True
    assert captured["started"] is True


def test_post_contains_only_event_id_and_authentication(monkeypatch):
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self):
            captured["read"] = True

    def fake_urlopen(request, timeout):
        captured["request"] = request
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(telemetry, "urlopen", fake_urlopen)
    telemetry._post_run("https://example.test/run", "secret-token", "event-123")

    request = captured["request"]
    assert request.full_url == "https://example.test/run"
    assert request.method == "POST"
    assert json.loads(request.data) == {"event_id": "event-123"}
    assert request.get_header("Authorization") == "Bearer secret-token"
    assert captured["timeout"] == telemetry._REQUEST_TIMEOUT_SECONDS
    assert captured["read"] is True


def test_all_delivery_and_thread_errors_are_suppressed(monkeypatch):
    def failed_urlopen(*_args, **_kwargs):
        raise OSError("offline")

    monkeypatch.setattr(telemetry, "urlopen", failed_urlopen)
    telemetry._post_run("https://example.test/run", "secret", "event-123")

    monkeypatch.setenv(telemetry.RUN_COUNTER_URL_ENV, "https://example.test/run")
    monkeypatch.setenv(telemetry.RUN_COUNTER_TOKEN_ENV, "secret")

    def failed_thread(**_kwargs):
        raise RuntimeError("thread unavailable")

    monkeypatch.setattr(telemetry.threading, "Thread", failed_thread)
    telemetry.record_successful_export()
