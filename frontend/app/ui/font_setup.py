from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication


FONT_FILENAME = "NotoSansArabic-Regular.ttf"
FONT_FAMILY = "Noto Sans Arabic"


def bundled_font_path() -> Path:
    """Return the bundled Arabic font path, including PyInstaller builds."""
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    else:
        base = Path(__file__).resolve().parents[1]
    return base / "assets" / "fonts" / FONT_FILENAME


def load_bundled_arabic_font() -> str:
    """Register the bundled Noto Sans Arabic font with Qt."""
    path = bundled_font_path()
    if not path.is_file():
        return ""
    font_id = QFontDatabase.addApplicationFont(str(path))
    if font_id < 0:
        return ""
    families = QFontDatabase.applicationFontFamilies(font_id)
    return families[0] if families else FONT_FAMILY


def setup_application_font(app: QApplication | None = None) -> str:
    """Use bundled Noto Sans Arabic first, then fall back to installed fonts."""
    app = app or QApplication.instance()
    if app is None:
        return ""

    bundled_family = load_bundled_arabic_font()
    if bundled_family:
        font = QFont(bundled_family)
        font.setStyleStrategy(QFont.PreferAntialias | QFont.PreferQuality)
        app.setFont(font)
        return bundled_family

    families = set(QFontDatabase.families())
    preferred = (
        FONT_FAMILY,
        "Noto Sans Arabic UI",
        "Segoe UI",
        "Tahoma",
        "Arial",
        "DejaVu Sans",
    )
    family = next((name for name in preferred if name in families), "Sans Serif")
    font = QFont(family)
    font.setStyleStrategy(QFont.PreferAntialias | QFont.PreferQuality)
    app.setFont(font)
    return family
