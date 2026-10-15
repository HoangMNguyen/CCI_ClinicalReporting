"""A side panel of help text for the page shown.

:class:`HelpPanel` shows a title and Markdown text (headings, lists, bold)
in a read-only browser, with a close button. :class:`~cci_ui.widgets.shell.AppShell`
puts one beside its pages when the tool gives help text for them.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QTextBrowser, QVBoxLayout, QWidget

from cci_ui.icons import IconName
from cci_ui.theme.qss import register_qss
from cci_ui.widgets.buttons import icon_button
from cci_ui.widgets.labels import text_label

register_qss(
    """
QFrame[cciRole="helpPanel"] {
    background: ${bg_window};
    border: none;
    border-left: 1px solid ${separator};
}
QFrame[cciRole="helpPanel"] QTextBrowser {
    background: transparent;
    border: none;
}
"""
)


class HelpPanel(QFrame):
    """Help for one page: a title, Markdown text, and a close button."""

    #: Emitted when the user clicks the close button.
    closeRequested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setProperty("cciRole", "helpPanel")
        self.title = text_label("", style="headline")
        self.close_button = icon_button(IconName.CLOSE, "Close help")
        self.close_button.clicked.connect(self.closeRequested)
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.addWidget(self.title, 1)
        header.addWidget(self.close_button)
        self.body = QTextBrowser()
        self.body.setReadOnly(True)
        self.body.setOpenLinks(False)
        self.body.setFrameShape(QFrame.Shape.NoFrame)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 8, 12)
        layout.setSpacing(8)
        layout.addLayout(header)
        layout.addWidget(self.body, 1)

    def set_content(self, title: str, markdown: str) -> None:
        """Show *title* and the Markdown *markdown*, from the top."""
        self.title.setText(title)
        self.body.setMarkdown(markdown)
        self.body.verticalScrollBar().setValue(0)


__all__ = ["HelpPanel"]
