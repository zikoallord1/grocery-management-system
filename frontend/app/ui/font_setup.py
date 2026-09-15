from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication


def setup_application_font(app: QApplication | None = None) -> str:
    """Select an installed Unicode/Arabic-capable font for the whole Qt application."""
    app = app or QApplication.instance()
    if app is None:
        return ""
    families = set(QFontDatabase.families())
    preferred = (
        "Noto Sans Arabic",
        "Noto Sans",
        "Segoe UI",
        "Tahoma",
        "Arial",
        "DejaVu Sans",
    )
    family = next((name for name in preferred if name in families), "")
    if family:
        font = QFont(family)
        font.setStyleStrategy(QFont.PreferQuality)
        app.setFont(font)
    return family
