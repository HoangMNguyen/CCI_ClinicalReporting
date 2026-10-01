"""Qt table model used to bind pandas DataFrames to preview views."""

from __future__ import annotations

from datetime import datetime

import numpy as np
import pandas as pd
from PySide6.QtCore import QAbstractTableModel, Qt

#: Values (and column names) at least this long also show whole in a
#: tooltip: the grid may shorten them (see ``cci_ui.widgets.views.COLUMN_MAX_W``).
TOOLTIP_FROM_LENGTH = 30


class ReportPreviewModel(QAbstractTableModel):
    """Qt model that exposes a pandas DataFrame to a :class:`QTableView`."""

    def __init__(self, data: pd.DataFrame):
        super().__init__()
        self._data = data

    def rowCount(self, parent=None):  # noqa: N802 (Qt naming convention)
        return len(self._data)

    def columnCount(self, parent=None):  # noqa: N802
        return len(self._data.columns)

    def data(self, index, role=Qt.DisplayRole):  # noqa: N802
        if not index.isValid():
            return None
        if role == Qt.DisplayRole:
            return self._text(index)
        if role == Qt.ToolTipRole:
            text = self._text(index)
            return text if len(text) >= TOOLTIP_FROM_LENGTH else None
        return None

    def _text(self, index) -> str:
        value = self._data.iloc[index.row(), index.column()]
        if pd.isna(value):
            return ""
        if isinstance(value, (pd.Timestamp, datetime, np.datetime64)):
            date = pd.Timestamp(value)
            return f"{date.month}/{date.day}/{date.year}"
        if (
            isinstance(value, (float, np.floating))
            and np.isfinite(value)
            and value == int(value)
        ):
            return str(int(value))
        return str(value)

    def headerData(self, section, orientation, role=Qt.DisplayRole):  # noqa: N802
        if orientation == Qt.Horizontal and role == Qt.ToolTipRole:
            name = str(self._data.columns[section])
            return name if len(name) >= TOOLTIP_FROM_LENGTH else None
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return str(self._data.columns[section])
        if orientation == Qt.Vertical:
            return str(section + 1)
        return None
