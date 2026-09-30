"""Stand-ins for widgets, shared by tests that drive the mixins without Qt."""


class FakePathPicker:
    """Like ``cci_ui.widgets.path_picker.PathPicker``: shows one path."""

    def __init__(self, path: str = ""):
        self._path = path

    def set_path(self, path) -> None:
        self._path = path or ""

    def path(self) -> str:
        return self._path
