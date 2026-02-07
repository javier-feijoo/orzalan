from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QToolButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QHeaderView,
)

from db.models import Client, Product, Quote, QuoteLine
from db.session import get_session
from ui.i18n import t, tu
from ui.numeric_delegate import NumericAlignDelegate
from services.exporter import export_quote_pdf, export_quote_xlsx
from settings import Settings


@dataclass(frozen=True)
class LineData:
    product_id: int | None
    ref: str
    desc: str
    unit: str
    qty: float
    unit_price: float
    discount: float
    vat: float


class ProductPicker(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        from ui.i18n import t
        self.setWindowTitle(t("add_from_catalog"))
        self.setMinimumWidth(600)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self.ed_search = QLineEdit()
        from ui.i18n import t
        self.ed_search.setPlaceholderText(t("search"))
        self.ed_search.textChanged.connect(self._apply_filter)
        layout.addWidget(self.ed_search)

        self.model = QStandardItemModel(0, 5, self)
        self.model.setHorizontalHeaderLabels(["ID", t("ref"), t("description"), t("unit"), t("sale_price")])

        from PySide6.QtWidgets import QTableView

        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setSortingEnabled(True)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.SingleSelection)
        self.table.setEditTriggers(QTableView.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setColumnHidden(0, True)
        layout.addWidget(self.table, 1)

        self.table.doubleClicked.connect(self._accept_on_double_click)

        actions = QHBoxLayout()
        actions.addStretch(1)
        from ui.i18n import t
        btn_cancel = QPushButton(tu("cancel"))
        btn_ok = QPushButton(tu("add"))
        btn_ok.setDefault(True)
        btn_cancel.clicked.connect(self.reject)
        btn_ok.clicked.connect(self.accept)
        actions.addWidget(btn_cancel)
        actions.addWidget(btn_ok)
        layout.addLayout(actions)

        self._load_products()

    def _accept_on_double_click(self) -> None:
        if self.selected_product_id() is not None:
            self.accept()

    def _load_products(self) -> None:
        self.model.setRowCount(0)
        with get_session() as session:
            products = session.query(Product).order_by(Product.ref.asc()).all()
            for p in products:
                self.model.appendRow(
                    [
                        QStandardItem(str(p.id)),
                        QStandardItem(p.ref or ""),
                        QStandardItem(p.short_desc or ""),
                        QStandardItem(p.unit or ""),
                        QStandardItem(f"{_calc_unit_price(p):.2f}"),
                    ]
                )
                self.model.item(self.model.rowCount() - 1, 4).setTextAlignment(
                    Qt.AlignRight | Qt.AlignVCenter
                )

    def _apply_filter(self) -> None:
        text = self.ed_search.text().strip().lower()
        for row in range(self.model.rowCount()):
            ref = self.model.item(row, 1).text().lower()
            desc = self.model.item(row, 2).text().lower()
            show = (not text) or (text in ref) or (text in desc)
            self.table.setRowHidden(row, not show)

    def selected_product_id(self) -> int | None:
        indexes = self.table.selectionModel().selectedRows()
        if not indexes:
            return None
        value = self.model.item(indexes[0].row(), 0).text()
        return int(value)


class FreeLineDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        from ui.i18n import t
        self.setWindowTitle(t("free_line"))
        self.setMinimumWidth(520)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        from ui.i18n import t
        group = QGroupBox(t("line"))
        form = QFormLayout(group)
        form.setLabelAlignment(Qt.AlignRight)
        form.setFormAlignment(Qt.AlignTop)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(8)
        self._header_form = form

        self.ed_ref = QLineEdit()
        self.ed_desc = QLineEdit()
        self.ed_unit = QLineEdit()
        self.ed_qty = QLineEdit("1")
        self.ed_price = QLineEdit("0")
        self.ed_discount = QLineEdit("0")
        self.ed_vat = QLineEdit("21")

        from ui.i18n import t
        form.addRow(t("ref"), self.ed_ref)
        form.addRow(t("description"), self.ed_desc)
        form.addRow(t("unit"), self.ed_unit)
        form.addRow(t("quantity"), self.ed_qty)
        form.addRow(t("sale_price"), self.ed_price)
        form.addRow(t("discount"), self.ed_discount)
        form.addRow(t("vat_percent"), self.ed_vat)

        root.addWidget(group)

        actions = QHBoxLayout()
        actions.addStretch(1)
        from ui.i18n import t
        btn_cancel = QPushButton(tu("cancel"))
        btn_ok = QPushButton(tu("add"))
        btn_ok.setDefault(True)
        btn_cancel.clicked.connect(self.reject)
        btn_ok.clicked.connect(self.accept)
        actions.addWidget(btn_cancel)
        actions.addWidget(btn_ok)
        root.addLayout(actions)

    def values(self) -> LineData:
        return LineData(
            product_id=None,
            ref=self.ed_ref.text().strip(),
            desc=self.ed_desc.text().strip(),
            unit=self.ed_unit.text().strip(),
            qty=_to_float(self.ed_qty.text(), 1.0),
            unit_price=_to_float(self.ed_price.text(), 0.0),
            discount=_to_float(self.ed_discount.text(), 0.0),
            vat=_to_float(self.ed_vat.text(), 0.0),
        )


class QuoteEditor(QDialog):
    def __init__(self, parent: QWidget | None = None, quote_id: int | None = None, duplicate: bool = False) -> None:
        super().__init__(parent)
        from ui.i18n import t
        self.setWindowTitle(t("line_editor"))
        self.setMinimumWidth(900)
        self._quote_id = quote_id
        self._duplicate = duplicate

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        root.addWidget(self._build_header())
        root.addWidget(self._build_lines(), 1)
        root.addWidget(self._build_totals())
        root.addLayout(self._build_actions())

        self._load_clients()
        if quote_id is not None:
            self._load_quote(quote_id, duplicate)
        else:
            self.ed_number.setText(_next_quote_number())
            self.ed_date.setDate(date.today())

        self._recalculate_totals()
        from ui.app_events import app_events
        app_events.language_changed.connect(self._reload_texts)
        app_events.costs_visibility_changed.connect(self._apply_cost_visibility)

    def _build_header(self) -> QWidget:
        group = QGroupBox()
        group.setTitle("")
        self._group_header = group

        header_bar = QWidget()
        header_bar.setObjectName("HeaderBar")
        header_layout = QHBoxLayout(header_bar)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        self.lbl_header = QLabel(t("quote_data"))
        self.lbl_header.setObjectName("HeaderChip")
        self.btn_header_toggle = QToolButton()
        self.btn_header_toggle.setObjectName("HeaderToggle")
        self.btn_header_toggle.setCheckable(True)
        self.btn_header_toggle.setChecked(True)
        self.btn_header_toggle.setText("▾")
        self.btn_header_toggle.setToolTip(t("hide"))
        self.btn_header_toggle.clicked.connect(self._toggle_header)
        header_layout.addWidget(self.lbl_header)
        header_layout.addStretch(1)
        header_layout.addWidget(self.btn_header_toggle)

        self._header_body = QWidget()
        self._header_body.setObjectName("HeaderBody")
        form = QFormLayout(self._header_body)
        form.setLabelAlignment(Qt.AlignRight)
        form.setFormAlignment(Qt.AlignTop)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(8)
        self._header_form = form

        self.ed_number = QLineEdit()
        self.ed_number.setReadOnly(True)

        self.cb_client = QComboBox()

        self.ed_date = QDateEdit()
        self.ed_date.setCalendarPopup(True)

        self.sp_valid = QSpinBox()
        self.sp_valid.setRange(1, 365)
        self.sp_valid.setValue(30)

        self.ed_global_vat = QLineEdit("0")
        self.ed_global_discount = QLineEdit("0")
        self.cb_status = QComboBox()
        self._reload_status_items()
        self.ed_global_vat.textChanged.connect(self._recalculate_totals)
        self.ed_global_discount.textChanged.connect(self._recalculate_totals)

        self._header_fields = [
            ("number", self.ed_number),
            ("client", self.cb_client),
            ("date", self.ed_date),
            ("valid_days", self.sp_valid),
            ("global_vat", self.ed_global_vat),
            ("global_discount", self.ed_global_discount),
            ("status", self.cb_status),
        ]
        for key, widget in self._header_fields:
            form.addRow(t(key), widget)

        outer = QVBoxLayout(group)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.setSpacing(8)
        outer.addWidget(header_bar)
        outer.addWidget(self._header_body)

        self._restore_header_state()
        return group

    def _toggle_header(self) -> None:
        expanded = self.btn_header_toggle.isChecked()
        self._header_body.setVisible(expanded)
        self.btn_header_toggle.setText("▾" if expanded else "▸")
        self.btn_header_toggle.setToolTip(t("hide") if expanded else t("show"))
        self._save_header_state(expanded)

    def _save_header_state(self, expanded: bool) -> None:
        settings = Settings.load()
        settings.set("quote_header_expanded", bool(expanded))
        settings.save()

    def _restore_header_state(self) -> None:
        settings = Settings.load()
        expanded = bool(settings.get("quote_header_expanded", True))
        self.btn_header_toggle.setChecked(expanded)
        self._header_body.setVisible(expanded)
        self.btn_header_toggle.setText("▾" if expanded else "▸")
        self.btn_header_toggle.setToolTip(t("hide") if expanded else t("show"))

    def _build_lines(self) -> QWidget:
        panel = QWidget()
        v = QVBoxLayout(panel)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(8)

        actions = QHBoxLayout()
        self.btn_add_catalog = QPushButton(tu("add_from_catalog"))
        self.btn_add_catalog.clicked.connect(self._add_from_catalog)
        self.btn_add_free = QPushButton(tu("add_free_line"))
        self.btn_add_free.clicked.connect(self._add_free_line)
        self.btn_remove = QPushButton(tu("remove_line"))
        self.btn_remove.clicked.connect(self._remove_line)
        actions.addWidget(self.btn_add_catalog)
        actions.addWidget(self.btn_add_free)
        actions.addWidget(self.btn_remove)
        actions.addStretch(1)
        v.addLayout(actions)

        self.table = QTableWidget(0, 9)
        self.table.setItemDelegate(NumericAlignDelegate(self.table))
        self.table.setObjectName("QuoteLinesTable")
        self._set_table_headers()
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.DoubleClicked | QTableWidget.SelectedClicked)
        self.table.itemChanged.connect(self._on_line_changed)
        header = self.table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setMinimumHeight(32)
        header.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(8, QHeaderView.ResizeToContents)
        header.setMinimumSectionSize(90)

        v.addWidget(self.table, 1)
        return panel

    def _build_totals(self) -> QWidget:
        panel = QWidget()
        h = QHBoxLayout(panel)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(12)

        h.addStretch(1)
        self.lbl_subtotal = QLabel(f"{t('subtotal')}: 0.00")
        self.lbl_vat = QLabel(f"{t('vat')}: 0.00")
        self.lbl_total = QLabel(f"{t('total')}: 0.00")
        h.addWidget(self.lbl_subtotal)
        h.addWidget(self.lbl_vat)
        h.addWidget(self.lbl_total)
        return panel

    def _build_actions(self) -> QHBoxLayout:
        row = QHBoxLayout()
        self.btn_export_pdf = QPushButton(tu("export_pdf"))
        self.btn_export_xlsx = QPushButton(tu("export_xlsx"))
        self.btn_export_pdf.clicked.connect(self._export_pdf)
        self.btn_export_xlsx.clicked.connect(self._export_xlsx)

        self.btn_export_pdf_internal = QPushButton(tu("export_internal_pdf"))
        self.btn_export_xlsx_internal = QPushButton(tu("export_internal_xlsx"))
        self.btn_export_pdf_internal.clicked.connect(lambda: self._export_pdf(internal=True))
        self.btn_export_xlsx_internal.clicked.connect(lambda: self._export_xlsx(internal=True))

        row.addWidget(self.btn_export_pdf)
        row.addWidget(self.btn_export_xlsx)

        settings = Settings.load()
        show_costs = bool(settings.get("mostrar_costes", False))
        self._apply_cost_visibility(show_costs)
        row.addWidget(self.btn_export_pdf_internal)
        row.addWidget(self.btn_export_xlsx_internal)

        row.addStretch(1)
        self.btn_cancel = QPushButton(tu("cancel"))
        self.btn_save = QPushButton(tu("ok"))
        self.btn_save.setDefault(True)
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_save.clicked.connect(self._save)
        row.addWidget(self.btn_cancel)
        row.addWidget(self.btn_save)
        return row

    def _set_table_headers(self) -> None:
        self.table.setHorizontalHeaderLabels(
            [
                t("quantity"),
                t("ref_short"),
                t("description"),
                t("unit"),
                t("sale_price"),
                t("discount_short"),
                t("vat_short"),
                t("subtotal"),
                t("total"),
            ]
        )

    def _reload_status_items(self) -> None:
        self.cb_status.clear()
        self.cb_status.addItems([t("draft"), t("sent"), t("accepted"), t("rejected")])

    def _reload_texts(self, _lang: str) -> None:
        self.setWindowTitle(t("line_editor"))
        if hasattr(self, "lbl_header"):
            self.lbl_header.setText(t("quote_data"))
        if hasattr(self, "btn_header_toggle"):
            expanded = self.btn_header_toggle.isChecked()
            self.btn_header_toggle.setToolTip(t("hide") if expanded else t("show"))
        self.btn_add_catalog.setText(tu("add_from_catalog"))
        self.btn_add_free.setText(tu("add_free_line"))
        self.btn_remove.setText(tu("remove_line"))
        self.btn_export_pdf.setText(tu("export_pdf"))
        self.btn_export_xlsx.setText(tu("export_xlsx"))
        self.btn_export_pdf_internal.setText(tu("export_internal_pdf"))
        self.btn_export_xlsx_internal.setText(tu("export_internal_xlsx"))
        self.btn_cancel.setText(tu("cancel"))
        self.btn_save.setText(tu("ok"))
        for key, widget in self._header_fields:
            label = self._header_form.labelForField(widget)
            if label is not None:
                label.setText(t(key))
        current_status = self.cb_status.currentText().lower()
        self._reload_status_items()
        status_map = {
            "draft": t("draft"),
            "borrador": t("draft"),
            "sent": t("sent"),
            "enviado": t("sent"),
            "accepted": t("accepted"),
            "aceptado": t("accepted"),
            "rejected": t("rejected"),
            "rechazado": t("rejected"),
            "rexeitado": t("rejected"),
        }
        new_status = status_map.get(current_status)
        if new_status:
            idx = self.cb_status.findText(new_status)
            if idx >= 0:
                self.cb_status.setCurrentIndex(idx)
        self._set_table_headers()
        self._recalculate_totals()

    def _apply_cost_visibility(self, show: bool) -> None:
        self.btn_export_pdf_internal.setVisible(show)
        self.btn_export_xlsx_internal.setVisible(show)

    def _load_clients(self) -> None:
        self.cb_client.clear()
        with get_session() as session:
            for client in session.query(Client).order_by(Client.name.asc()).all():
                self.cb_client.addItem(client.name, client.id)

    def _load_quote(self, quote_id: int, duplicate: bool) -> None:
        with get_session() as session:
            quote = session.get(Quote, quote_id)
            if quote is None:
                return
            if duplicate:
                self.ed_number.setText(_next_quote_number())
                self.cb_status.setCurrentText(t("draft"))
            else:
                self.ed_number.setText(quote.number or "")
                status = (quote.status or "").lower()
                map_status = {
                    "draft": t("draft"),
                    "borrador": t("draft"),
                    "sent": t("sent"),
                    "enviado": t("sent"),
                    "accepted": t("accepted"),
                    "aceptado": t("accepted"),
                    "rejected": t("rejected"),
                    "rechazado": t("rejected"),
                    "rexeitado": t("rejected"),
                }
                self.cb_status.setCurrentText(map_status.get(status, quote.status or t("draft")))
            self.ed_date.setDate(quote.date or date.today())
            self.sp_valid.setValue(quote.valid_days or 30)
            self.ed_global_vat.setText(str(quote.global_vat or 0))
            self.ed_global_discount.setText(str(quote.global_discount or 0))
            idx = self.cb_client.findData(quote.client_id)
            if idx >= 0:
                self.cb_client.setCurrentIndex(idx)

            self.table.setRowCount(0)
            for line in quote.lines:
                self._append_line(
                    LineData(
                        product_id=line.product_id,
                        ref=line.ref_snapshot or "",
                        desc=line.desc_snapshot or "",
                        unit=line.unit_snapshot or "",
                        qty=float(line.qty or 0),
                        unit_price=float(line.unit_price_snapshot or 0),
                        discount=float(line.discount or 0),
                        vat=float(line.vat or 0),
                    )
                )

    def _append_line(self, data: LineData) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)

        values = [
            f"{data.qty:.2f}",
            data.ref,
            data.desc,
            data.unit,
            f"{data.unit_price:.2f}",
            f"{data.discount:.2f}",
            f"{data.vat:.2f}",
            "0.00",
            "0.00",
        ]
        for col, val in enumerate(values):
            item = QTableWidgetItem(val)
            if col in {0, 4, 5, 6, 7, 8}:
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if col == 1:
                item.setData(Qt.UserRole, data.product_id)
            self.table.setItem(row, col, item)

        self._recalculate_row(row)

    def _add_from_catalog(self) -> None:
        picker = ProductPicker(self)
        if picker.exec() != QDialog.Accepted:
            return
        product_id = picker.selected_product_id()
        if product_id is None:
            return
        with get_session() as session:
            product = session.get(Product, product_id)
            if product is None:
                return
            self._append_line(
                LineData(
                    product_id=product.id,
                    ref=product.ref or "",
                    desc=product.short_desc or "",
                    unit=product.unit or "",
                    qty=1.0,
                    unit_price=_calc_unit_price(product),
                    discount=0.0,
                    vat=float(product.vat or 0),
                )
            )

    def _add_free_line(self) -> None:
        dlg = FreeLineDialog(self)
        if dlg.exec() != QDialog.Accepted:
            return
        data = dlg.values()
        if not data.desc:
            from ui.i18n import t
            QMessageBox.warning(self, t("line"), t("description_required"))
            return
        self._append_line(data)

    def _remove_line(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            return
        self.table.removeRow(row)
        self._recalculate_totals()

    def _on_line_changed(self, item: QTableWidgetItem) -> None:
        row = item.row()
        self._recalculate_row(row)

    def _recalculate_row(self, row: int) -> None:
        qty = _to_float(self._cell(row, 0), 0)
        price = _to_float(self._cell(row, 4), 0)
        discount = _to_float(self._cell(row, 5), 0)
        vat = _to_float(self._cell(row, 6), 0)

        line_subtotal = qty * price * (1 - discount / 100.0)
        line_total = line_subtotal * (1 + vat / 100.0)

        self.table.blockSignals(True)
        self._set_cell(row, 7, f"{line_subtotal:.2f}")
        self._set_cell(row, 8, f"{line_total:.2f}")
        self.table.blockSignals(False)
        self._recalculate_totals()

    def _recalculate_totals(self) -> None:
        subtotal = 0.0
        vat_total = 0.0
        for row in range(self.table.rowCount()):
            sub = _to_float(self._cell(row, 7), 0)
            tot = _to_float(self._cell(row, 8), 0)
            subtotal += sub
            vat_total += max(tot - sub, 0)

        global_discount = _to_float(self.ed_global_discount.text(), 0)
        subtotal_after = subtotal * (1 - global_discount / 100.0)

        global_vat = _to_float(self.ed_global_vat.text(), 0)
        if global_vat > 0:
            vat_total = subtotal_after * (global_vat / 100.0)

        total = subtotal_after + vat_total

        from ui.i18n import t
        self.lbl_subtotal.setText(f"{t('subtotal')}: {subtotal_after:.2f}")
        self.lbl_vat.setText(f"{t('vat')}: {vat_total:.2f}")
        self.lbl_total.setText(f"{t('total')}: {total:.2f}")

    def _cell(self, row: int, col: int) -> str:
        item = self.table.item(row, col)
        return item.text() if item else ""

    def _set_cell(self, row: int, col: int, value: str) -> None:
        item = self.table.item(row, col)
        if item is None:
            item = QTableWidgetItem(value)
            item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, col, item)
        else:
            item.setText(value)

    def _save(self) -> None:
        client_id = self.cb_client.currentData()
        if not client_id:
            from ui.i18n import t
            QMessageBox.warning(self, t("quotes"), t("select_client"))
            return

        lines = self._collect_lines()
        if not lines:
            from ui.i18n import t
            QMessageBox.warning(self, t("quotes"), t("add_line_required"))
            return

        with get_session() as session:
            if self._quote_id and not self._duplicate:
                quote = session.get(Quote, self._quote_id)
            else:
                quote = None

            if quote is None:
                quote = Quote(number=self.ed_number.text().strip(), client_id=client_id)
                session.add(quote)

            quote.client_id = client_id
            quote.date = self.ed_date.date().toPython()
            quote.valid_days = int(self.sp_valid.value())
            quote.status = self.cb_status.currentText()
            quote.global_vat = _to_float(self.ed_global_vat.text(), 0)
            quote.global_discount = _to_float(self.ed_global_discount.text(), 0)
            quote.vat_mode = "line"
            quote.notes = ""

            quote.lines.clear()
            for line in lines:
                line_subtotal = line.qty * line.unit_price * (1 - line.discount / 100.0)
                line_total = line_subtotal * (1 + line.vat / 100.0)
                quote.lines.append(
                    QuoteLine(
                        product_id=line.product_id,
                        ref_snapshot=line.ref,
                        desc_snapshot=line.desc,
                        unit_snapshot=line.unit,
                        qty=line.qty,
                        unit_price_snapshot=line.unit_price,
                        discount=line.discount,
                        vat=line.vat,
                        line_subtotal=line_subtotal,
                        line_total=line_total,
                    )
                )

            subtotal, vat_total, total = _compute_totals(lines, quote.global_discount, quote.global_vat)
            quote.subtotal = subtotal
            quote.vat_total = vat_total
            quote.total = total

            session.commit()

        self.accept()

    def _export_pdf(self, internal: bool = False) -> None:
        if not self._quote_id:
            from ui.i18n import t
            QMessageBox.information(self, t("export"), t("export_save_first"))
            return
        path = export_quote_pdf(Path(f"presupuesto_{self._quote_id}.pdf"), self._quote_id, include_costs=internal)
        QMessageBox.information(self, t("export"), f"{t('pdf_generated')}: {path}")

    def _export_xlsx(self, internal: bool = False) -> None:
        if not self._quote_id:
            from ui.i18n import t
            QMessageBox.information(self, t("export"), t("export_save_first"))
            return
        path = export_quote_xlsx(Path(f"presupuesto_{self._quote_id}.xlsx"), self._quote_id, include_costs=internal)
        QMessageBox.information(self, t("export"), f"{t('xlsx_generated')}: {path}")

    def _collect_lines(self) -> list[LineData]:
        data: list[LineData] = []
        for row in range(self.table.rowCount()):
            product_id = None
            ref_item = self.table.item(row, 1)
            if ref_item is not None:
                product_id = ref_item.data(Qt.UserRole)
            data.append(
                LineData(
                    product_id=product_id,
                    ref=self._cell(row, 1),
                    desc=self._cell(row, 2),
                    unit=self._cell(row, 3),
                    qty=_to_float(self._cell(row, 0), 0),
                    unit_price=_to_float(self._cell(row, 4), 0),
                    discount=_to_float(self._cell(row, 5), 0),
                    vat=_to_float(self._cell(row, 6), 0),
                )
            )
        return data


