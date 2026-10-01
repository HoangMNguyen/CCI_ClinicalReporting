"""Status messages tagged with how serious they are.

A :class:`Message` is a plain ``str``, so code that compares, joins, or
prefix-checks message text keeps working. It also carries a ``kind``
(``info``, ``success``, ``warning`` or ``error``) and optional ``details``
such as a traceback, so any front end (the desktop app today, a web page
later) can style it without parsing the text.
"""

from __future__ import annotations

from typing import Optional

KINDS = ("info", "success", "warning", "error")


class Message(str):
    """A status message string with a ``kind`` and optional ``details``."""

    kind: str
    details: Optional[str]

    def __new__(
        cls, text: str, kind: str = "info", details: Optional[str] = None
    ) -> Message:
        if kind not in KINDS:
            raise ValueError(f"Unknown message kind {kind!r}; expected one of {KINDS}")
        message = super().__new__(cls, text)
        message.kind = kind
        message.details = details
        return message

    def __repr__(self) -> str:
        return f"Message({str(self)!r}, kind={self.kind!r})"

    def __reduce__(self):
        return (Message, (str(self), self.kind, self.details))


def info(text: str, details: Optional[str] = None) -> Message:
    """Neutral progress or status text."""
    return Message(text, "info", details)


def success(text: str, details: Optional[str] = None) -> Message:
    """An action finished as the user intended."""
    return Message(text, "success", details)


def warning(text: str, details: Optional[str] = None) -> Message:
    """The action finished, or can't start yet, and the user should look."""
    return Message(text, "warning", details)


def error(text: str, details: Optional[str] = None) -> Message:
    """The action failed."""
    return Message(text, "error", details)


def kind_of(text: Optional[str]) -> str:
    """Return the kind of *text*; plain strings count as ``info``."""
    return getattr(text, "kind", "info")


def one_line(text: str) -> str:
    """*text* for a one-line status: lines joined, their "- " bullets dropped.

    (Lists of problems, such as "Cannot run:" messages, put one per line.)
    A line that doesn't end in punctuation gets a full stop before the next.
    """
    lines = [line.strip().removeprefix("- ") for line in text.splitlines()]
    lines = [line for line in lines if line]
    ended = [line if line[-1] in ".:;!?…" else f"{line}." for line in lines[:-1]]
    return " ".join(ended + lines[-1:])


__all__ = [
    "KINDS",
    "Message",
    "error",
    "info",
    "kind_of",
    "one_line",
    "success",
    "warning",
]
