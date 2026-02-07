from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QLabel, QMessageBox, QPushButton, QVBoxLayout, QWidget

from paths import get_portable_dir
from services.backups import create_backup, restore_backup
from ui.i18n import t, tu
from ui.app_events import app_events


class BackupsView(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)
        self.title = QLabel(tu("backup_title"))
        self.title.setObjectName("PageTitle")
        self.title.setVisible(False)
        self.title.setFixedHeight(0)
        layout.addWidget(self.title)

        row = QHBoxLayout()
        self.btn_create = QPushButton(tu("create_backup"))
        self.btn_restore = QPushButton(tu("restore_backup"))
        self.btn_open = QPushButton(tu("open_backups"))
        self.btn_create.clicked.connect(self._create_backup)
        self.btn_restore.clicked.connect(self._restore_backup)
        self.btn_open.clicked.connect(self._open_folder)
        row.addWidget(self.btn_create)
        row.addWidget(self.btn_restore)
        row.addWidget(self.btn_open)
        row.addStretch(1)
        layout.addLayout(row)
        layout.addStretch(1)
        app_events.language_changed.connect(self._reload_texts)

    def _reload_texts(self, _lang: str) -> None:
        self.title.setText(tu("backup_title"))
        self.btn_create.setText(tu("create_backup"))
        self.btn_restore.setText(tu("restore_backup"))
        self.btn_open.setText(tu("open_backups"))

    def _create_backup(self) -> None:
        path = create_backup()
        QMessageBox.information(self, t("backup_title"), f"{t('backup_created')}: {path}")

    def _restore_backup(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, t("backup_title"), str(get_portable_dir("backups")), "ZIP (*.zip)"
        )
        if not path:
            return
        confirm = QMessageBox.question(
            self,
            t("confirm"),
            t("restore_confirm"),
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return
        restore_backup(Path(path))
        QMessageBox.information(self, t("backup_title"), t("backup_restored"))

    def _open_folder(self) -> None:
        folder = get_portable_dir("backups")
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))
