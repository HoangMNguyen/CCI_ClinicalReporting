"""Text labels in the type scale, and labels that keep long paths in bounds.

:class:`ElidedLabel` shortens a path in the middle to fit one line;
:class:`WrappingLabel` wraps it over several lines, for messages that show
it in full.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Callable, Optional, Sequence

from PySide6.QtCore import QEvent, QSize, Qt
from PySide6.QtGui import QFontMetricsF, QKeySequence, QPainter
from PySide6.QtWidgets import QApplication, QLabel, QMenu, QSizePolicy, QWidget

from cci_ui.icons import icon
from cci_ui.theme.manager import repolish
from cci_ui.theme.tokens import TYPE_SCALE

#: An invisible place where word wrap may break a line.
BREAK_CHANCE = "\N{ZERO WIDTH SPACE}"
#: Path separators and name punctuation; a long word breaks after a run of them.
_SEPARATORS = frozenset("\\/_.-")
#: A line never starts with closing punctuation or ends with opening punctuation.
_CLOSING = frozenset(
    ",;:!?)]}'\"\N{RIGHT SINGLE QUOTATION MARK}\N{RIGHT DOUBLE QUOTATION MARK}"
)
_OPENING = frozenset(
    "([{'\"\N{LEFT SINGLE QUOTATION MARK}\N{LEFT DOUBLE QUOTATION MARK}"
)
_JOINER = "\N{ZERO WIDTH JOINER}"
#: What word wrap keeps together: no-break spaces (pasted from Word, say) join.
_WORD = re.compile(
    r"(?:\S|[\N{NO-BREAK SPACE}\N{FIGURE SPACE}\N{NARROW NO-BREAK SPACE}])+"
)

#: Says whether a piece of text fits on one line.
Fits = Callable[[str], bool]


def _may_break(word: str, i: int) -> bool:
    """Whether a line may break between ``word[i - 1]`` and ``word[i]`` at all."""
    before, after = word[i - 1], word[i]
    return not (
        after in _CLOSING
        or before in _OPENING
        or _JOINER in (before, after)
        or after == "\N{VARIATION SELECTOR-16}"
        or unicodedata.category(after).startswith("M")  # An accent, say.
    )


def _after_separators(word: str, i: int) -> bool:
    before, after = word[i - 1], word[i]
    # After a run (``\\server``) but not inside a date or a number (2026-09-29).
    return (
        before in _SEPARATORS
        and after not in _SEPARATORS
        and not (before in "-." and after.isdigit())
    )


def _between_words(word: str, i: int) -> bool:
    before, after = word[i - 1], word[i]
    # camelCase, and where letters meet digits (DEMO01).
    return (
        (before.islower() and after.isupper())
        or (before.isalpha() and after.isdigit())
        or (before.isdigit() and after.isalpha())
    )


def _anywhere(word: str, i: int) -> bool:
    return True


#: Where a word too wide for a line breaks, tried in turn on each piece that
#: still doesn't fit.
_RULES = (_after_separators, _between_words, _anywhere)


def _break_word(
    word: str, fits: Fits, rules: Sequence[Callable[[str, int], bool]] = _RULES
) -> str:
    if not rules or fits(word):
        return word
    rule, later = rules[0], rules[1:]
    cuts = [i for i in range(1, len(word)) if rule(word, i) and _may_break(word, i)]
    pieces = [word[a:b] for a, b in zip([0, *cuts], [*cuts, len(word)])]
    return BREAK_CHANCE.join(_break_word(piece, fits, later) for piece in pieces)


def add_break_chances(text: str, fits: Fits) -> str:
    """*text* with :data:`BREAK_CHANCE` inside each word that doesn't *fit*.

    Word wrap breaks at spaces, ``-`` and ``/``, but not after ``\\``, ``_``
    or ``.``, so a Windows path or a long name would make a wrapped label as
    wide as the whole of it. A word too wide for a line may break after a
    ``\\ / _ . -`` (but not inside a date such as 2026-09-29); a piece still
    too wide, where a camelCase name's words or letters and digits meet; and
    a piece still too wide, anywhere. Words that fit get none, so they move to
    the next line whole.
    """
    return _WORD.sub(lambda match: _break_word(match.group(), fits), text)


def text_label(
    text: str = "",
    *,
    style: str = "body",
    tone: Optional[str] = None,
    wrap: bool = False,
    break_long_words: bool = False,
    selectable: bool = False,
    parent: Optional[QWidget] = None,
) -> QLabel:
    """A label in a :data:`~cci_ui.theme.tokens.TYPE_SCALE` style.

    *tone* (``"secondary"`` or ``"tertiary"``) recolors any style.
    *break_long_words* makes it a :class:`WrappingLabel` (always wrapped), for
    text that may hold a long path or a typed name.
    """
    if style not in TYPE_SCALE:
        raise ValueError(
            f"Unknown text style {style!r}; expected one of {list(TYPE_SCALE)}"
        )
    label = WrappingLabel(text, parent) if break_long_words else QLabel(text, parent)
    label.setProperty("textStyle", style)
    if tone:
        label.setProperty("tone", tone)
    label.setWordWrap(wrap or break_long_words)
    if selectable:
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    return label


def section_label(text: str) -> QLabel:
    """The small label above a group of widgets, as over a Section's card."""
    label = text_label(text, style="subheadline")
    label.setContentsMargins(4, 0, 0, 0)
    return label


