from __future__ import annotations

from datetime import date
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
    QStyle,
    QDialog,
    QHeaderView,
)

from db.models import Client, Quote
from db.session import get_session
from ui.quote_editor import QuoteEditor
from ui.i18n import t, tu
from services.exporter import export_quote_pdf, export_quote_xlsx
from ui.numeric_delegate import NumericAlignDelegate


class QuotesView(QWidget):
    COL_ID = 0
    COL_NUMBER = 1
    COL_CLIENT = 2
    COL_DATE = 3
    COL_STATUS = 4
    COL_TOTAL = 5

    def __init__(self) -> None:
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        self.title = QLabel(tu("quotes"))
        self.title.setObjectName("PageTitle")
        self.title.setVisible(False)
        self.title.setFixedHeight(0)
        layout.addWidget(self.title)

        layout.addLayout(self._build_filters())
        layout.addLayout(self._build_actions())
        layout.addWidget(self._build_table(), 1)

        self._load_filters()
        self._load_quotes()
        from ui.app_events import app_events
        app_events.language_changed.connect(self._reload_texts)

    def _build_filters(self) -> QFormLayout:
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        form.setFormAlignment(Qt.AlignTop)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(6)

        self.cb_status = QComboBox()
        self.cb_status.addItems([t("all"), t("draft"), t("sent"), t("accepted"), t("rejected")])
        self.cb_status.currentIndexChanged.connect(self._load_quotes)

        self.cb_client = QComboBox()
        self.cb_client.currentIndexChanged.connect(self._load_quotes)

        self.dt_from = QDateEdit()
        self.dt_from.setCalendarPopup(True)
        self.dt_from.setDate(date.today())
        self.dt_from.dateChanged.connect(self._load_quotes)

        self.dt_to = QDateEdit()
        self.dt_to.setCalendarPopup(True)
        self.dt_to.setDate(date.today())
        self.dt_to.dateChanged.connect(self._load_quotes)

        self.cb_use_dates = QComboBox()
        self.cb_use_dates.addItems([t("no_range"), t("filter_range")])
        self.cb_use_dates.currentIndexChanged.connect(self._load_quotes)

        self._form = form
        self._form_rows = [
            ("status", self.cb_status),
            ("client", self.cb_client),
            ("dates", self.cb_use_dates),
            ("date_from", self.dt_from),
            ("date_to", self.dt_to),
        ]
        for key, widget in self._form_rows:
            form.addRow(t(key), widget)
        return form

    def _build_actions(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(8)

        self.btn_new = QPushButton(tu("new"))
        self.btn_new.setIcon(self.style().standardIcon(QStyle.SP_FileIcon))
        self.btn_new.clicked.connect(self._new_quote)

        self.btn_edit = QPushButton(tu("edit"))
        self.btn_edit.setIcon(self.style().standardIcon(QStyle.SP_FileDialogDetailedView))
        self.btn_edit.clicked.connect(self._edit_quote)

        self.btn_dup = QPushButton(tu("duplicate"))
        self.btn_dup.setIcon(self.style().standardIcon(QStyle.SP_FileDialogNewFolder))
        self.btn_dup.clicked.connect(self._duplicate_quote)

        self.btn_status = QPushButton(tu("change_status"))
        self.btn_status.setIcon(self.style().standardIcon(QStyle.SP_BrowserReload))
        self.btn_status.clicked.connect(self._toggle_status)

        self.btn_delete = QPushButton(tu("delete"))
        self.btn_delete.setIcon(self.style().standardIcon(QStyle.SP_TrashIcon))
        self.btn_delete.clicked.connect(self._delete_quote)

        self.btn_export_pdf = QPushButton(tu("export_pdf"))
        self.btn_export_pdf.setIcon(self.style().standardIcon(QStyle.SP_DialogSaveButton))
        self.btn_export_pdf.clicked.connect(self._export_pdf)
        self.btn_export_xlsx = QPushButton(tu("export_xlsx"))
        self.btn_export_xlsx.setIcon(self.style().standardIcon(QStyle.SP_DialogSaveButton))
        self.btn_export_xlsx.clicked.connect(self._export_xlsx)
        self.btn_export_pdf.setEnabled(False)
        self.btn_export_xlsx.setEnabled(False)

        row.addWidget(self.btn_new)
        row.addWidget(self.btn_edit)
        row.addWidget(self.btn_dup)
        row.addWidget(self.btn_status)
        row.addWidget(self.btn_delete)
        row.addWidget(self.btn_export_pdf)
        row.addWidget(self.btn_export_xlsx)
        row.addStretch(1)
        return row

    def _build_table(self) -> QTableView:
        from PySide6.QtGui import QStandardItemModel, QStandardItem

        self.model = QStandardItemModel(0, 6, self)
        self._set_table_headers()

        table = QTableView()
        table.setObjectName("QuotesTable")
        table.setModel(self.model)
        table.setItemDelegate(NumericAlignDelegate(table))
        table.setSortingEnabled(True)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableView.SelectRows)
        table.setSelectionMode(QTableView.SingleSelection)
        table.setEditTriggers(QTableView.NoEditTriggers)
        header = table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(self.COL_NUMBER, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(self.COL_CLIENT, QHeaderView.Stretch)
        header.setSectionResizeMode(self.COL_DATE, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(self.COL_STATUS, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(self.COL_TOTAL, QHeaderView.ResizeToContents)
        table.verticalHeader().setVisible(False)
        table.setColumnHidden(self.COL_ID, True)
        table.selectionModel().selectionChanged.connect(self._update_export_buttons)

        self.table = table
        self._item_cls = QStandardItem
        return table

    def _load_filters(self) -> None:
        self.cb_client.blockSignals(True)
        self.cb_client.clear()
        self.cb_client.addItem(t("all"), 0)
        with get_session() as session:
            for client in session.query(Client).order_by(Client.name.asc()).all():
                self.cb_client.addItem(client.name, client.id)
        self.cb_client.blockSignals(False)

    def _load_quotes(self) -> None:
        self.model.setRowCount(0)
        status = self.cb_status.currentText()
        client_id = self.cb_client.currentData()

        use_dates = self.cb_use_dates.currentIndex() == 1
        from_date = self.dt_from.date().toPython()
        to_date = self.dt_to.date().toPython()

        with get_session() as session:
            q = session.query(Quote, Client).join(Client, Quote.client_id == Client.id)
            if status != t("all"):
                variants = _status_variants(status)
                if variants:
                    q = q.filter(Quote.status.in_(list(variants)))
                else:
                    q = q.filter(Quote.status == status)
            if client_id and client_id != 0:
                q = q.filter(Quote.client_id == client_id)
            if use_dates:
                q = q.filter(Quote.date >= from_date, Quote.date <= to_date)
            q = q.order_by(Quote.date.desc())

            for quote, client in q.all():
                self.model.appendRow(
                    [
                        self._item_cls(str(quote.id)),
                        self._item_cls(quote.number or ""),
                        self._item_cls(client.name or ""),
                        self._item_cls(str(quote.date) if quote.date else ""),
                        self._item_cls(_display_status(quote.status)),
                        self._item_cls(f"{quote.total:.2f}" if quote.total is not None else "0.00"),
                    ]
                )
                self.model.item(self.model.rowCount() - 1, self.COL_TOTAL).setTextAlignment(
                    Qt.AlignRight | Qt.AlignVCenter
                )

    def _selected_quote_id(self) -> int | None:
        indexes = self.table.selectionModel().selectedRows()
        if not indexes:
            return None
        value = self.model.item(indexes[0].row(), self.COL_ID).text()
        return int(value)

    def _update_export_buttons(self) -> None:
        enabled = self._selected_quote_id() is not None
        self.btn_export_pdf.setEnabled(enabled)
        self.btn_export_xlsx.setEnabled(enabled)

    def _new_quote(self) -> None:
        editor = QuoteEditor(self)
        if editor.exec() == QDialog.Accepted:
            self._load_quotes()

    def _edit_quote(self) -> None:
        quote_id = self._selected_quote_id()
        if quote_id is None:
            QMessageBox.information(self, t("quotes"), t("select_quote"))
            return
        editor = QuoteEditor(self, quote_id=quote_id)
        if editor.exec() == QDialog.Accepted:
            self._load_quotes()

    def _duplicate_quote(self) -> None:
        quote_id = self._selected_quote_id()
        if quote_id is None:
            QMessageBox.information(self, t("quotes"), t("select_quote"))
            return
        editor = QuoteEditor(self, quote_id=quote_id, duplicate=True)
        if editor.exec() == QDialog.Accepted:
            self._load_quotes()

    def _toggle_status(self) -> None:
        quote_id = self._selected_quote_id()
        if quote_id is None:
            QMessageBox.information(self, t("quotes"), t("select_quote"))
            return
        with get_session() as session:
            quote = session.get(Quote, quote_id)
            if quote is None:
                return
            current = (quote.status or "").lower()
            if current in {"draft", "borrador"}:
                next_status = t("sent")
            else:
                next_status = t("draft")
            quote.status = next_status
            session.commit()
        self._load_quotes()

    def _delete_quote(self) -> None:
        quote_id = self._selected_quote_id()
        if quote_id is None:
            QMessageBox.information(self, t("quotes"), t("select_quote"))
            return
        confirm = QMessageBox.question(
            self,
            t("delete"),
            t("delete_quote_confirm"),
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return
        with get_session() as session:
            quote = session.get(Quote, quote_id)
            if quote is None:
                return
            session.delete(quote)
            session.commit()
        self._load_quotes()

    def _export_pdf(self) -> None:
        quote_id = self._selected_quote_id()
        if quote_id is None:
            QMessageBox.information(self, t("quotes"), t("select_quote"))
            return
        path = export_quote_pdf(Path(f"presupuesto_{quote_id}.pdf"), quote_id, include_costs=False)
        QMessageBox.information(self, t("export"), f"{t('pdf_generated')}: {path}")

    def _export_xlsx(self) -> None:
        quote_id = self._selected_quote_id()
        if quote_id is None:
            QMessageBox.information(self, t("quotes"), t("select_quote"))
            return
        path = export_quote_xlsx(Path(f"presupuesto_{quote_id}.xlsx"), quote_id, include_costs=False)
        QMessageBox.information(self, t("export"), f"{t('xlsx_generated')}: {path}")

    def _set_table_headers(self) -> None:
        self.model.setHorizontalHeaderLabels(
            ["ID", t("number"), t("client"), t("date"), t("status"), t("total")]
        )

    def _reload_texts(self, _lang: str) -> None:
        self.title.setText(tu("quotes"))
        self.btn_new.setText(tu("new"))
        self.btn_edit.setText(tu("edit"))
        self.btn_dup.setText(tu("duplicate"))
        self.btn_status.setText(tu("change_status"))
        self.btn_delete.setText(tu("delete"))
        self.btn_export_pdf.setText(tu("export_pdf"))
        self.btn_export_xlsx.setText(tu("export_xlsx"))
        self.cb_status.blockSignals(True)
        self.cb_status.clear()
        self.cb_status.addItems([t("all"), t("draft"), t("sent"), t("accepted"), t("rejected")])
        self.cb_status.setCurrentIndex(0)
        self.cb_status.blockSignals(False)
        self.cb_use_dates.blockSignals(True)
        self.cb_use_dates.clear()
        self.cb_use_dates.addItems([t("no_range"), t("filter_range")])
        self.cb_use_dates.blockSignals(False)
        # update form labels
        # update existing form labels
        for key, widget in self._form_rows:
            lbl = self._form.labelForField(widget)
            if lbl is not None:
                lbl.setText(t(key))
        self._set_table_headers()
        self._load_filters()
        self._load_quotes()


def _display_status(status: str | None) -> str:
    if not status:
        return ""
    lower = status.lower()
    map_en_to_es = {
        "draft": t("draft"),
        "sent": t("sent"),
        "accepted": t("accepted"),
        "rejected": t("rejected"),
    }
    return map_en_to_es.get(lower, status)


def _status_variants(label: str) -> set[str]:
    lower = label.lower()
    if lower in {t("draft").lower(), "borrador", "draft"}:
        return {"draft", "borrador", t("draft")}
    if lower in {t("sent").lower(), "enviado", "sent"}:
        return {"sent", "enviado", t("sent")}
    if lower in {t("accepted").lower(), "aceptado", "accepted"}:
        return {"accepted", "aceptado", t("accepted")}
    if lower in {t("rejected").lower(), "rechazado", "rexeitado", "rejected"}:
        return {"rejected", "rechazado", "rexeitado", t("rejected")}
    return set()
