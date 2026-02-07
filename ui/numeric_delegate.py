from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QStyledItemDelegate


class NumericAlignDelegate(QStyledItemDelegate):
    """Align numeric-looking values to the right."""

    def initStyleOption(self, option, index) -> None:
        super().initStyleOption(option, index)
        if index.data() is None:
            return
        text = str(index.data()).strip()
        if not text:
            return
        candidate = text.replace(".", "").replace(",", "").replace("%", "")
        if candidate.isdigit():
            option.displayAlignment = Qt.AlignRight | Qt.AlignVCenter