def escape_ampersands(text: str) -> str:
    """*text* for a button or tab, where a lone "&" marks a keyboard shortcut."""
    return text.replace("&", "&&")


class ElidedLabel(QLabel):
    """Shows text that doesn't fit shortened in the middle, e.g. ``C:\\Users\\…\\data.zip``.

    :meth:`text` returns the full text and the tooltip shows it whenever it is
    shortened, so code that reads the label back is unaffected. Text is shown
    in *tone* (``None`` for the normal color); when empty, the placeholder is
    shown in the tertiary color.
    """

    def __init__(
        self,
        text: str = "",
        parent: Optional[QWidget] = None,
        *,
        placeholder: str = "",
        tone: Optional[str] = None,
        mode: Qt.TextElideMode = Qt.TextElideMode.ElideMiddle,
    ) -> None:
        super().__init__(parent)
        self._full_text = ""
        self._placeholder = placeholder
        self._tone = tone
        self._mode = mode
        # Paths can contain characters that look like markup.
        self.setTextFormat(Qt.TextFormat.PlainText)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setText(text)

    def text(self) -> str:  # Full text, not the shortened one on screen.
        return self._full_text

    def setText(self, text: Optional[str]) -> None:  # noqa: N802 (Qt API)
        self._full_text = text or ""
        tone = self._tone if self._full_text else "tertiary"
        if self.property("tone") != tone:
            self.setProperty("tone", tone)
            repolish(self)
        self._refresh()

    def placeholderText(self) -> str:  # noqa: N802 (Qt naming)
        return self._placeholder

    def setPlaceholderText(self, text: str) -> None:  # noqa: N802 (Qt naming)
        self._placeholder = text
        self._refresh()

    def minimumSizeHint(self) -> QSize:  # noqa: N802 (Qt override)
        return QSize(0, super().minimumSizeHint().height())

    def sizeHint(self) -> QSize:  # noqa: N802 (Qt override)
        shown = self._full_text or self._placeholder
        margins = self.contentsMargins()
        width = (
            self.fontMetrics().horizontalAdvance(shown)
            + margins.left()
            + margins.right()
        )
        return QSize(width, super().sizeHint().height())

    def resizeEvent(self, event) -> None:  # noqa: N802 (Qt override)
        super().resizeEvent(event)
        self._refresh()

    def changeEvent(self, event) -> None:  # noqa: N802 (Qt override)
        super().changeEvent(event)
        if event.type() in (QEvent.Type.FontChange, QEvent.Type.StyleChange):
            self._refresh()

    def _refresh(self) -> None:
        shown = self._full_text or self._placeholder
        width = self.contentsRect().width()
        elided = (
            self.fontMetrics().elidedText(shown, self._mode, width)
            if width > 0
            else shown
        )
        super().setText(elided)
        self.setToolTip(self._full_text if elided != self._full_text else "")
        # Screen readers get the whole text, not the shortened one.
        self.setAccessibleName(self._full_text or self._placeholder)
        self.updateGeometry()


