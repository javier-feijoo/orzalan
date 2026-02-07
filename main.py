import sys

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QLocale
from PySide6.QtGui import QIcon

from paths import ensure_portable_dirs, get_base_dir
from settings import Settings
from db import init_db
from ui.main_window import MainWindow


def _apply_qss(app: QApplication) -> None:
    base_dir = get_base_dir()
    qss_path = base_dir / "assets" / "styles.qss"
    if qss_path.exists():
        current = app.styleSheet()
        qss = qss_path.read_text(encoding="utf-8")
        app.setStyleSheet(f"{current}\n{qss}")


def _apply_material_theme(app: QApplication, settings: Settings) -> None:
    try:
        from qt_material import apply_stylesheet  # type: ignore
    except Exception:
        return

    theme = settings.get("theme", "light")
    if theme not in {"light", "dark"}:
        theme = "light"

    if theme == "dark":
        xml = "dark_blue.xml"
    else:
        xml = "light_blue.xml"

    apply_stylesheet(app, theme=xml)


def main() -> None:
    app = QApplication(sys.argv)

    ensure_portable_dirs()
    init_db()
    settings = Settings.load()

    lang = settings.get("idioma", "es")
    if lang == "gl":
        QLocale.setDefault(QLocale(QLocale.Galician, QLocale.Spain))
    else:
        QLocale.setDefault(QLocale(QLocale.Spanish, QLocale.Spain))

    _apply_material_theme(app, settings)
    _apply_qss(app)

    base_dir = get_base_dir()
    icon_path = base_dir / "assets" / "app_icon.ico"
    if not icon_path.exists():
        icon_path = base_dir / "assets" / "app_icon.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
