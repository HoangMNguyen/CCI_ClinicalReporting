"""Run slow work (reading a ZIP, building a report) without freezing the window.

:class:`TaskRunner` runs one job at a time on a background thread and calls
the success or error callback back on the GUI thread, where it is safe to
change the report and widgets. While a job runs, its
:class:`~cci_ui.widgets.busy.BusyOverlay` blocks the window. A callback may
start the next job (e.g. export after building a preview); the overlay then
stays up between the two.

Rules for the work function: it gets everything it needs as arguments, never
touches widgets, and returns its result instead of changing shared state;
the callbacks apply the result. :func:`run_task` runs the same work directly
when a window has no runner (tests and headless use), with the same
callback contract.

Callbacks run while the window is still blocked, so nothing can interleave
with them. A dialog a callback wants to show should wait until the window
is free: pass it to :meth:`TaskRunner.call_when_idle`.

The overlay drops clicks and keys, but some actions still arrive while a job
runs. One user action can trigger two: a page change makes the date field on
the hidden page commit (starting a reload), then shows the preview page
(asking for a preview). And fields commit when they lose focus to another
app or a dialog. Start these actions with :func:`defer_if_busy`, so they run
once the window is idle instead of being dropped or racing the job: every
action that starts work, anything that fires without a click or key press,
and anything that changes what a running job reads (the input file, say).

Closing a window: call :meth:`TaskRunner.shutdown` once ``closeEvent`` has
accepted the close. The running job's result is ignored and nothing new
starts (a field losing focus as the window hides could otherwise start a
job). The job itself can't be stopped; destroying the runner waits for it
to finish (the thread pool's destructor blocks), so the process may stay
alive, invisibly, until it does.
"""

from __future__ import annotations

import sys
import traceback
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    NamedTuple,
    Optional,
    Tuple,
)

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal

if TYPE_CHECKING:
    # Only for annotations: importing the widgets here would be circular
    # (cci_ui.widgets.workflow_page runs its work through this module).
    from cci_ui.widgets.busy import BusyOverlay

#: Success callback: receives the work function's return value.
SuccessCallback = Callable[[Any], None]
#: Error callback: receives the exception and its formatted traceback.
ErrorCallback = Callable[[BaseException, str], None]


class _JobSignals(QObject):
    # Created on the GUI thread and emitted from the worker thread, so the
    # runner's slots receive them on the GUI thread (queued connections).
    succeeded = Signal(int, object)
    failed = Signal(int, object, str)


class _Job(QRunnable):
    def __init__(
        self,
        job_id: int,
        fn: Callable[..., Any],
        args: Tuple[Any, ...],
        kwargs: Dict[str, Any],
        signals: _JobSignals,
    ) -> None:
        super().__init__()
        self._job_id = job_id
        self._fn = fn
        self._args = args
        self._kwargs = kwargs
        self._signals = signals

    def run(self) -> None:
        try:
            try:
                result = self._fn(*self._args, **self._kwargs)
            except BaseException as exc:  # Even SystemExit must report back, or
                # the window would stay blocked forever.
                self._signals.failed.emit(self._job_id, exc, traceback.format_exc())
            else:
                self._signals.succeeded.emit(self._job_id, result)
        except RuntimeError:
            # The app is exiting and has already deleted the signal object;
            # nobody is waiting for this result.
            pass


class _Pending(NamedTuple):
    signals: _JobSignals
    on_success: SuccessCallback
    on_error: ErrorCallback
    generation: int


