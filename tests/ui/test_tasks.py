"""Tests for running slow work in the background (cci_ui.tasks)."""

import sys
import threading

import pytest
from PySide6.QtCore import QThread
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QWidget

from cci_ui.tasks import TaskRunner, defer_if_busy, run_task, when_idle
from cci_ui.widgets.busy import BusyOverlay


def test_work_runs_off_the_gui_thread_and_callbacks_on_it(qapp, settle):
    runner = TaskRunner()
    seen = {}

    def work(value):
        seen["work_thread"] = QThread.currentThread()
        return value * 2

    def done(result):
        seen["result"] = result
        seen["callback_thread"] = QThread.currentThread()

    assert runner.submit(work, 21, on_success=done)
    settle(runner)

    assert seen["result"] == 42
    assert seen["work_thread"] is not qapp.thread()
    assert seen["callback_thread"] is qapp.thread()


def test_failures_come_back_with_their_traceback(qapp, settle):
    runner = TaskRunner()
    errors = []

    def work():
        raise ValueError("File is not a zip file")

    runner.submit(
        work, on_success=lambda _r: None, on_error=lambda e, tb: errors.append((e, tb))
    )
    settle(runner)

    ((exc, details),) = errors
    assert isinstance(exc, ValueError)
    assert "File is not a zip file" in details and "Traceback" in details


def test_one_job_at_a_time(qapp, settle):
    runner = TaskRunner()
    release = threading.Event()
    results = []

    first = runner.submit(
        release.wait, 5, on_success=lambda _r: results.append("first")
    )
    second = runner.submit(lambda: None, on_success=lambda _r: results.append("second"))
    release.set()
    settle(runner)

    assert first and not second
    assert results == ["first"] and not runner.busy


def test_busy_overlay_follows_the_job(qapp, settle):
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
    settle(runner)

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


def test_a_failing_callback_still_ends_the_busy_state(qapp, monkeypatch, settle):
    raised = []
    monkeypatch.setattr(sys, "excepthook", lambda *args: raised.append(args[1]))
    runner = TaskRunner()

    def broken_callback(_result):
        raise RuntimeError("callback bug")

    runner.submit(lambda: 1, on_success=broken_callback)
    settle(runner)

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


def test_run_task_uses_the_hosts_runner(qapp, settle):
    class Host:
        task_runner = TaskRunner()

    results = []
    assert run_task(Host(), lambda: "done", on_success=results.append)
    settle(Host.task_runner)

    assert results == ["done"]


def test_a_callback_can_start_the_next_job(qapp, settle):
    runner = TaskRunner()
    states, results = [], []
    runner.busyChanged.connect(states.append)

    def after_preview(preview):
        results.append(preview)
        assert runner.submit(lambda: "exported", on_success=results.append)

    runner.submit(lambda: "preview", on_success=after_preview)
    settle(runner)
    settle(runner)

    assert results == ["preview", "exported"]
    assert states == [True, False]  # busy the whole way, then idle once


def test_system_exit_in_the_work_still_reports_back(qapp, settle):
    runner = TaskRunner()
    errors = []

    def work():
        raise SystemExit(3)

    runner.submit(
        work, on_success=lambda _r: None, on_error=lambda e, tb: errors.append(e)
    )
    settle(runner)

    assert [type(error) for error in errors] == [SystemExit] and not runner.busy


def test_unhandled_failures_reach_the_error_hook(qapp, monkeypatch, settle):
    raised = []
    monkeypatch.setattr(sys, "excepthook", lambda *args: raised.append(args[1]))
    runner = TaskRunner()

    runner.submit(lambda: 1 / 0, on_success=lambda _r: None)
    settle(runner)

    assert [type(error) for error in raised] == [ZeroDivisionError]


def test_finished_jobs_release_their_bookkeeping(qapp, settle):
    runner = TaskRunner()
    for value in range(20):
        runner.submit(lambda v=value: v, on_success=lambda _r: None)
        settle(runner)

    assert runner._jobs == {}


def test_idle_actions_run_now_or_after_all_chained_work(qapp, settle):
    runner = TaskRunner()
    order = []
    runner.call_when_idle(lambda: order.append("idle now"))

    def after_first(_result):
        order.append("first done")
        runner.submit(lambda: None, on_success=lambda _r: order.append("second done"))

    def later():
        order.append("later")

    runner.submit(lambda: None, on_success=after_first)
    runner.call_when_idle(later)
    runner.call_when_idle(later)  # Queued once.
    settle(runner)
    settle(runner)

    assert order == ["idle now", "first done", "second done", "later"]


def test_an_idle_action_that_starts_work_holds_back_the_rest(qapp, settle):
    runner = TaskRunner()
    order = []
    release = threading.Event()

    def start_more():
        order.append("start")
        runner.submit(release.wait, 5, on_success=lambda _r: order.append("job"))

    runner.submit(lambda: None, on_success=lambda _r: None)
    runner.call_when_idle(start_more)
    runner.call_when_idle(lambda: order.append("after job"))
    assert runner.wait(3000)  # The first job is done; its callback is queued.
    QApplication.processEvents()
    assert order == ["start"] and runner.busy

    release.set()
    settle(runner)

    assert order == ["start", "job", "after job"]


def test_discarding_results_drops_queued_actions(qapp):
    runner = TaskRunner()
    release = threading.Event()
    ran = []
    runner.submit(release.wait, 5, on_success=lambda _r: None)
    runner.call_when_idle(lambda: ran.append(True))

    runner.discard_results()
    release.set()
    runner.wait(3000)
    QTest.qWait(50)

    assert ran == []


def test_a_failing_idle_action_does_not_stop_the_next(qapp, monkeypatch, settle):
    raised = []
    monkeypatch.setattr(sys, "excepthook", lambda *args: raised.append(args[1]))
    runner = TaskRunner()
    ran = []

    def broken():
        raise RuntimeError("action bug")

    runner.submit(lambda: None, on_success=lambda _r: None)
    runner.call_when_idle(broken)
    runner.call_when_idle(lambda: ran.append(True))
    settle(runner)

    assert ran == [True]
    assert [type(error) for error in raised] == [RuntimeError]


def test_defer_if_busy_only_queues_while_the_runner_is_busy(qapp, settle):
    class Host:
        task_runner = TaskRunner()

    ran = []

    def action():
        ran.append(True)

    assert not defer_if_busy(object(), action)
    assert not defer_if_busy(Host(), action)
    Host.task_runner.submit(lambda: None, on_success=lambda _r: None)
    assert defer_if_busy(Host(), action)
    assert ran == []

    settle(Host.task_runner)

    assert ran == [True]


def test_a_shut_down_runner_ignores_its_job_and_starts_nothing(qapp):
    runner = TaskRunner()
    release = threading.Event()
    results = []
    runner.submit(release.wait, 5, on_success=lambda _r: results.append("late"))

    runner.shutdown()
    release.set()
    runner.wait(3000)
    QTest.qWait(50)

    assert results == [] and not runner.busy
    assert not runner.submit(lambda: None, on_success=results.append)
    runner.call_when_idle(lambda: results.append("idle"))
    assert results == []


def test_when_idle_waits_for_the_runner_or_runs_now(qapp, settle):
    class Host:
        task_runner = TaskRunner()

    shown = []
    when_idle(object(), lambda: shown.append("no runner"))
    Host.task_runner.submit(lambda: None, on_success=lambda _r: None)
    when_idle(Host(), lambda: shown.append("after job"))
    assert shown == ["no runner"]

    settle(Host.task_runner)

    assert shown == ["no runner", "after job"]
