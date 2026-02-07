from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QStyle,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtGui import QPixmap, QPainter, QPen, QIcon

from ui.backups_view import BackupsView
from ui.clients_view import ClientsView
from ui.company_settings_view import CompanySettingsView
from ui.products_view import ProductsView
from ui.quotes_view import QuotesView
from ui.tools_view import ToolsView
from ui.i18n import t, tu
from settings import Settings


@dataclass(frozen=True)
class NavItem:
    key: str
    label: str
    icon: QStyle.StandardPixmap


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ORZALAN")
        self.setMinimumSize(900, 600)
        theme = Settings.load().get("theme", "light")
        self.setProperty("theme", theme)

        self._collapsed = False
        self._expanded_width = 220
        self._collapsed_width = 60

        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._sidebar = self._build_sidebar()
        self._stack = self._build_stack()
        self._topbar = self._build_topbar()

        root.addWidget(self._sidebar)
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        right_layout.addWidget(self._topbar)
        right_layout.addWidget(self._stack, 1)
        root.addWidget(right, 1)
        self.setCentralWidget(central)
        self._apply_logo()

        if self._nav.count() > 0:
            self._nav.setCurrentRow(0)
            self._on_nav_changed(0)

        from ui.i18n import t
        self.statusBar().showMessage(t("ready"))
        from ui.app_events import app_events
        app_events.language_changed.connect(self._reload_texts)

    def _build_sidebar(self) -> QWidget:
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(self._expanded_width)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(10)

        self._btn_toggle = QPushButton()
        self._btn_toggle.setObjectName("SidebarToggle")
        self._btn_toggle.setCursor(Qt.PointingHandCursor)
        self._btn_toggle.clicked.connect(self._toggle_sidebar)
        self._btn_toggle.setFixedSize(32, 32)
        self._btn_toggle.setIconSize(self._btn_toggle.size())
        self._update_toggle_icon()

        self._title = QLabel("")
        self._title.setObjectName("SidebarTitle")
        self._title.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        self._title.setMinimumHeight(48)
        self._title.setSizePolicy(self._title.sizePolicy().horizontalPolicy(), self._title.sizePolicy().verticalPolicy())
        logo_path = (Path(__file__).resolve().parents[1] / "assets" / "logo_orzalan.png")
        if logo_path.exists():
            self._logo_pix = QPixmap(str(logo_path))
        else:
            self._title.setText("ORZALAN")

        header.addWidget(self._btn_toggle, 0)
        header.addWidget(self._title, 1)
        layout.addLayout(header)

        self._nav = QListWidget()
        self._nav.setObjectName("NavList")
        self._nav.setSelectionMode(QAbstractItemView.SingleSelection)
        self._nav.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._nav.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._nav.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self._nav.setSpacing(2)

        for item in self._nav_items():
            self._nav.addItem(self._make_nav_item(item))

        self._nav.currentRowChanged.connect(self._on_nav_changed)

        self._nav.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        if self._nav.count() > 0:
            row_h = self._nav.sizeHintForRow(0)
            if row_h <= 0:
                row_h = 36
            total_h = (row_h * self._nav.count()) + (self._nav.spacing() * (self._nav.count() - 1)) + 24
            self._nav.setMinimumHeight(total_h)
            self._nav.setMaximumHeight(total_h)
        layout.addWidget(self._nav, 0)
        layout.addStretch(1)
        footer = QWidget()
        footer_layout = QVBoxLayout(footer)
        footer_layout.setContentsMargins(0, 8, 0, 0)
        footer_layout.setSpacing(4)
        self._lbl_credits = QLabel("Autor: Javier Feijóo\nDocente Informática")
        self._lbl_credits.setObjectName("SidebarCredits")
        self._lbl_credits.setWordWrap(True)
        self._lbl_repo = QLabel(
            '<a href="https://github.com/javier-feijoo/orzalan">Manual de ayuda</a>'
        )
        self._lbl_repo.setObjectName("SidebarLink")
        self._lbl_repo.setOpenExternalLinks(True)
        self._lbl_license = QLabel(
            '<a href="https://creativecommons.org/licenses/by-nc-sa/4.0/">Licencia CC BY-NC-SA 4.0</a>'
        )
        self._lbl_license.setObjectName("SidebarLink")
        self._lbl_license.setOpenExternalLinks(True)
        footer_layout.addWidget(self._lbl_credits)
        footer_layout.addWidget(self._lbl_repo)
        footer_layout.addWidget(self._lbl_license)
        layout.addWidget(footer)
        return sidebar

    def _build_stack(self) -> QStackedWidget:
        stack = QStackedWidget()
        stack.setObjectName("MainStack")

        for item in self._nav_items():
            page = self._build_page(item.key)
            page.setObjectName(f"Page_{item.key}")
            stack.addWidget(page)

        return stack

    def _build_topbar(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("TopBar")
        layout = QVBoxLayout(bar)
        layout.setContentsMargins(18, 10, 18, 8)
        layout.setSpacing(2)

        self._section_title = QLabel("")
        self._section_title.setObjectName("TopBarTitle")
        self._section_title.setStyleSheet("font-weight: 800; font-size: 24px; letter-spacing: 0.8px;")
        self._section_subtitle = QLabel("")
        self._section_subtitle.setObjectName("TopBarSubtitle")
        self._section_subtitle.setStyleSheet("font-size: 12px;")

        layout.addWidget(self._section_title)
        layout.addWidget(self._section_subtitle)
        return bar

    def _build_page(self, key: str) -> QWidget:
        if key == "catalog":
            return ProductsView()
        if key == "clients":
            return ClientsView()
        if key == "quotes":
            return QuotesView()
        if key == "tools":
            return ToolsView()
        if key == "settings":
            return CompanySettingsView()
        if key == "backups":
            return BackupsView()
        return QWidget()

    def _nav_items(self) -> list[NavItem]:
        return [
            NavItem("catalog", t("catalog"), QStyle.SP_DirIcon),
            NavItem("clients", t("clients"), QStyle.SP_FileDialogInfoView),
            NavItem("quotes", t("quotes"), QStyle.SP_FileDialogListView),
            NavItem("tools", t("tools"), QStyle.SP_ArrowDown),
            NavItem("settings", t("settings"), QStyle.SP_FileDialogDetailedView),
            NavItem("backups", t("backups"), QStyle.SP_DriveFDIcon),
        ]

    def _make_nav_item(self, item: NavItem) -> QListWidgetItem:
        icon = self.style().standardIcon(item.icon)
        w_item = QListWidgetItem(icon, item.label)
        w_item.setData(Qt.UserRole, item.label)
        w_item.setSizeHint(w_item.sizeHint())
        return w_item

    def _toggle_sidebar(self) -> None:
        self._collapsed = not self._collapsed
        self._apply_sidebar_state()

    def _apply_sidebar_state(self) -> None:
        if self._collapsed:
            self._sidebar.setFixedWidth(self._collapsed_width)
            self._title.hide()
            for i in range(self._nav.count()):
                item = self._nav.item(i)
                item.setText("")
        else:
            self._sidebar.setFixedWidth(self._expanded_width)
            self._title.show()
            self._apply_logo()
            for i in range(self._nav.count()):
                item = self._nav.item(i)
                item.setText(item.data(Qt.UserRole))
        self._update_toggle_icon()

    def _update_toggle_icon(self) -> None:
        self._btn_toggle.setIcon(self._hamburger_icon())
        self._btn_toggle.setToolTip(f"{t('show')}/{t('hide')} {t('menu').lower()}")

    def _hamburger_icon(self) -> QIcon:
        size = 18
        pix = QPixmap(size, size)
        pix.fill(Qt.transparent)
        painter = QPainter(pix)
        pen = QPen(self.palette().color(self.foregroundRole()))
        pen.setWidth(2)
        pen.setCapStyle(Qt.RoundCap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(pen)
        for y in (4, 9, 14):
            painter.drawLine(3, y, 15, y)
        painter.end()
        return QIcon(pix)

    def _apply_logo(self) -> None:
        if not hasattr(self, "_logo_pix"):
            return
        if self._collapsed:
            return
        available_w = max(self._sidebar.width() if hasattr(self, "_sidebar") else 220, 220)
        available_w = max(available_w - self._btn_toggle.width() - 24, 60)
        scaled = self._logo_pix.scaledToWidth(available_w, Qt.SmoothTransformation)
        self._title.setPixmap(scaled)

    def _on_nav_changed(self, index: int) -> None:
        if index < 0:
            return
        self._stack.setCurrentIndex(index)
        item = self._nav.item(index)
        label = item.data(Qt.UserRole)
        from ui.i18n import t
        self.statusBar().showMessage(f"{t('section')}: {label}")
        items = self._nav_items()
        if index < len(items):
            self._update_section_header(items[index].key)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._apply_logo()

    def _reload_texts(self, _lang: str) -> None:
        from ui.i18n import t
        self._btn_toggle.setText("")
        # Sidebar labels
        items = self._nav_items()
        for i, nav in enumerate(items):
            if i < self._nav.count():
                item = self._nav.item(i)
                item.setText(nav.label if not self._collapsed else "")
                item.setData(Qt.UserRole, nav.label)
        # Status bar
        self.statusBar().showMessage(t("ready"))
        if hasattr(self, "_lbl_repo"):
            self._lbl_repo.setText(f'<a href="https://github.com/javier-feijoo/orzalan">{t("open_repo")}</a>')
        if hasattr(self, "_lbl_license"):
            self._lbl_license.setText(
                '<a href="https://creativecommons.org/licenses/by-nc-sa/4.0/">Licencia CC BY-NC-SA 4.0</a>'
            )
        current = self._nav.currentRow()
        if current >= 0 and current < len(items):
            self._update_section_header(items[current].key)

    def _update_section_header(self, key: str) -> None:
        title_key = f"section_{key}"
        subtitle_key = f"subtitle_{key}"
        self._section_title.setText(tu(title_key))
        self._section_subtitle.setText(t(subtitle_key))
