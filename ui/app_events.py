from __future__ import annotations

from PySide6.QtCore import QObject, Signal


class AppEvents(QObject):
    costs_visibility_changed = Signal(bool)
    language_changed = Signal(str)
    catalog_changed = Signal()


app_events = AppEvents()
