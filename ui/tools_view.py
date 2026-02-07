from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget, QMessageBox, QFileDialog, QHBoxLayout

from paths import get_portable_dir
from services.catalog_export import export_catalog_template_csv, export_catalog_template_xlsx
from services.categories_io import export_categories_csv, export_categories_xlsx, import_categories
from services.catalog_reset import reset_catalog, reset_all
from ui.import_wizard import ImportWizard
from ui.i18n import t, tu
from ui.app_events import app_events


class ToolsView(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        self.title = QLabel(tu("tools_title"))
        self.title.setObjectName("PageTitle")
        self.title.setVisible(False)
        self.title.setFixedHeight(0)
        layout.addWidget(self.title)

        row1 = QHBoxLayout()
        self.btn_import_catalog = QPushButton(tu("import_catalog"))
        self.btn_import_catalog.clicked.connect(self._open_import_wizard)
        self.btn_export_catalog = QPushButton(tu("export_catalog"))
        self.btn_export_catalog.clicked.connect(self._export_catalog)
        row1.addWidget(self.btn_import_catalog)
        row1.addWidget(self.btn_export_catalog)
        row1.addStretch(1)
        layout.addLayout(row1)

        row2 = QHBoxLayout()
        self.btn_export_cats = QPushButton(tu("export_categories"))
        self.btn_export_cats.clicked.connect(self._export_categories)
        self.btn_import_cats = QPushButton(tu("import_categories"))
        self.btn_import_cats.clicked.connect(self._import_categories)
        row2.addWidget(self.btn_export_cats)
        row2.addWidget(self.btn_import_cats)
        row2.addStretch(1)
        layout.addLayout(row2)

        row3 = QHBoxLayout()
        self.btn_reset_base = QPushButton(tu("reset_catalog_base"))
        self.btn_reset_base.clicked.connect(self._reset_catalog_base)
        self.btn_reset_empty = QPushButton(tu("reset_catalog_empty"))
        self.btn_reset_empty.clicked.connect(self._reset_catalog_empty)
        row3.addWidget(self.btn_reset_base)
        row3.addWidget(self.btn_reset_empty)
        row3.addStretch(1)
        layout.addLayout(row3)

        row4 = QHBoxLayout()
        self.btn_reset_all_base = QPushButton(tu("reset_all_base"))
        self.btn_reset_all_base.clicked.connect(self._reset_all_base)
        self.btn_reset_all_empty = QPushButton(tu("reset_all_empty"))
        self.btn_reset_all_empty.clicked.connect(self._reset_all_empty)
        row4.addWidget(self.btn_reset_all_base)
        row4.addWidget(self.btn_reset_all_empty)
        row4.addStretch(1)
        layout.addLayout(row4)

        layout.addStretch(1)
        app_events.language_changed.connect(self._reload_texts)

    def _reload_texts(self, _lang: str) -> None:
        self.title.setText(tu("tools_title"))
        self.btn_import_catalog.setText(tu("import_catalog"))
        self.btn_export_catalog.setText(tu("export_catalog"))
        self.btn_export_cats.setText(tu("export_categories"))
        self.btn_import_cats.setText(tu("import_categories"))
        self.btn_reset_base.setText(tu("reset_catalog_base"))
        self.btn_reset_empty.setText(tu("reset_catalog_empty"))
        self.btn_reset_all_base.setText(tu("reset_all_base"))
        self.btn_reset_all_empty.setText(tu("reset_all_empty"))

    def _open_import_wizard(self) -> None:
        dlg = ImportWizard(self)
        dlg.exec()

    def _export_catalog(self) -> None:
        base = get_portable_dir("exports")
        path, _ = QFileDialog.getSaveFileName(
            self,
            t("export_catalog"),
            str(base / "catalogo_template.xlsx"),
            "Excel (*.xlsx);;CSV (*.csv)",
        )
        if not path:
            return
        p = Path(path)
        if p.suffix.lower() == ".csv":
            export_catalog_template_csv(p, include_data=True)
        else:
            if p.suffix.lower() != ".xlsx":
                p = p.with_suffix(".xlsx")
            export_catalog_template_xlsx(p, include_data=True)
        QMessageBox.information(self, t("export"), f"{t('catalog_exported')}: {p}")

    def _export_categories(self) -> None:
        base = get_portable_dir("exports")
        path, _ = QFileDialog.getSaveFileName(
            self,
            t("export_categories"),
            str(base / "categorias.xlsx"),
            "Excel (*.xlsx);;CSV (*.csv)",
        )
        if not path:
            return
        p = Path(path)
        if p.suffix.lower() == ".csv":
            export_categories_csv(p)
        else:
            if p.suffix.lower() != ".xlsx":
                p = p.with_suffix(".xlsx")
            export_categories_xlsx(p)
        QMessageBox.information(self, t("export"), f"{t('categories_exported')}: {p}")

    def _import_categories(self) -> None:
        base = get_portable_dir("imports")
        path, _ = QFileDialog.getOpenFileName(
            self,
            t("import_categories"),
            str(base),
            "Excel (*.xlsx);;CSV (*.csv)",
        )
        if not path:
            return
        inserted, skipped = import_categories(Path(path))
        QMessageBox.information(
            self,
            t("import_categories"),
            f"{t('imported')}: {inserted} | {t('rejected_count')}: {skipped}",
        )

    def _reset_catalog_base(self) -> None:
        if QMessageBox.question(
            self,
            t("confirm"),
            t("reset_catalog_base_confirm"),
            QMessageBox.Yes | QMessageBox.No,
        ) != QMessageBox.Yes:
            return
        products, categories = reset_catalog(use_base=True)
        app_events.catalog_changed.emit()
        QMessageBox.information(
            self,
            t("tools_title"),
            f"{t('reset_done')} {t('products')}: {products} | {t('categories')}: {categories}",
        )

    def _reset_catalog_empty(self) -> None:
        if QMessageBox.question(
            self,
            t("confirm"),
            t("reset_catalog_empty_confirm"),
            QMessageBox.Yes | QMessageBox.No,
        ) != QMessageBox.Yes:
            return
        products, categories = reset_catalog(use_base=False)
        app_events.catalog_changed.emit()
        QMessageBox.information(
            self,
            t("tools_title"),
            f"{t('reset_done')} {t('products')}: {products} | {t('categories')}: {categories}",
        )

    def _reset_all_base(self) -> None:
        if QMessageBox.question(
            self,
            t("confirm"),
            t("reset_all_base_confirm"),
            QMessageBox.Yes | QMessageBox.No,
        ) != QMessageBox.Yes:
            return
        products, categories, clients, quotes = reset_all(use_base=True)
        app_events.catalog_changed.emit()
        QMessageBox.information(
            self,
            t("tools_title"),
            f"{t('reset_done')} {t('products')}: {products} | {t('categories')}: {categories} | {t('clients')}: {clients} | {t('quotes')}: {quotes}",
        )

    def _reset_all_empty(self) -> None:
        if QMessageBox.question(
            self,
            t("confirm"),
            t("reset_all_empty_confirm"),
            QMessageBox.Yes | QMessageBox.No,
        ) != QMessageBox.Yes:
            return
        products, categories, clients, quotes = reset_all(use_base=False)
        app_events.catalog_changed.emit()
        QMessageBox.information(
            self,
            t("tools_title"),
            f"{t('reset_done')} {t('products')}: {products} | {t('categories')}: {categories} | {t('clients')}: {clients} | {t('quotes')}: {quotes}",
        )
