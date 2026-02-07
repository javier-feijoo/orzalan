from __future__ import annotations

import shutil
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from paths import get_portable_dir
from settings import Settings
from ui.app_events import app_events
from ui.i18n import t, tu


class CompanySettingsView(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._settings = Settings.load()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll)

        content = QWidget()
        scroll.setWidget(content)

        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        self.title = QLabel(tu("company"))
        self.title.setObjectName("PageTitle")
        self.title.setVisible(False)
        self.title.setFixedHeight(0)
        layout.addWidget(self.title)

        layout.addWidget(self._build_company_form())
        layout.addWidget(self._build_defaults_form())
        layout.addWidget(self._build_options_form())
        layout.addLayout(self._build_actions())
        layout.addStretch(1)

        self._load_values()
        app_events.language_changed.connect(self._reload_texts)

    def _build_company_form(self) -> QGroupBox:
        self.group_company = QGroupBox(t("data_company"))
        form = QFormLayout(self.group_company)
        form.setLabelAlignment(Qt.AlignRight)
        form.setFormAlignment(Qt.AlignTop)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(8)
        self.form_company = form

        self.ed_name = QLineEdit()
        self.ed_tax = QLineEdit()
        self.ed_address = QLineEdit()
        self.ed_phone = QLineEdit()
        self.ed_email = QLineEdit()
        self.ed_web = QLineEdit()

        self._company_fields = [
            ("name", self.ed_name),
            ("tax_id", self.ed_tax),
            ("address", self.ed_address),
            ("phone", self.ed_phone),
            ("email", self.ed_email),
            ("web", self.ed_web),
        ]
        for key, widget in self._company_fields:
            form.addRow(t(key), widget)

        logo_widget = QWidget()
        logo_row = QHBoxLayout(logo_widget)
        logo_row.setContentsMargins(0, 0, 0, 0)
        self.ed_logo = QLineEdit()
        self.ed_logo.setReadOnly(True)
        self.btn_logo = QPushButton(tu("select_logo"))
        self.btn_logo.clicked.connect(self._pick_logo)
        logo_row.addWidget(self.ed_logo, 1)
        logo_row.addWidget(self.btn_logo)
        form.addRow(t("logo"), logo_widget)

        self.lbl_logo_preview = QLabel()
        self.lbl_logo_preview.setFixedHeight(90)
        self.lbl_logo_preview.setMinimumWidth(200)
        self.lbl_logo_preview.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.lbl_logo_preview.setScaledContents(False)
        self.lbl_logo_preview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        form.addRow(t("logo_preview"), self.lbl_logo_preview)

        return self.group_company

    def _build_defaults_form(self) -> QGroupBox:
        self.group_defaults = QGroupBox(t("defaults"))
        form = QFormLayout(self.group_defaults)
        form.setLabelAlignment(Qt.AlignRight)
        form.setFormAlignment(Qt.AlignTop)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(8)
        self.form_defaults = form

        self.ed_default_vat = QLineEdit()
        self.ed_default_margin = QLineEdit()
        self.ed_quote_prefix = QLineEdit()
        self.cb_lang = QComboBox()
        self.cb_lang.addItem(t("lang_es"), "es")
        self.cb_lang.addItem(t("lang_gl"), "gl")

        self.cb_theme = QComboBox()
        self.cb_theme.addItem(t("theme_light"), "light")
        self.cb_theme.addItem(t("theme_dark"), "dark")

        self._defaults_fields = [
            ("default_vat", self.ed_default_vat),
            ("default_margin", self.ed_default_margin),
            ("quote_prefix", self.ed_quote_prefix),
            ("language", self.cb_lang),
            ("theme", self.cb_theme),
        ]
        for key, widget in self._defaults_fields:
            form.addRow(t(key), widget)
        return self.group_defaults

    def _build_options_form(self) -> QGroupBox:
        self.group_options = QGroupBox(t("preferences"))
        form = QFormLayout(self.group_options)
        form.setLabelAlignment(Qt.AlignRight)
        form.setFormAlignment(Qt.AlignTop)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(8)
        self.form_options = form

        self.chk_costs = QCheckBox(t("show_costs"))
        self.chk_costs.stateChanged.connect(self._on_toggle_costs)
        form.addRow(self.chk_costs)
        return self.group_options

    def _build_actions(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.addStretch(1)
        self.btn_save = QPushButton(tu("ok"))
        self.btn_save.clicked.connect(self._save)
        row.addWidget(self.btn_save)
        return row

    def _load_values(self) -> None:
        s = self._settings
        self.ed_name.setText(str(s.get("company_name", "")))
        self.ed_tax.setText(str(s.get("company_tax_id", "")))
        self.ed_address.setText(str(s.get("company_address", "")))
        self.ed_phone.setText(str(s.get("company_phone", "")))
        self.ed_email.setText(str(s.get("company_email", "")))
        self.ed_web.setText(str(s.get("company_web", "")))
        logo_path = str(s.get("logo_path", ""))
        self.ed_logo.setText(logo_path)
        self._update_logo_preview(logo_path)
        self.ed_default_vat.setText(str(s.get("default_vat", "")))
        self.ed_default_margin.setText(str(s.get("default_margin", "")))
        self.ed_quote_prefix.setText(str(s.get("quote_prefix", "PRES-")))
        self.chk_costs.setChecked(bool(s.get("mostrar_costes", True)))
        lang = str(s.get("idioma", "es"))
        idx = self.cb_lang.findData(lang)
        if idx >= 0:
            self.cb_lang.setCurrentIndex(idx)
        theme = str(s.get("theme", "light"))
        idx = self.cb_theme.findData(theme)
        if idx >= 0:
            self.cb_theme.setCurrentIndex(idx)

    def _pick_logo(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, t("select_logo"), "", "Imagenes (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        if not path:
            return
        src = Path(path)
        if not src.exists():
            return
        data_dir = get_portable_dir("data")
        dest = data_dir / f"logo{src.suffix.lower()}"
        shutil.copy2(src, dest)
        self.ed_logo.setText(str(dest))
        self._update_logo_preview(str(dest))
        self._settings.set("logo_path", str(dest))
        self._settings.save()

    def _on_toggle_costs(self, state: int) -> None:
        value = state == Qt.Checked
        self._settings.set("mostrar_costes", value)
        self._settings.save()
        app_events.costs_visibility_changed.emit(value)

    def _save(self) -> None:
        self._settings.set("company_name", self.ed_name.text().strip())
        self._settings.set("company_tax_id", self.ed_tax.text().strip())
        self._settings.set("company_address", self.ed_address.text().strip())
        self._settings.set("company_phone", self.ed_phone.text().strip())
        self._settings.set("company_email", self.ed_email.text().strip())
        self._settings.set("company_web", self.ed_web.text().strip())
        self._settings.set("default_vat", self.ed_default_vat.text().strip())
        self._settings.set("default_margin", self.ed_default_margin.text().strip())
        self._settings.set("quote_prefix", self.ed_quote_prefix.text().strip() or "PRES-")
        self._settings.set("idioma", self.cb_lang.currentData())
        self._settings.set("theme", self.cb_theme.currentData() or "light")
        self._settings.save()
        app_events.language_changed.emit(self.cb_lang.currentData())
        QMessageBox.information(self, t("company"), t("saved"))

    def _reload_texts(self, _lang: str) -> None:
        self.title.setText(tu("company"))
        self.group_company.setTitle(t("data_company"))
        self.group_defaults.setTitle(t("defaults"))
        self.group_options.setTitle(t("preferences"))
        for key, widget in self._company_fields:
            label = self.form_company.labelForField(widget)
            if label is not None:
                label.setText(t(key))
        label = self.form_company.labelForField(self.ed_logo.parentWidget())
        if label is not None:
            label.setText(t("logo"))
        label = self.form_company.labelForField(self.lbl_logo_preview)
        if label is not None:
            label.setText(t("logo_preview"))
        self.btn_logo.setText(tu("select_logo"))

        for key, widget in self._defaults_fields:
            label = self.form_defaults.labelForField(widget)
            if label is not None:
                label.setText(t(key))

        lang_value = self.cb_lang.currentData()
        self.cb_lang.blockSignals(True)
        self.cb_lang.clear()
        self.cb_lang.addItem(t("lang_es"), "es")
        self.cb_lang.addItem(t("lang_gl"), "gl")
        idx = self.cb_lang.findData(lang_value)
        if idx >= 0:
            self.cb_lang.setCurrentIndex(idx)
        self.cb_lang.blockSignals(False)

        theme_value = self.cb_theme.currentData()
        self.cb_theme.blockSignals(True)
        self.cb_theme.clear()
        self.cb_theme.addItem(t("theme_light"), "light")
        self.cb_theme.addItem(t("theme_dark"), "dark")
        idx = self.cb_theme.findData(theme_value)
        if idx >= 0:
            self.cb_theme.setCurrentIndex(idx)
        self.cb_theme.blockSignals(False)

        self.chk_costs.setText(t("show_costs"))
        self.btn_save.setText(tu("ok"))

    def _update_logo_preview(self, logo_path: str) -> None:
        logo_file = None
        if logo_path:
            candidate = Path(logo_path)
            if candidate.exists():
                logo_file = candidate
        if logo_file is None:
            default_logo = Path(__file__).resolve().parents[1] / "assets" / "logo_orzalan.png"
            if default_logo.exists():
                logo_file = default_logo
                if not self.ed_logo.text().strip():
                    self.ed_logo.setPlaceholderText(f"{t('logo_default')}: {default_logo}")
        if logo_file is None:
            self.lbl_logo_preview.clear()
            return
        pix = QPixmap(str(logo_file))
        target_h = self.lbl_logo_preview.height() or 90
        scaled = pix.scaledToHeight(target_h, Qt.SmoothTransformation)
        self.lbl_logo_preview.setPixmap(scaled)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_logo_preview(self.ed_logo.text().strip())