class TaskRunner(QObject):
    """Runs one job at a time in the background; callbacks run on the GUI thread."""

    #: Emitted with True when work starts and False once no more work follows.
    busyChanged = Signal(bool)

    def __init__(
        self,
        parent: Optional[QObject] = None,
        *,
        overlay: Optional[BusyOverlay] = None,
    ) -> None:
        super().__init__(parent)
        self._overlay = overlay
        self._pool = QThreadPool(self)
        self._pool.setMaxThreadCount(1)
        self._busy = False  # the overlay is up
        self._running = False  # a job is in flight (its callback hasn't started)
        self._closed = False  # shutdown() was called
        self._generation = 0
        self._next_id = 0
        # Holds each job's signal object until the job reports back; without
        # it the worker thread could free the object mid-emit.
        self._jobs: Dict[int, _Pending] = {}
        self._idle_actions: List[Callable[[], None]] = []

    @property
    def busy(self) -> bool:
        return self._busy

    def submit(
        self,
        fn: Callable[..., Any],
        *args: Any,
        on_success: SuccessCallback,
        on_error: Optional[ErrorCallback] = None,
        message: str = "Working…",
        **kwargs: Any,
    ) -> bool:
        """Start ``fn(*args, **kwargs)``; return False if a job is already running.

        May be called from a callback to chain the next job. Without
        *on_error*, a failure goes to ``sys.excepthook`` (the error dialog in
        the built apps). Returns False after :meth:`shutdown`, too.
        """
        if self._running or self._closed:
            return False
        self._running = True
        job_id = self._next_id
        self._next_id += 1
        signals = _JobSignals()
        signals.succeeded.connect(self._on_succeeded)
        signals.failed.connect(self._on_failed)
        self._jobs[job_id] = _Pending(
            signals, on_success, on_error or _report_error, self._generation
        )
        if self._busy:
            self.set_message(message)
        else:
            self._busy = True
            if self._overlay is not None:
                self._overlay.start(message)
            self.busyChanged.emit(True)
        self._pool.start(_Job(job_id, fn, args, kwargs, signals))
        return True

    def set_message(self, message: str) -> None:
        """Update what the busy overlay says (e.g. "Writing Excel file…")."""
        if self._overlay is not None:
            self._overlay.set_message(message)

    def call_when_idle(self, action: Callable[[], None]) -> None:
        """Call *action* now if idle, otherwise once no more work follows.

        Queued actions run in order. An action equal to one already queued is
        skipped, so a bound method queued twice runs once (a ``partial`` or
        ``lambda`` never equals another). If an action starts a job, the rest
        wait for that job too. Ignored after :meth:`shutdown`.
        """
        if self._closed:
            return
        if not self._busy:
            action()
        elif action not in self._idle_actions:
            self._idle_actions.append(action)

    def discard_results(self) -> None:
        """Ignore whatever the running job returns (e.g. the window is closing).

        Actions waiting in :meth:`call_when_idle` are dropped too.
        """
        self._generation += 1
        self._running = False
        self._idle_actions.clear()
        self._set_idle()

    def shutdown(self) -> None:
        """Stop for good (the window is closing): discard results, start nothing."""
        self._closed = True
        self.discard_results()

    def wait(self, msecs: int = -1) -> bool:
        """Block until the worker is idle (for tests and shutdown)."""
        return self._pool.waitForDone(msecs)

    def _on_succeeded(self, job_id: int, result: Any) -> None:
        self._complete(job_id, lambda pending: pending.on_success(result))

    def _on_failed(self, job_id: int, exc: BaseException, details: str) -> None:
        self._complete(job_id, lambda pending: pending.on_error(exc, details))

    def _complete(self, job_id: int, call: Callable[[_Pending], None]) -> None:
        pending = self._jobs.pop(job_id, None)
        if pending is None:
            return
        pending.signals.deleteLater()
        if pending.generation != self._generation:
            return  # A job the window no longer wants (see discard_results).
        self._running = False
        try:
            # Still busy while the callback updates the report and widgets,
            # so nothing can be clicked half-way through.
            call(pending)
        finally:
            if not self._running:  # The callback didn't chain another job.
                self._set_idle()

    def _set_idle(self) -> None:
        if not self._busy:
            return
        self._busy = False
        if self._overlay is not None:
            self._overlay.stop()
        self.busyChanged.emit(False)
        self._run_idle_actions()

    def _run_idle_actions(self) -> None:
        while self._idle_actions and not self._busy:
            action = self._idle_actions.pop(0)
            try:
                action()
            except Exception as exc:  # One broken action mustn't block the rest.
                _report_error(exc, "")


def _report_error(exc: BaseException, details: str) -> None:
    # The error dialog hook installed by create_app logs it as well.
    sys.excepthook(type(exc), exc, exc.__traceback__)


def defer_if_busy(host: object, action: Callable[[], None]) -> bool:
    """If ``host.task_runner`` is busy, queue *action* for when it's idle.

    Returns True when *action* was queued, so the caller should stop; False
    when there's no runner or it's idle, so the caller carries on now::

        def preview_report(self):
            if defer_if_busy(self, self.preview_report):
                return
            ...
    """
    runner: Optional[TaskRunner] = getattr(host, "task_runner", None)
    if runner is None or not runner.busy:
        return False
    runner.call_when_idle(action)
    return True


def run_task(
    host: object,
    fn: Callable[..., Any],
    *args: Any,
    on_success: SuccessCallback,
    on_error: Optional[ErrorCallback] = None,
    message: str = "Working…",
    **kwargs: Any,
) -> bool:
    """Run *fn* on ``host.task_runner``, or right away if *host* has none.

    With a runner the callbacks run later, on the GUI thread; without one
    they run before this returns, which is what tests and headless code
    expect. Either way *on_success* gets the result and *on_error* the
    exception and traceback; without a runner and without *on_error*, the
    exception propagates. Returns False only if the runner was busy or shut
    down.
    """
    runner: Optional[TaskRunner] = getattr(host, "task_runner", None)
    if runner is not None:
        return runner.submit(
            fn,
            *args,
            on_success=on_success,
            on_error=on_error,
            message=message,
            **kwargs,
        )
    try:
        result = fn(*args, **kwargs)
    except Exception as exc:
        if on_error is None:
            raise
        on_error(exc, traceback.format_exc())
        return True
    on_success(result)
    return True


__all__ = [
    "ErrorCallback",
    "SuccessCallback",
    "TaskRunner",
    "defer_if_busy",
    "run_task",
]