def _to_float(value: str, default: float) -> float:
    try:
        return float(value.replace(",", "."))
    except Exception:
        return default


def _calc_unit_price(product: Product) -> float:
    if product.fixed_price:
        return float(product.sale_price or 0)
    cost = float(product.cost or 0)
    margin = float(product.margin or 0)
    if cost > 0 and margin > 0:
        return cost * (1 + margin)
    return float(product.sale_price or 0)


def _next_quote_number() -> str:
    settings = Settings.load()
    prefix = settings.get("quote_prefix", "PRES-") or "PRES-"
    with get_session() as session:
        last = session.query(Quote).order_by(Quote.id.desc()).first()
        next_id = (last.id + 1) if last is not None else 1
        return f"{prefix}{next_id:04d}"


def _compute_totals(lines: list[LineData], global_discount: float, global_vat: float) -> tuple[float, float, float]:
    subtotal = 0.0
    vat_total = 0.0
    for line in lines:
        line_subtotal = line.qty * line.unit_price * (1 - line.discount / 100.0)
        line_total = line_subtotal * (1 + line.vat / 100.0)
        subtotal += line_subtotal
        vat_total += max(line_total - line_subtotal, 0)

    subtotal_after = subtotal * (1 - global_discount / 100.0)
    if global_vat > 0:
        vat_total = subtotal_after * (global_vat / 100.0)
    total = subtotal_after + vat_total
    return subtotal_after, vat_total, total
