"""Stand-ins for widgets and data tables, shared by tests that don't need real ones."""


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


class FakeCheckBox:
    """Like a ``QCheckBox``: checked or not."""

    def __init__(self, checked: bool):
        self._checked = checked

    def isChecked(self) -> bool:  # noqa: N802 (Qt naming)
        return self._checked


class FakeTableView:
    """Like a ``QTableView``: keeps the model it is given (one to start with)."""

    def __init__(self):
        self._model = object()

    def setModel(self, model) -> None:  # noqa: N802 (Qt naming)
        self._model = model

    def model(self):
        return self._model


class DummyTable:
    """Like a ``DataFrame`` during form setup: only its columns."""

    def __init__(self, columns):
        self.columns = columns
