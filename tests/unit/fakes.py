"""Stand-ins for widgets, shared by tests that drive the mixins without Qt."""


class FakePathPicker:
    """Like ``cci_ui.widgets.path_picker.PathPicker``: shows one path."""

    def __init__(self, path: str = ""):
        self._path = path

    def set_path(self, path) -> None:
        self._path = path or ""

    def path(self) -> str:
        return self._path


class FakeSection:
    """Like ``cci_ui.widgets.section.Section``: keeps its footnote."""

    def __init__(self):
        self.footnote = ""

    def set_footnote(self, text: str) -> None:
        self.footnote = text


class FakeBanner:
    """Like ``cci_ui.widgets.status.StatusBanner``: keeps the message shown."""

    def __init__(self):
        self.value = ""

    def setText(self, text) -> None:  # noqa: N802 (Qt naming)
        self.value = text or ""

    def text(self) -> str:
        return self.value

    def kind(self) -> str:
        return getattr(self.value, "kind", "info")


class FakeTableView:
    """Like a ``QTableView``: keeps the model it is given (one to start with)."""

    def __init__(self):
        self._model = object()

    def setModel(self, model) -> None:  # noqa: N802 (Qt naming)
        self._model = model

    def model(self):
        return self._model
