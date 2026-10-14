"""Pick items by moving them between an "available" and a "selected" list.

:class:`DualListPicker` only provides the widgets; the code that fills the
lists and reacts to the buttons stays where it is (for Clinical Reporting,
the selection page mixins), because the lists are ordinary ``QListWidget``
objects and the buttons ordinary buttons. The count next to each title
updates by itself.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QListWidget,
    QVBoxLayout,
    QWidget,
)

from cci_ui.icons import IconName
from cci_ui.theme.manager import current, theme_events
from cci_ui.theme.qss import register_qss
from cci_ui.widgets.buttons import icon_button
from cci_ui.widgets.labels import text_label
from cci_ui.widgets.search import SearchField
from cci_ui.widgets.views import PlaceholderListWidget

register_qss(
    """
QLabel[cciRole="countPill"] {
    background: ${fill};
    color: ${text_secondary};
    border-radius: 8px;
    padding: 0 7px;
    font-size: 11px;
    font-weight: 600;
}
QWidget[cciRole="listHeader"] {
    border-bottom: 1px solid ${separator};
}
"""
)


class _ListCard(QFrame):
    """A card holding a title, a live count, and a list."""

    def __init__(self, title: str, placeholder: str):
        super().__init__()
        self.setProperty("cciRole", "card")
        header = QWidget()
        header.setProperty("cciRole", "listHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 8, 12, 8)
        header_layout.addWidget(text_label(title, style="subheadline"))
        header_layout.addStretch(1)
        self.count_label = text_label("0")
        self.count_label.setProperty("cciRole", "countPill")
        header_layout.addWidget(self.count_label)

        self.list = PlaceholderListWidget(placeholder)
        self.list.setProperty("cciRole", "embedded")
        self.list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.list.setAccessibleName(title)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(1, 1, 1, 1)
        layout.setSpacing(0)
        layout.addWidget(header)
        layout.addWidget(self.list, 1)

        model = self.list.model()
        for signal in (model.rowsInserted, model.rowsRemoved, model.modelReset):
            signal.connect(self._update_count)

    def _update_count(self, *_args) -> None:
        self.count_label.setText(str(self.list.count()))


class DualListPicker(QWidget):
    """Search, an available list, move buttons, and a selected list."""

    def __init__(
        self,
        *,
        available_title: str = "Available",
        selected_title: str = "Selected",
        search_placeholder: str = "Search",
        available_placeholder: str = "",
        selected_placeholder: str = "Nothing selected yet",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.search = SearchField(search_placeholder)
        self._available_card = _ListCard(available_title, available_placeholder)
        self._selected_card = _ListCard(selected_title, selected_placeholder)
        #: Items that can be added.
        self.available: QListWidget = self._available_card.list
        #: Items already chosen.
        self.selected: QListWidget = self._selected_card.list

        self.add_button = icon_button(
            IconName.ADD_SELECTED, "Add selected", variant="secondary"
        )
        self.add_all_button = icon_button(
            IconName.ADD_ALL, "Add all shown", variant="secondary"
        )
        self.remove_button = icon_button(
            IconName.REMOVE_SELECTED, "Remove selected", variant="secondary"
        )
        self.remove_all_button = icon_button(
            IconName.REMOVE_ALL, "Remove all shown", variant="secondary"
        )
        buttons = QVBoxLayout()
        buttons.setSpacing(8)
        buttons.addStretch(1)
        for button in (
            self.add_button,
            self.add_all_button,
            self.remove_button,
            self.remove_all_button,
        ):
            buttons.addWidget(button)
        buttons.addStretch(1)

        self._lists = QHBoxLayout()
        self._lists.addWidget(self._available_card, 1)
        self._lists.addLayout(buttons)
        self._lists.addWidget(self._selected_card, 1)

        self.hint_label = text_label(
            "Double-click an item to move it. Ctrl-click to select several.",
            style="caption",
        )
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.addWidget(self.search)
        self._layout.addLayout(self._lists, 1)
        self._layout.addWidget(self.hint_label, 0, Qt.AlignmentFlag.AlignLeft)

        theme_events().changed.connect(self._apply_metrics)
        self._apply_metrics()

    def _apply_metrics(self) -> None:
        gap = current().metrics.pair_gap
        self._lists.setSpacing(gap)
        self._layout.setSpacing(gap)

    def available_count(self) -> int:
        return int(self._available_card.count_label.text())

    def selected_count(self) -> int:
        return int(self._selected_card.count_label.text())


__all__ = ["DualListPicker"]
