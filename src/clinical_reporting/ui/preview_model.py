"""Qt table model used to bind pandas DataFrames to preview views."""

from __future__ import annotations

from datetime import datetime

import numpy as np
import pandas as pd
from PySide6.QtCore import QAbstractTableModel, Qt


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
            value = self._data.iloc[index.row(), index.column()]
            if pd.isna(value):
                return ""
            if isinstance(value, (pd.Timestamp, datetime, np.datetime64)):
                date = pd.Timestamp(value)
                return f"{date.month}/{date.day}/{date.year}"
            if isinstance(value, (float, np.floating)) and value == int(value):
                return str(int(value))
            return str(value)
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):  # noqa: N802
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return str(self._data.columns[section])
        if orientation == Qt.Vertical:
            return str(section + 1)
        return None
