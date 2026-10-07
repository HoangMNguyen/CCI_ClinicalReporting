"""Tests for silent successful-save usage reporting."""

from __future__ import annotations

import json
import threading

import pytest

from clinical_reporting import telemetry


def test_the_tests_never_count_runs(monkeypatch):
    """No test reaches the usage endpoint, even with telemetry.json in place.

    A developer's checkout holds the bundled telemetry.json for the builds;
    the suite must not count its exports and saves there.
    """
    posted = []
    monkeypatch.setattr(
        telemetry, "urlopen", lambda request, timeout: posted.append(request)
    )
    before = set(threading.enumerate())

    telemetry.record_successful_export("monthly report.xlsx")
    telemetry.record_successful_setting_save("monthly")
    for worker in set(threading.enumerate()) - before:
        worker.join(timeout=5)

    assert posted == []


def test_counter_is_disabled_without_configuration(monkeypatch):
    monkeypatch.delenv(telemetry.RUN_COUNTER_URL_ENV, raising=False)
    monkeypatch.delenv(telemetry.RUN_COUNTER_TOKEN_ENV, raising=False)
    monkeypatch.setattr(telemetry, "_bundled_configuration", lambda: ("", ""))

    def unexpected_thread(**_kwargs):
        raise AssertionError("a worker should not be created")

    monkeypatch.setattr(telemetry.threading, "Thread", unexpected_thread)
    telemetry.record_successful_export("monthly report.xlsx")


def test_bundled_configuration_is_used_without_environment(monkeypatch):
    monkeypatch.delenv(telemetry.RUN_COUNTER_URL_ENV, raising=False)
    monkeypatch.delenv(telemetry.RUN_COUNTER_TOKEN_ENV, raising=False)
    monkeypatch.setattr(
        telemetry,
        "_bundled_configuration",
        lambda: ("https://bundled.example/run", "bundled-token"),
    )
    captured = {}

    class FakeThread:
        def __init__(self, **kwargs):
            captured.update(kwargs)

        def start(self):
            captured["started"] = True

    monkeypatch.setattr(telemetry.threading, "Thread", FakeThread)
    monkeypatch.setattr(telemetry.getpass, "getuser", lambda: "hmn39")

    telemetry.record_successful_export("monthly report.xlsx")

    assert captured["args"][:2] == (
        "https://bundled.example/run",
        "bundled-token",
    )
    assert captured["started"] is True


def test_environment_overrides_bundled_configuration(monkeypatch):
    monkeypatch.setenv(telemetry.RUN_COUNTER_URL_ENV, "https://override.example/run")
    monkeypatch.setenv(telemetry.RUN_COUNTER_TOKEN_ENV, "override-token")
    monkeypatch.setattr(
        telemetry,
        "_bundled_configuration",
        lambda: ("https://bundled.example/run", "bundled-token"),
    )

    assert telemetry._configuration() == (
        "https://override.example/run",
        "override-token",
    )


def test_counter_uses_a_daemon_worker(monkeypatch):
    monkeypatch.setenv(telemetry.RUN_COUNTER_URL_ENV, "https://example.test/run")
    monkeypatch.setenv(telemetry.RUN_COUNTER_TOKEN_ENV, "secret-token")
    monkeypatch.setattr(telemetry.getpass, "getuser", lambda: "hmn39")
    captured = {}

    class FakeThread:
        def __init__(self, **kwargs):
            captured.update(kwargs)

        def start(self):
            captured["started"] = True

    monkeypatch.setattr(telemetry.threading, "Thread", FakeThread)
    telemetry.record_successful_export("monthly report.xlsx")

    assert captured["target"] is telemetry._post_event
    assert captured["args"][:2] == ("https://example.test/run", "secret-token")
    assert captured["args"][3:] == (
        telemetry.REPORT_SAVED_EVENT,
        "hmn39",
        "monthly report.xlsx",
    )
    assert captured["daemon"] is True
    assert captured["started"] is True


