"""Silent, best-effort reporting of successful UI exports.

The run counter is deliberately isolated from the reporting workflow.  It is
disabled unless both environment variables below are configured, performs its
request on a daemon thread, and suppresses every delivery error.
"""

from __future__ import annotations

import json
import os
import threading
import uuid
from urllib.request import Request, urlopen

RUN_COUNTER_URL_ENV = "CLINICAL_REPORTING_RUN_COUNTER_URL"
RUN_COUNTER_TOKEN_ENV = "CLINICAL_REPORTING_RUN_COUNTER_TOKEN"
_REQUEST_TIMEOUT_SECONDS = 2.0


def record_successful_export() -> None:
    """Queue one run-count event without blocking or notifying the user.

    Telemetry is opt-in through environment configuration.  This function is
    intentionally fail-closed and best-effort: configuration, thread creation,
    networking, and server failures never escape into the application.
    """

    try:
        endpoint = os.environ.get(RUN_COUNTER_URL_ENV, "").strip()
        token = os.environ.get(RUN_COUNTER_TOKEN_ENV, "").strip()
        if not endpoint or not token:
            return

        event_id = str(uuid.uuid4())
        worker = threading.Thread(
            target=_post_run,
            args=(endpoint, token, event_id),
            name="run-counter",
            daemon=True,
        )
        worker.start()
    except Exception:  # The run counter must never affect report export.
        return


def _post_run(endpoint: str, token: str, event_id: str) -> None:
    """Send one run-count event, silently discarding every outcome."""

    try:
        payload = json.dumps({"event_id": event_id}).encode("utf-8")
        request = Request(
            endpoint,
            data=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urlopen(request, timeout=_REQUEST_TIMEOUT_SECONDS) as response:
            # Complete the exchange so the connection can be released.  The
            # response content is intentionally ignored.
            response.read()
    except Exception:  # Network and HTTP failures are intentionally silent.
        return


__all__ = ["record_successful_export"]
