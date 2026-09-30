"""Tests for running slow work in the background (cci_ui.tasks)."""

import sys
import threading

import pytest
from PySide6.QtCore import QElapsedTimer, QThread
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QWidget

from cci_ui.tasks import TaskRunner, run_task
from cci_ui.widgets.busy import BusyOverlay


def _settle(runner, timeout_ms=3000):
    """Wait for the worker, then let its queued callbacks run."""
    assert runner.wait(timeout_ms)
    timer = QElapsedTimer()
    timer.start()
    while runner.busy and timer.elapsed() < timeout_ms:
        QTest.qWait(10)


def test_work_runs_off_the_gui_thread_and_callbacks_on_it(qapp):
    runner = TaskRunner()
    seen = {}

    def work(value):
        seen["work_thread"] = QThread.currentThread()
        return value * 2

    def done(result):
        seen["result"] = result
        seen["callback_thread"] = QThread.currentThread()

    assert runner.submit(work, 21, on_success=done)
    _settle(runner)

    assert seen["result"] == 42
    assert seen["work_thread"] is not qapp.thread()
    assert seen["callback_thread"] is qapp.thread()


def test_failures_come_back_with_their_traceback(qapp):
    runner = TaskRunner()
    errors = []

    def work():
        raise ValueError("File is not a zip file")

    runner.submit(
        work, on_success=lambda _r: None, on_error=lambda e, tb: errors.append((e, tb))
    )
    _settle(runner)

    ((exc, details),) = errors
    assert isinstance(exc, ValueError)
    assert "File is not a zip file" in details and "Traceback" in details


def test_one_job_at_a_time(qapp):
    runner = TaskRunner()
    release = threading.Event()
    results = []

    first = runner.submit(
        release.wait, 5, on_success=lambda _r: results.append("first")
    )
    second = runner.submit(lambda: None, on_success=lambda _r: results.append("second"))
    release.set()
    _settle(runner)

    assert first and not second
    assert results == ["first"] and not runner.busy


def test_busy_overlay_follows_the_job(qapp):
    window = QWidget()
    window.resize(300, 200)
    window.show()
    overlay = BusyOverlay(window)
    runner = TaskRunner(overlay=overlay)
    states = []
    runner.busyChanged.connect(states.append)
    release = threading.Event()

    runner.submit(release.wait, 5, on_success=lambda _r: None, message="Reading ZIP…")
    during = overlay.busy
    runner.set_message("Reading 18 forms…")
    release.set()
    _settle(runner)

    assert during and overlay.message() == "Reading 18 forms…"
    assert not overlay.busy and states == [True, False]
    window.close()


def test_discarded_results_are_ignored(qapp):
    runner = TaskRunner()
    release = threading.Event()
    results = []

    runner.submit(release.wait, 5, on_success=lambda _r: results.append("late"))
    runner.discard_results()
    release.set()
    runner.wait(3000)
    QTest.qWait(50)

    assert results == [] and not runner.busy


def test_a_failing_callback_still_ends_the_busy_state(qapp, monkeypatch):
    raised = []
    monkeypatch.setattr(sys, "excepthook", lambda *args: raised.append(args[1]))
    runner = TaskRunner()

    def broken_callback(_result):
        raise RuntimeError("callback bug")

    runner.submit(lambda: 1, on_success=broken_callback)
    _settle(runner)

    assert not runner.busy
    assert [type(error) for error in raised] == [RuntimeError]


def test_run_task_without_a_runner_runs_directly():
    class Host:
        pass

    results, errors = [], []
    assert run_task(Host(), lambda x: x + 1, 1, on_success=results.append)
    run_task(
        Host(),
        lambda: 1 / 0,
        on_success=results.append,
        on_error=lambda e, tb: errors.append(type(e)),
    )

    assert results == [2] and errors == [ZeroDivisionError]
    with pytest.raises(ZeroDivisionError):
        run_task(Host(), lambda: 1 / 0, on_success=results.append)


def test_run_task_uses_the_hosts_runner(qapp):
    class Host:
        task_runner = TaskRunner()

    results = []
    assert run_task(Host(), lambda: "done", on_success=results.append)
    _settle(Host.task_runner)

    assert results == ["done"]


def test_a_callback_can_start_the_next_job(qapp):
    runner = TaskRunner()
    states, results = [], []
    runner.busyChanged.connect(states.append)

    def after_preview(preview):
        results.append(preview)
        assert runner.submit(lambda: "exported", on_success=results.append)

    runner.submit(lambda: "preview", on_success=after_preview)
    _settle(runner)
    _settle(runner)

    assert results == ["preview", "exported"]
    assert states == [True, False]  # busy the whole way, then idle once


def test_system_exit_in_the_work_still_reports_back(qapp):
    runner = TaskRunner()
    errors = []

    def work():
        raise SystemExit(3)

    runner.submit(
        work, on_success=lambda _r: None, on_error=lambda e, tb: errors.append(e)
    )
    _settle(runner)

    assert [type(error) for error in errors] == [SystemExit] and not runner.busy


def test_unhandled_failures_reach_the_error_hook(qapp, monkeypatch):
    raised = []
    monkeypatch.setattr(sys, "excepthook", lambda *args: raised.append(args[1]))
    runner = TaskRunner()

    runner.submit(lambda: 1 / 0, on_success=lambda _r: None)
    _settle(runner)

    assert [type(error) for error in raised] == [ZeroDivisionError]


def test_finished_jobs_release_their_bookkeeping(qapp):
    runner = TaskRunner()
    for value in range(20):
        runner.submit(lambda v=value: v, on_success=lambda _r: None)
        _settle(runner)

    assert runner._jobs == {}
