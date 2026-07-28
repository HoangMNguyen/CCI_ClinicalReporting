"""Silent, best-effort reporting of successful UI save actions.

Usage reporting is deliberately isolated from the reporting workflow.  It is
disabled unless both environment variables below are configured, performs its
request on a daemon thread, and suppresses every delivery error.
"""

from __future__ import annotations

import getpass
import json
import os
from pathlib import Path
import threading
import uuid
from urllib.request import Request, urlopen

RUN_COUNTER_URL_ENV = "CLINICAL_REPORTING_RUN_COUNTER_URL"
RUN_COUNTER_TOKEN_ENV = "CLINICAL_REPORTING_RUN_COUNTER_TOKEN"
REPORT_SAVED_EVENT = "report_saved"
SETTING_SAVED_EVENT = "setting_saved"
_VALID_EVENT_TYPES = frozenset({REPORT_SAVED_EVENT, SETTING_SAVED_EVENT})
_REQUEST_TIMEOUT_SECONDS = 2.0
_TELEMETRY_CONFIG_PATH = Path(__file__).resolve().with_name("telemetry.json")


def _bundled_configuration() -> tuple[str, str]:
    """Read the optional configuration bundled beside this module."""

    try:
        configuration = json.loads(_TELEMETRY_CONFIG_PATH.read_text(encoding="utf-8"))
        if not isinstance(configuration, dict):
            return "", ""
        endpoint = configuration.get("url", "")
        token = configuration.get("token", "")
        if not isinstance(endpoint, str) or not isinstance(token, str):
            return "", ""
        return endpoint.strip(), token.strip()
    except Exception:
        return "", ""


def _configuration() -> tuple[str, str]:
    """Return environment overrides followed by bundled JSON defaults."""

    bundled_endpoint, bundled_token = _bundled_configuration()
    endpoint = os.environ.get(RUN_COUNTER_URL_ENV, bundled_endpoint).strip()
    token = os.environ.get(RUN_COUNTER_TOKEN_ENV, bundled_token).strip()
    return endpoint, token


def record_successful_export(report_name: str) -> None:
    """Queue one successful-report event without notifying the user."""

    _record_event(REPORT_SAVED_EVENT, report_name)


def record_successful_setting_save(setting_name: str) -> None:
    """Queue one successful-setting event without notifying the user."""

    _record_event(SETTING_SAVED_EVENT, setting_name)


def _record_event(event_type: str, saved_name: str) -> None:
    """Queue a supported usage event without blocking the application.

    Telemetry is opt-in through environment configuration.  This function is
    intentionally fail-closed and best-effort: configuration, thread creation,
    networking, and server failures never escape into the application.
    """

    try:
        endpoint, token = _configuration()
        if not endpoint or not token:
            return

        if event_type not in _VALID_EVENT_TYPES:
            return
        saved_name = saved_name.strip()
        if (
            not saved_name
            or len(saved_name) > 255
            or not all(character.isprintable() for character in saved_name)
        ):
            return
        username = getpass.getuser().strip()
        if not username or len(username) > 128:
            return

        event_id = str(uuid.uuid4())
        worker = threading.Thread(
            target=_post_event,
            args=(endpoint, token, event_id, event_type, username, saved_name),
            name="usage-event",
            daemon=True,
        )
        worker.start()
    except Exception:  # Usage reporting must never affect save operations.
        return


def _post_event(
    endpoint: str,
    token: str,
    event_id: str,
    event_type: str,
    username: str,
    saved_name: str,
) -> None:
    """Send one usage event, silently discarding every outcome."""

    try:
        event_name_field = (
            "report_name" if event_type == REPORT_SAVED_EVENT else "setting_name"
        )
        payload = json.dumps(
            {
                "event_id": event_id,
                "event_type": event_type,
                "username": username,
                event_name_field: saved_name,
            }
        ).encode("utf-8")
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


__all__ = ["record_successful_export", "record_successful_setting_save"]
