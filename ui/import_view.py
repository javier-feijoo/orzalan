from __future__ import annotations

from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from ui.import_wizard import ImportWizard
from ui.i18n import t, tu
from ui.app_events import app_events


class ImportView(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)
        self.title = QLabel(tu("import_title"))
        self.title.setObjectName("PageTitle")
        self.title.setVisible(False)
        self.title.setFixedHeight(0)
        layout.addWidget(self.title)

        self.btn_open = QPushButton(tu("open_import_wizard"))
        self.btn_open.clicked.connect(self._open_wizard)
        layout.addWidget(self.btn_open)
        layout.addStretch(1)
        app_events.language_changed.connect(self._reload_texts)

    def _reload_texts(self, _lang: str) -> None:
        self.title.setText(tu("import_title"))
        self.btn_open.setText(tu("open_import_wizard"))

    def _open_wizard(self) -> None:
        dlg = ImportWizard(self)
        dlg.exec()
