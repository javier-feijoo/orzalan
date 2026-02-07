from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QSortFilterProxyModel, Qt
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QCheckBox,
    QSizePolicy,
    QTableView,
    QVBoxLayout,
    QWidget,
    QStyle,
    QHeaderView,
)

from db.models import Product, ProductCategory
from db.session import get_session
from settings import Settings
from ui.app_events import app_events
from ui.i18n import t, tu
from ui.numeric_delegate import NumericAlignDelegate


@dataclass(frozen=True)
class ProductRow:
    ref: str
    category: str
    category_id: int | None
    desc: str
    unit: str
    cost: float
    margin: float
    price: float
    active: bool


class ProductDialog(QDialog):
    def __init__(self, parent: QWidget | None = None, initial: Product | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(t("product"))
        self.setMinimumWidth(520)
        self._initial = initial

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        group = QGroupBox(t("products_title"))
        form = QFormLayout(group)
        form.setLabelAlignment(Qt.AlignRight)
        form.setFormAlignment(Qt.AlignTop)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(8)

        self.ed_ref = QLineEdit()
        self.cb_category = QComboBox()
        self.ed_desc = QLineEdit()
        self.ed_unit = QLineEdit()
        self.ed_cost = QLineEdit()
        self.ed_margin = QLineEdit()
        self.ed_price = QLineEdit()
        self.chk_fixed = QCheckBox(tu("fixed_price"))
        self.chk_active = QCheckBox(tu("active"))

        form.addRow(t("ref"), self.ed_ref)
        form.addRow(t("category"), self.cb_category)
        form.addRow(t("description"), self.ed_desc)
        form.addRow(t("unit"), self.ed_unit)
        form.addRow(t("cost"), self.ed_cost)
        form.addRow(t("margin"), self.ed_margin)
        form.addRow(t("sale_price"), self.ed_price)
        form.addRow(self.chk_fixed)
        form.addRow(self.chk_active)

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

        self._load_categories()
        self._load_initial()

    def _load_initial(self) -> None:
        if self._initial is None:
            self.chk_active.setChecked(True)
            return
        self.ed_ref.setText(self._initial.ref or "")
        self.ed_desc.setText(self._initial.short_desc or "")
        self.ed_unit.setText(self._initial.unit or "")
        self.ed_cost.setText(f"{float(self._initial.cost or 0):.2f}")
        self.ed_margin.setText(f"{float(self._initial.margin or 0) * 100:.2f}")
        self.ed_price.setText(f"{float(self._initial.sale_price or 0):.2f}")
        self.chk_fixed.setChecked(bool(self._initial.fixed_price))
        self.chk_active.setChecked(bool(self._initial.active))
        if self._initial.category_id:
            idx = self.cb_category.findData(self._initial.category_id)
            if idx >= 0:
                self.cb_category.setCurrentIndex(idx)

    def values(self) -> dict:
        return {
            "ref": self.ed_ref.text().strip(),
            "category_id": self.cb_category.currentData(),
            "desc": self.ed_desc.text().strip(),
            "unit": self.ed_unit.text().strip(),
            "cost": _to_float(self.ed_cost.text(), 0.0),
            "margin": _to_float(self.ed_margin.text(), 0.0),
            "price": _to_float(self.ed_price.text(), 0.0),
            "fixed": self.chk_fixed.isChecked(),
            "active": self.chk_active.isChecked(),
        }

    def _load_categories(self) -> None:
        self.cb_category.clear()
        with get_session() as session:
            categories = session.query(ProductCategory).all()
            categories = _sort_categories(categories)
            for c in categories:
                label = f"{c.code} - {c.name}" if c.code else c.name
                self.cb_category.addItem(label, c.id)
            # ensure default selection
            default = _default_category(session)
            if default is not None:
                idx = self.cb_category.findData(default.id)
                if idx >= 0:
                    self.cb_category.setCurrentIndex(idx)


def _to_float(value: str, default: float) -> float:
    try:
        return float(value.replace(",", "."))
    except Exception:
        return default


class ProductsView(QWidget):
    COL_REF = 0
    COL_CATEGORY = 1
    COL_DESC = 2
    COL_UNIT = 3
    COL_COST = 4
    COL_MARGIN = 5
    COL_PRICE = 6
    COL_ACTIVE = 7

    def __init__(self) -> None:
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        self.title = QLabel(tu("products"))
        self.title.setObjectName("PageTitle")
        self.title.setVisible(False)
        self.title.setFixedHeight(0)
        layout.addWidget(self.title)

        layout.addWidget(self._build_toolbar())
        layout.addWidget(self._build_table(), 1)

        app_events.costs_visibility_changed.connect(self.apply_cost_visibility)
        app_events.catalog_changed.connect(self._reload_catalog)
        settings = Settings.load()
        self.apply_cost_visibility(bool(settings.get("mostrar_costes", True)))
        self._refresh_filters()
        app_events.language_changed.connect(self._reload_texts)

    def _build_toolbar(self) -> QWidget:
        wrapper = QWidget()
        v = QVBoxLayout(wrapper)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(6)

        bar = QHBoxLayout()
        bar.setContentsMargins(0, 0, 0, 0)
        bar.setSpacing(8)

        self.ed_search = QLineEdit()
        self.ed_search.setPlaceholderText(t("search"))
        self.ed_search.textChanged.connect(self._apply_filters)
        self.ed_search.setMinimumWidth(320)
        self.ed_search.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.cb_category = QComboBox()
        self.cb_category.addItem(t("all_categories"), None)
        self.cb_category.currentIndexChanged.connect(self._apply_filters)
        self.cb_category.setMinimumWidth(220)
        self.cb_category.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.cb_category.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

        self.btn_categories = QPushButton(tu("categories"))
        self.btn_categories.clicked.connect(self._manage_categories)
        self.btn_categories.setMinimumWidth(110)
        self.btn_add = QPushButton(tu("new"))
        self.btn_add.setIcon(self.style().standardIcon(QStyle.SP_FileIcon))
        self.btn_add.setMinimumWidth(90)
        self.btn_add.clicked.connect(self._open_new_dialog)

        self.btn_edit = QPushButton(tu("edit"))
        self.btn_edit.setIcon(self.style().standardIcon(QStyle.SP_FileDialogDetailedView))
        self.btn_edit.setMinimumWidth(90)
        self.btn_edit.clicked.connect(self._open_edit_dialog)

        self.btn_delete = QPushButton(tu("delete"))
        self.btn_delete.setIcon(self.style().standardIcon(QStyle.SP_TrashIcon))
        self.btn_delete.setMinimumWidth(90)
        self.btn_delete.clicked.connect(self._delete_product)

        bar.addWidget(self.ed_search, 3)
        bar.addWidget(self.cb_category, 0)
        bar.addStretch(1)

        row2 = QHBoxLayout()
        row2.setContentsMargins(0, 0, 0, 0)
        row2.setSpacing(8)
        row2.addWidget(self.btn_categories)
        row2.addStretch(1)
        row2.addWidget(self.btn_add)
        row2.addWidget(self.btn_edit)
        row2.addWidget(self.btn_delete)

        v.addLayout(bar)
        v.addLayout(row2)
        return wrapper

    def _build_table(self) -> QTableView:
        self.model = QStandardItemModel(0, 8, self)
        self._set_table_headers()

        self.proxy = QSortFilterProxyModel(self)
        self.proxy.setSourceModel(self.model)
        self.proxy.setFilterCaseSensitivity(Qt.CaseInsensitive)

        table = QTableView()
        table.setObjectName("ProductsTable")
        table.setModel(self.proxy)
        table.setItemDelegate(NumericAlignDelegate(table))
        table.setSortingEnabled(True)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableView.SelectRows)
        table.setSelectionMode(QTableView.SingleSelection)
        table.setEditTriggers(QTableView.NoEditTriggers)
        header = table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(self.COL_REF, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(self.COL_CATEGORY, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(self.COL_DESC, QHeaderView.Stretch)
        header.setSectionResizeMode(self.COL_UNIT, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(self.COL_COST, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(self.COL_MARGIN, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(self.COL_PRICE, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(self.COL_ACTIVE, QHeaderView.ResizeToContents)
        table.verticalHeader().setVisible(False)

        self.table = table

        self._load_products()
        return table

    def _load_products(self) -> None:
        self.model.setRowCount(0)
        with get_session() as session:
            rows = session.query(Product).order_by(Product.ref.asc()).all()
            for r in rows:
                self.model.appendRow(
                    self._row_to_items(
                        ProductRow(
                            ref=r.ref,
                            category=r.category.name if r.category else "Sin categoria",
                            category_id=r.category_id,
                            desc=r.short_desc or "",
                            unit=r.unit or "",
                            cost=float(r.cost or 0),
                            margin=float(r.margin or 0),
                            price=float(r.sale_price or 0),
                            active=bool(r.active),
                        )
                    )
                )

    def _row_to_items(self, row: ProductRow) -> list[QStandardItem]:
        items = [
            QStandardItem(row.ref),
            QStandardItem(row.category),
            QStandardItem(row.desc),
            QStandardItem(row.unit),
            QStandardItem(f"{row.cost:.2f}"),
            QStandardItem(f"{row.margin:.2f}"),
            QStandardItem(f"{row.price:.2f}"),
            QStandardItem(t("active") if row.active else t("inactive")),
        ]
        items[self.COL_CATEGORY].setData(row.category_id, Qt.UserRole)

        color = Qt.darkGreen if row.active else Qt.gray
        items[self.COL_ACTIVE].setForeground(color)
        for col in (self.COL_COST, self.COL_MARGIN, self.COL_PRICE):
            items[col].setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        return items

    def _apply_filters(self) -> None:
        search = self.ed_search.text().strip().lower()
        cat_value = self.cb_category.currentData()

        for row in range(self.model.rowCount()):
            ref = self.model.item(row, self.COL_REF).text().lower()
            desc = self.model.item(row, self.COL_DESC).text().lower()
            row_cat_id = self.model.item(row, self.COL_CATEGORY).data(Qt.UserRole)

            matches_search = (not search) or (search in ref) or (search in desc)
            matches_cat = (cat_value is None) or (row_cat_id == cat_value)

            is_visible = matches_search and matches_cat
            self.table.setRowHidden(self.proxy.mapFromSource(self.model.index(row, 0)).row(), not is_visible)

    def apply_cost_visibility(self, show: bool) -> None:
        self.table.setColumnHidden(self.COL_COST, not show)
        self.table.setColumnHidden(self.COL_MARGIN, not show)

    def _open_new_dialog(self) -> None:
        dlg = ProductDialog(self)
        if dlg.exec() != QDialog.Accepted:
            return
        data = dlg.values()
        if not data["ref"]:
            QMessageBox.warning(self, t("product"), f"{t('ref')} {t('required')}")
            return
        with get_session() as session:
            if session.query(Product).filter(Product.ref == data["ref"]).first() is not None:
                QMessageBox.warning(self, t("product"), f"{t('ref')} {t('duplicate_ref')}")
                return
            product = Product(ref=data["ref"])
            _apply_product_values(product, data)
            session.add(product)
            session.commit()
        self._load_products()

    def _open_edit_dialog(self) -> None:
        ref = self._selected_ref()
        if not ref:
            QMessageBox.information(self, t("product"), t("select_product"))
            return
        with get_session() as session:
            product = session.query(Product).filter(Product.ref == ref).first()
            if product is None:
                return
            dlg = ProductDialog(self, initial=product)
            if dlg.exec() != QDialog.Accepted:
                return
            data = dlg.values()
            if not data["ref"]:
                QMessageBox.warning(self, t("product"), f"{t('ref')} {t('required')}")
                return
            # allow updating ref if unique
            if data["ref"] != product.ref:
                if session.query(Product).filter(Product.ref == data["ref"]).first() is not None:
                    QMessageBox.warning(self, t("product"), f"{t('ref')} {t('duplicate_ref')}")
                    return
                product.ref = data["ref"]
            _apply_product_values(product, data)
            session.commit()
        self._load_products()

    def _delete_product(self) -> None:
        ref = self._selected_ref()
        if not ref:
            QMessageBox.information(self, t("product"), t("select_product"))
            return
        if QMessageBox.question(
            self,
            t("confirm"),
            f"{t('delete')} {ref}?",
            QMessageBox.Yes | QMessageBox.No,
        ) != QMessageBox.Yes:
            return
        with get_session() as session:
            product = session.query(Product).filter(Product.ref == ref).first()
            if product is None:
                return
            session.delete(product)
            session.commit()
        self._load_products()

    # export/import moved to Herramientas

    def _refresh_filters(self) -> None:
        self.cb_category.blockSignals(True)
        self.cb_category.clear()
        self.cb_category.addItem(t("all_categories"), None)
        with get_session() as session:
            categories = session.query(ProductCategory).all()
            categories = _sort_categories(categories)
            for c in categories:
                label = f"{c.code} - {c.name}" if c.code else c.name
                self.cb_category.addItem(label, c.id)
        self.cb_category.blockSignals(False)

    def _manage_categories(self) -> None:
        dlg = _ListCrudDialog(self, t("categories"), ProductCategory)
        if dlg.exec() == QDialog.Accepted:
            self._refresh_filters()

    def _set_table_headers(self) -> None:
        self.model.setHorizontalHeaderLabels(
            [
                t("ref"),
                t("category"),
                t("description"),
                t("unit"),
                t("cost"),
                t("margin"),
                t("sale_price"),
                t("active"),
            ]
        )

    def _reload_texts(self, _lang: str) -> None:
        self.title.setText(tu("products"))
        self.ed_search.setPlaceholderText(t("search"))
        self.btn_categories.setText(tu("categories"))
        self.btn_add.setText(tu("new"))
        self.btn_edit.setText(tu("edit"))
        self.btn_delete.setText(tu("delete"))
        self._set_table_headers()
        # refresh active/inactive labels
        self._load_products()
        self._refresh_filters()

    def _reload_catalog(self) -> None:
        self._load_products()
        self._refresh_filters()

    def _selected_ref(self) -> str | None:
        indexes = self.table.selectionModel().selectedRows()
        if not indexes:
            return None
        source_index = self.proxy.mapToSource(indexes[0])
        return self.model.item(source_index.row(), self.COL_REF).text()


def _normalize_margin(value: float) -> float:
    if value > 1:
        return value / 100.0
    return value


def _apply_product_values(product: Product, data: dict) -> None:
    product.ref = data["ref"]
    product.category_id = data["category_id"] or _default_category_id()
    product.short_desc = data["desc"]
    product.unit = data["unit"]
    product.cost = data["cost"]
    margin = _normalize_margin(data["margin"])
    product.margin = margin
    product.fixed_price = data["fixed"]
    if product.fixed_price:
        product.sale_price = data["price"]
    else:
        product.sale_price = product.cost * (1 + margin)
    product.active = data["active"]


def _default_category_id() -> int | None:
    with get_session() as session:
        cat = _default_category(session)
        return cat.id if cat else None


def _default_category(session) -> ProductCategory | None:
    return session.query(ProductCategory).filter(ProductCategory.name == "Sin categoria").first()


def _sort_categories(categories: list[ProductCategory]) -> list[ProductCategory]:
    def key(cat: ProductCategory) -> tuple[int, str, str]:
        is_default = 0 if (cat.code or "").upper() == "SIN" or cat.name == "Sin categoria" else 1
        code = (cat.code or "").upper()
        name = cat.name.upper()
        return (is_default, code, name)

    return sorted(categories, key=key)


def _code_from_name(name: str) -> str:
    base = "".join([c for c in name.upper() if c.isalnum()])[:3]
    return base or "CAT"


class _ListCrudDialog(QDialog):
    def __init__(self, parent: QWidget, title: str, model_cls) -> None:
        super().__init__(parent)
        self.model_cls = model_cls
        self.setWindowTitle(title)
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        self.lbl_selected = QLabel(f"{t('selected')}: -")
        layout.addWidget(self.lbl_selected)

        self.ed_code = QLineEdit()
        self.ed_code.setPlaceholderText(t("code"))
        self.ed_code.setMaxLength(10)
        layout.addWidget(self.ed_code)

        self.ed_name = QLineEdit()
        self.ed_name.setPlaceholderText(t("name"))
        layout.addWidget(self.ed_name)

        self.list = QTableView()
        self.model = QStandardItemModel(0, 3, self)
        self.model.setHorizontalHeaderLabels(["ID", t("code"), t("name")])
        self.list.setModel(self.model)
        self.list.setSelectionBehavior(QTableView.SelectRows)
        self.list.setSelectionMode(QTableView.SingleSelection)
        self.list.setEditTriggers(QTableView.NoEditTriggers)
        self.list.setColumnHidden(0, True)
        self.list.horizontalHeader().setStretchLastSection(True)
        self.list.verticalHeader().setVisible(False)
        self.list.selectionModel().selectionChanged.connect(self._on_select)
        layout.addWidget(self.list, 1)

        btn_row = QHBoxLayout()
        self.btn_create = QPushButton(tu("create"))
        self.btn_update = QPushButton(tu("update"))
        self.btn_del = QPushButton(tu("delete"))
        self.btn_clear = QPushButton(tu("clear"))
        btn_close = QPushButton(tu("close") if t("close") else "CERRAR")
        self.btn_create.clicked.connect(self._add)
        self.btn_update.clicked.connect(self._edit)
        self.btn_del.clicked.connect(self._delete)
        self.btn_clear.clicked.connect(self._clear_selection)
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(self.btn_create)
        btn_row.addWidget(self.btn_update)
        btn_row.addWidget(self.btn_del)
        btn_row.addWidget(self.btn_clear)
        btn_row.addStretch(1)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

        self._load()
        self._update_action_state()

    def _load(self) -> None:
        self.model.setRowCount(0)
        with get_session() as session:
            rows = session.query(self.model_cls).all()
            rows = _sort_categories(rows)
            for r in rows:
                self.model.appendRow([QStandardItem(str(r.id)), QStandardItem(r.code or ""), QStandardItem(r.name)])

    def _selected_id(self) -> int | None:
        indexes = self.list.selectionModel().selectedRows()
        if not indexes:
            return None
        value = self.model.item(indexes[0].row(), 0).text()
        return int(value)

    def _on_select(self) -> None:
        item_id = self._selected_id()
        if item_id is None:
            self.lbl_selected.setText(f"{t('selected')}: -")
            self._update_action_state()
            return
        row = self.list.selectionModel().selectedRows()[0].row()
        code = self.model.item(row, 1).text()
        name = self.model.item(row, 2).text()
        self.ed_code.setText(code)
        self.ed_name.setText(name)
        self.lbl_selected.setText(f"{t('selected')}: {code} - {name}")
        self._update_action_state()

    def _clear_selection(self) -> None:
        self.list.clearSelection()
        self.ed_code.clear()
        self.ed_name.clear()
        self.lbl_selected.setText(f"{t('selected')}: -")
        self._update_action_state()

    def _add(self) -> None:
        code = self.ed_code.text().strip().upper()
        name = self.ed_name.text().strip()
        if not name:
            return
        if not code:
            code = _code_from_name(name)
        with get_session() as session:
            if session.query(self.model_cls).filter(self.model_cls.code == code).first() is not None:
                QMessageBox.information(self, t("warning"), t("category_exists"))
                return
            if session.query(self.model_cls).filter(self.model_cls.name == name).first() is not None:
                QMessageBox.information(self, t("warning"), t("category_exists"))
                return
            session.add(self.model_cls(code=code, name=name))
            session.commit()
        self.ed_name.clear()
        self.ed_code.clear()
        self._load()

    def _edit(self) -> None:
        item_id = self._selected_id()
        if item_id is None:
            return
        code = self.ed_code.text().strip().upper()
        name = self.ed_name.text().strip()
        if not name:
            return
        if not code:
            code = _code_from_name(name)
        with get_session() as session:
            obj = session.get(self.model_cls, item_id)
            if obj is None:
                return
            if obj.name in {"Sin categoria"} or (obj.code or "").upper() == "SIN":
                QMessageBox.information(self, t("warning"), t("default_protected_edit"))
                return
            if session.query(self.model_cls).filter(self.model_cls.code == code, self.model_cls.id != obj.id).first():
                QMessageBox.information(self, t("warning"), t("category_exists"))
                return
            if session.query(self.model_cls).filter(self.model_cls.name == name, self.model_cls.id != obj.id).first():
                QMessageBox.information(self, t("warning"), t("category_exists"))
                return
            obj.code = code
            obj.name = name
            session.commit()
        self.ed_name.clear()
        self.ed_code.clear()
        self._load()

    def _delete(self) -> None:
        item_id = self._selected_id()
        if item_id is None:
            return
        with get_session() as session:
            obj = session.get(self.model_cls, item_id)
            if obj is None:
                return
            # Protect default entries
            if obj.name in {"Sin categoria"} or (obj.code or "").upper() == "SIN":
                QMessageBox.information(self, t("warning"), t("default_protected_delete"))
                return
            default_cat = _default_category(session)
            default_id = default_cat.id if default_cat else None
            # Reassign products using deleted type/category
            from db.models import Product

            updated = 0
            if default_id is not None:
                updated = session.query(Product).filter(Product.category_id == obj.id).update({"category_id": default_id})
            session.delete(obj)
            session.commit()
        if updated:
            QMessageBox.information(
                self,
                t("warning"),
                f"{t('reassigned_products')} 'Sin categoria': {updated}",
            )
        self._load()
        self._clear_selection()

    def _update_action_state(self) -> None:
        has_selection = self._selected_id() is not None
        self.btn_update.setEnabled(has_selection)
        self.btn_del.setEnabled(has_selection)
