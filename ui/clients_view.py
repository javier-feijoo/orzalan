from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QSortFilterProxyModel, Qt
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
    QStyle,
    QHeaderView,
)

from db.models import Client, Quote
from db.session import get_session
from ui.i18n import t, tu
from ui.app_events import app_events
from ui.numeric_delegate import NumericAlignDelegate


@dataclass(frozen=True)
class ClientRow:
    id: int
    name: str
    tax_id: str
    email: str
    phone: str
    contact: str


class ClientDialog(QDialog):
    def __init__(self, parent: QWidget | None = None, initial: ClientRow | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(t("client"))
        self.setMinimumWidth(520)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        group = QGroupBox(t("client"))
        form = QFormLayout(group)
        form.setLabelAlignment(Qt.AlignRight)
        form.setFormAlignment(Qt.AlignTop)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(8)

        self.ed_name = QLineEdit()
        self.ed_tax = QLineEdit()
        self.ed_email = QLineEdit()
        self.ed_phone = QLineEdit()
        self.ed_contact = QLineEdit()

        form.addRow(t("name"), self.ed_name)
        form.addRow(t("nif"), self.ed_tax)
        form.addRow(t("email"), self.ed_email)
        form.addRow(t("phone"), self.ed_phone)
        form.addRow(t("contact"), self.ed_contact)

        if initial is not None:
            self.ed_name.setText(initial.name)
            self.ed_tax.setText(initial.tax_id)
            self.ed_email.setText(initial.email)
            self.ed_phone.setText(initial.phone)
            self.ed_contact.setText(initial.contact)

        root.addWidget(group)

        actions = QHBoxLayout()
        actions.addStretch(1)
        btn_cancel = QPushButton(tu("cancel"))
        btn_ok = QPushButton(tu("ok"))
        btn_ok.setDefault(True)
        btn_cancel.clicked.connect(self.reject)
        btn_ok.clicked.connect(self.accept)
        actions.addWidget(btn_cancel)
        actions.addWidget(btn_ok)
        root.addLayout(actions)

    def values(self) -> ClientRow:
        return ClientRow(
            id=0,
            name=self.ed_name.text().strip(),
            tax_id=self.ed_tax.text().strip(),
            email=self.ed_email.text().strip(),
            phone=self.ed_phone.text().strip(),
            contact=self.ed_contact.text().strip(),
        )


class ClientsView(QWidget):
    COL_ID = 0
    COL_NAME = 1
    COL_TAX = 2
    COL_EMAIL = 3
    COL_PHONE = 4
    COL_CONTACT = 5

    def __init__(self) -> None:
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        self.title = QLabel(tu("clients"))
        self.title.setObjectName("PageTitle")
        self.title.setVisible(False)
        self.title.setFixedHeight(0)
        layout.addWidget(self.title)

        layout.addLayout(self._build_toolbar())
        layout.addWidget(self._build_table(), 1)
        layout.addWidget(self._build_quotes_panel())

        self._load_clients()
        app_events.language_changed.connect(self._reload_texts)

    def _build_toolbar(self) -> QHBoxLayout:
        bar = QHBoxLayout()
        bar.setSpacing(8)

        self.ed_search = QLineEdit()
        self.ed_search.setPlaceholderText(t("search_clients"))
        self.ed_search.textChanged.connect(self._apply_filter)

        self.btn_add = QPushButton(tu("new"))
        self.btn_add.setIcon(self.style().standardIcon(QStyle.SP_FileIcon))
        self.btn_add.clicked.connect(self._add_client)

        self.btn_edit = QPushButton(tu("edit"))
        self.btn_edit.setIcon(self.style().standardIcon(QStyle.SP_FileDialogDetailedView))
        self.btn_edit.clicked.connect(self._edit_client)

        self.btn_delete = QPushButton(tu("delete"))
        self.btn_delete.setIcon(self.style().standardIcon(QStyle.SP_TrashIcon))
        self.btn_delete.clicked.connect(self._delete_client)

        bar.addWidget(self.ed_search, 1)
        bar.addWidget(self.btn_add)
        bar.addWidget(self.btn_edit)
        bar.addWidget(self.btn_delete)
        return bar

    def _build_table(self) -> QTableView:
        self.model = QStandardItemModel(0, 6, self)
        self._set_table_headers()

        self.proxy = QSortFilterProxyModel(self)
        self.proxy.setSourceModel(self.model)
        self.proxy.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.proxy.setFilterKeyColumn(-1)

        table = QTableView()
        table.setObjectName("ClientsTable")
        table.setModel(self.proxy)
        table.setItemDelegate(NumericAlignDelegate(table))
        table.setSortingEnabled(True)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableView.SelectRows)
        table.setSelectionMode(QTableView.SingleSelection)
        table.setEditTriggers(QTableView.NoEditTriggers)
        header = table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(self.COL_NAME, QHeaderView.Stretch)
        header.setSectionResizeMode(self.COL_TAX, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(self.COL_EMAIL, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(self.COL_PHONE, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(self.COL_CONTACT, QHeaderView.ResizeToContents)
        table.verticalHeader().setVisible(False)
        table.setColumnHidden(self.COL_ID, True)
        table.selectionModel().selectionChanged.connect(self._on_client_selected)

        self.table = table
        return table

    def _build_quotes_panel(self) -> QWidget:
        panel = QWidget()
        v = QVBoxLayout(panel)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(8)

        self.label_quotes = QLabel(t("client_quotes"))
        self.label_quotes.setObjectName("SectionTitle")
        v.addWidget(self.label_quotes)

        self.quotes_model = QStandardItemModel(0, 4, self)
        self._set_quotes_headers()

        self.quotes_table = QTableView()
        self.quotes_table.setModel(self.quotes_model)
        self.quotes_table.setItemDelegate(NumericAlignDelegate(self.quotes_table))
        self.quotes_table.setAlternatingRowColors(True)
        self.quotes_table.setSelectionBehavior(QTableView.SelectRows)
        self.quotes_table.setSelectionMode(QTableView.SingleSelection)
        self.quotes_table.setEditTriggers(QTableView.NoEditTriggers)
        qh = self.quotes_table.horizontalHeader()
        qh.setStretchLastSection(True)
        qh.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        qh.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        qh.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        qh.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.quotes_table.verticalHeader().setVisible(False)

        v.addWidget(self.quotes_table)
        return panel

    def _apply_filter(self) -> None:
        self.proxy.setFilterFixedString(self.ed_search.text().strip())

    def _load_clients(self) -> None:
        self.model.setRowCount(0)
        with get_session() as session:
            rows = session.query(Client).order_by(Client.name.asc()).all()
            for row in rows:
                self.model.appendRow(self._row_to_items(row))

    def _row_to_items(self, row: Client) -> list[QStandardItem]:
        return [
            QStandardItem(str(row.id)),
            QStandardItem(row.name or ""),
            QStandardItem(row.tax_id or ""),
            QStandardItem(row.email or ""),
            QStandardItem(row.phone or ""),
            QStandardItem(row.contact_person or ""),
        ]

    def _selected_client_id(self) -> int | None:
        indexes = self.table.selectionModel().selectedRows()
        if not indexes:
            return None
        source_index = self.proxy.mapToSource(indexes[0])
        value = self.model.item(source_index.row(), self.COL_ID).text()
        return int(value)

    def _on_client_selected(self) -> None:
        client_id = self._selected_client_id()
        self._load_quotes(client_id)

    def _load_quotes(self, client_id: int | None) -> None:
        self.quotes_model.setRowCount(0)
        if client_id is None:
            return
        with get_session() as session:
            rows = (
                session.query(Quote)
                .filter(Quote.client_id == client_id)
                .order_by(Quote.date.desc())
                .all()
            )
            for row in rows:
                self.quotes_model.appendRow(
                    [
                        QStandardItem(row.number or ""),
                        QStandardItem(str(row.date) if row.date else ""),
                        QStandardItem(_display_status(row.status)),
                        QStandardItem(f"{row.total:.2f}" if row.total is not None else "0.00"),
                    ]
                )
                self.quotes_model.item(self.quotes_model.rowCount() - 1, 3).setTextAlignment(
                    Qt.AlignRight | Qt.AlignVCenter
                )

    def _add_client(self) -> None:
        dlg = ClientDialog(self)
        if dlg.exec() != QDialog.Accepted:
            return
        data = dlg.values()
        if not data.name:
            QMessageBox.warning(self, t("client"), f"{t('name')} {t('required')}")
            return
        with get_session() as session:
            client = Client(
                name=data.name,
                tax_id=data.tax_id,
                email=data.email,
                phone=data.phone,
                contact_person=data.contact,
            )
            session.add(client)
            session.commit()
        self._load_clients()

    def _edit_client(self) -> None:
        client_id = self._selected_client_id()
        if client_id is None:
            QMessageBox.information(self, t("client"), t("select_client"))
            return
        with get_session() as session:
            client = session.get(Client, client_id)
            if client is None:
                return
            initial = ClientRow(
                id=client.id,
                name=client.name or "",
                tax_id=client.tax_id or "",
                email=client.email or "",
                phone=client.phone or "",
                contact=client.contact_person or "",
            )
        dlg = ClientDialog(self, initial=initial)
        if dlg.exec() != QDialog.Accepted:
            return
        data = dlg.values()
        if not data.name:
            QMessageBox.warning(self, t("client"), f"{t('name')} {t('required')}")
            return
        with get_session() as session:
            client = session.get(Client, client_id)
            if client is None:
                return
            client.name = data.name
            client.tax_id = data.tax_id
            client.email = data.email
            client.phone = data.phone
            client.contact_person = data.contact
            session.commit()
        self._load_clients()

    def _delete_client(self) -> None:
        client_id = self._selected_client_id()
        if client_id is None:
            QMessageBox.information(self, t("client"), t("select_client"))
            return
        confirm = QMessageBox.question(
            self,
            t("delete"),
            t("delete_client_confirm"),
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return
        with get_session() as session:
            client = session.get(Client, client_id)
            if client is None:
                return
            session.delete(client)
            session.commit()
        self._load_clients()

    def _set_table_headers(self) -> None:
        self.model.setHorizontalHeaderLabels(
            ["ID", t("name"), t("nif"), t("email"), t("phone"), t("contact")]
        )

    def _set_quotes_headers(self) -> None:
        self.quotes_model.setHorizontalHeaderLabels(
            [t("number"), t("date"), t("status"), t("total")]
        )

    def _reload_texts(self, _lang: str) -> None:
        self.title.setText(tu("clients"))
        self.ed_search.setPlaceholderText(t("search_clients"))
        self.btn_add.setText(tu("new"))
        self.btn_edit.setText(tu("edit"))
        self.btn_delete.setText(tu("delete"))
        self.label_quotes.setText(t("client_quotes"))
        self._set_table_headers()
        self._set_quotes_headers()
        current_id = self._selected_client_id()
        self._load_clients()
        self._load_quotes(current_id)


def _display_status(status: str | None) -> str:
    if not status:
        return ""
    lower = status.lower()
    map_en_to_local = {
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
    return map_en_to_local.get(lower, status)