def test_setting_save_uses_setting_event_type(monkeypatch):
    monkeypatch.setenv(telemetry.RUN_COUNTER_URL_ENV, "https://example.test/run")
    monkeypatch.setenv(telemetry.RUN_COUNTER_TOKEN_ENV, "secret-token")
    monkeypatch.setattr(telemetry.getpass, "getuser", lambda: "hmn39")
    captured = {}

    class FakeThread:
        def __init__(self, **kwargs):
            captured.update(kwargs)

        def start(self):
            pass

    monkeypatch.setattr(telemetry.threading, "Thread", FakeThread)

    telemetry.record_successful_setting_save("baseline")

    assert captured["args"][3:] == (
        telemetry.SETTING_SAVED_EVENT,
        "hmn39",
        "baseline",
    )


def test_post_contains_event_identity_type_and_authentication(monkeypatch):
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
    telemetry._post_event(
        "https://example.test/run",
        "secret-token",
        "event-123",
        telemetry.REPORT_SAVED_EVENT,
        "hmn39",
        "monthly report.xlsx",
    )

    request = captured["request"]
    assert request.full_url == "https://example.test/run"
    assert request.method == "POST"
    assert json.loads(request.data) == {
        "event_id": "event-123",
        "event_type": "report_saved",
        "username": "hmn39",
        "report_name": "monthly report.xlsx",
    }
    assert request.get_header("Authorization") == "Bearer secret-token"
    assert captured["timeout"] == telemetry._REQUEST_TIMEOUT_SECONDS
    assert captured["read"] is True


def test_all_delivery_and_thread_errors_are_suppressed(monkeypatch):
    def failed_urlopen(*_args, **_kwargs):
        raise OSError("offline")

    monkeypatch.setattr(telemetry, "urlopen", failed_urlopen)
    telemetry._post_event(
        "https://example.test/run",
        "secret",
        "event-123",
        telemetry.REPORT_SAVED_EVENT,
        "hmn39",
        "monthly report.xlsx",
    )

    monkeypatch.setenv(telemetry.RUN_COUNTER_URL_ENV, "https://example.test/run")
    monkeypatch.setenv(telemetry.RUN_COUNTER_TOKEN_ENV, "secret")
    monkeypatch.setattr(telemetry.getpass, "getuser", lambda: "hmn39")

    def failed_thread(**_kwargs):
        raise RuntimeError("thread unavailable")

    monkeypatch.setattr(telemetry.threading, "Thread", failed_thread)
    telemetry.record_successful_export("monthly report.xlsx")


def test_username_lookup_errors_are_suppressed(monkeypatch):
    monkeypatch.setenv(telemetry.RUN_COUNTER_URL_ENV, "https://example.test/run")
    monkeypatch.setenv(telemetry.RUN_COUNTER_TOKEN_ENV, "secret")

    def failed_username_lookup():
        raise OSError("login unavailable")

    monkeypatch.setattr(telemetry.getpass, "getuser", failed_username_lookup)
    telemetry.record_successful_export("monthly report.xlsx")


def test_the_bundled_configuration_needs_an_endpoint_and_a_token(monkeypatch):
    def bundled(*values):
        monkeypatch.setattr(telemetry, "_bundled_configuration", lambda: values)
        return telemetry.has_bundled_configuration()

    # The environment doesn't count: the check is about the bundled file.
    monkeypatch.setenv(telemetry.RUN_COUNTER_URL_ENV, "https://env.example/run")
    monkeypatch.setenv(telemetry.RUN_COUNTER_TOKEN_ENV, "env-token")

    assert bundled("", "") is False
    assert bundled("https://x.example/run", "") is False
    assert bundled("", "token") is False
    assert bundled("https://x.example/run", "token") is True


def test_the_clinical_reporting_self_test_reports_the_bundled_file(monkeypatch):
    pytest.importorskip("PySide6")
    from clinical_reporting.ui import app as cr_app

    monkeypatch.setattr(telemetry, "has_bundled_configuration", lambda: True)

    assert cr_app._self_test_extra() == {"telemetry_bundled": True}