class WrappingLabel(QLabel):
    """A word-wrapped label that also wraps long paths and names.

    It wraps like CSS ``overflow-wrap: anywhere``: a word that fits on a
    line moves to the next line whole, and only a word too wide for the label
    gets break chances (:func:`add_break_chances`, redone when the width or
    font changes). So it never needs to be wider than its container, however
    long a path is. :meth:`text` returns the text as set, and copying a
    selection (Ctrl+C or the context menu) leaves the break chances out, so a
    copied path still works; dragging selected text out, which would carry
    them along, starts a new selection instead.
    """

    def __init__(self, text: str = "", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._full_text = ""
        # Paths can contain characters that look like markup.
        self.setTextFormat(Qt.TextFormat.PlainText)
        self.setWordWrap(True)
        self.setText(text)

    def text(self) -> str:  # The text as set, without the break chances.
        return self._full_text

    def setText(self, text: Optional[str]) -> None:  # noqa: N802 (Qt API)
        self._full_text = text or ""
        # Screen readers get the text as set.
        self.setAccessibleName(self._full_text)
        self._refresh()

    def clear(self) -> None:
        self.setText("")

    def minimumSizeHint(self) -> QSize:  # noqa: N802 (Qt override)
        # Long words wrap to any width, so they don't widen the layout.
        return QSize(0, super().minimumSizeHint().height())

    def resizeEvent(self, event) -> None:  # noqa: N802 (Qt override)
        super().resizeEvent(event)
        if event.size().width() != event.oldSize().width():
            self._refresh()

    def changeEvent(self, event) -> None:  # noqa: N802 (Qt override)
        super().changeEvent(event)
        if event.type() in (QEvent.Type.FontChange, QEvent.Type.StyleChange):
            self._refresh()

    def _refresh(self) -> None:
        width = self.contentsRect().width() - 2 * self.margin()
        metrics = QFontMetricsF(self.font())
        shown = add_break_chances(
            self._full_text, lambda word: metrics.horizontalAdvance(word) < width
        )
        if shown != QLabel.text(self):
            super().setText(shown)

    # ------------------------------------------------------------------
    # Copying without the break chances

    def _selectable(self) -> bool:
        return bool(
            self.textInteractionFlags()
            & (
                Qt.TextInteractionFlag.TextSelectableByMouse
                | Qt.TextInteractionFlag.TextSelectableByKeyboard
            )
        )

    def _copy_selection(self) -> None:
        """Put the selected text on the clipboard, without the break chances."""
        if self.hasSelectedText():
            QApplication.clipboard().setText(
                self.selectedText().replace(BREAK_CHANCE, "")
            )

    def keyPressEvent(self, event) -> None:  # noqa: N802 (Qt override)
        if event.matches(QKeySequence.StandardKey.Copy) and self.hasSelectedText():
            self._copy_selection()
            event.accept()
            return
        super().keyPressEvent(event)

    def mousePressEvent(self, event) -> None:  # noqa: N802 (Qt override)
        # Pressing on the selection and moving would drag it out, break
        # chances and all; start a new selection instead (Shift still extends).
        shift = event.modifiers() & Qt.KeyboardModifier.ShiftModifier
        if event.button() == Qt.MouseButton.LeftButton and not shift:
            self.setSelection(0, 0)
        super().mousePressEvent(event)

    def contextMenuEvent(self, event) -> None:  # noqa: N802 (Qt override)
        if not self._selectable():
            super().contextMenuEvent(event)
            return
        # QLabel's own menu would copy the break chances too.
        menu = self._context_menu()
        menu.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        menu.popup(event.globalPos())
        event.accept()

    def _context_menu(self) -> QMenu:
        """The menu a right-click shows on selectable text: Copy, Select All."""
        menu = QMenu(self)
        copy = menu.addAction("Copy", self._copy_selection)
        copy.setShortcut(QKeySequence.StandardKey.Copy)
        copy.setEnabled(self.hasSelectedText())
        # Bound methods, not lambdas: a lambda capturing self keeps the label
        # referenced from its own child menu, so the last reference can drop
        # while the menu is being deleted, inside the label's destructor.
        select_all = menu.addAction("Select All", self._select_all)
        select_all.setShortcut(QKeySequence.StandardKey.SelectAll)
        return menu

    def _select_all(self) -> None:
        shown = QLabel.text(self)
        # Selections count UTF-16 units: an emoji is two.
        self.setSelection(0, len(shown.encode("utf-16-le")) // 2)


class IconLabel(QWidget):
    """A theme-aware icon on its own, e.g. the symbol in a status banner."""

    def __init__(
        self,
        icon_name: str,
        role: str = "secondary",
        size: int = 16,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._size = size
        self.set_icon(icon_name, role)
        self.setFixedSize(size, size)

    def set_icon(self, icon_name: str, role: str = "secondary") -> None:
        self._icon = icon(icon_name, role)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt override)
        painter = QPainter(self)
        self._icon.paint(painter, self.rect())
        painter.end()


__all__ = [
    "BREAK_CHANCE",
    "ElidedLabel",
    "Fits",
    "IconLabel",
    "WrappingLabel",
    "add_break_chances",
    "escape_ampersands",
    "section_label",
    "text_label",
]
