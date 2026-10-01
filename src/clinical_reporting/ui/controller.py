"""Small adapter for composing legacy UI behaviors without mixin inheritance."""

from __future__ import annotations

from types import MethodType
from typing import Iterable
from weakref import ref


def compose_behaviors(*behaviors: type):
    """Copy behavior descriptors onto a concrete Qt class.

    This is intentionally a transition helper: it preserves the exact slots
    Qt signals currently target without placing behavior classes in the
    window's inheritance hierarchy.
    """

    def decorate(window_type: type) -> type:
        for behavior in behaviors:
            for name, descriptor in behavior.__dict__.items():
                if name.startswith("__") or hasattr(window_type, name):
                    continue
                setattr(window_type, name, descriptor)
        return window_type

    return decorate


class FeatureController:
    """Bind methods from cohesive behavior classes to one main window.

    The existing page behavior methods intentionally continue to run with the
    window as ``self`` during the migration.  That preserves shared state and
    signal wiring while removing the fragile ten-class inheritance chain.
    """

    def __init__(self, window, *behaviors: type):
        self._window_ref = ref(window)
        self.behaviors = behaviors

    def method_names(self) -> Iterable[str]:
        for behavior in self.behaviors:
            yield from behavior.__dict__

    def resolve(self, name: str):
        """Return a behavior attribute bound to the controller's window."""
        window = self._window_ref()
        if window is None:
            raise AttributeError(name)
        for behavior in self.behaviors:
            if name not in behavior.__dict__:
                continue
            descriptor = behavior.__dict__[name]
            if isinstance(descriptor, staticmethod):
                return descriptor.__get__(None, behavior)
            if isinstance(descriptor, classmethod):
                return descriptor.__get__(behavior, behavior)
            if callable(descriptor):
                return MethodType(descriptor, window)
            return descriptor
        raise AttributeError(name)

    def contains(self, name: str) -> bool:
        return any(name in behavior.__dict__ for behavior in self.behaviors)

    def call(self, name: str, *args, **kwargs):
        """Invoke one behavior method against the owned main window."""
        return self.resolve(name)(*args, **kwargs)
