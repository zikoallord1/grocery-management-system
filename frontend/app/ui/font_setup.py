from __future__ import annotations

import re
import sys
from pathlib import Path

from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication, QWidget


FONT_FILENAME = "NotoSansArabic-Regular.ttf"
FONT_FAMILY = "Noto Sans Arabic"
_FONT_FAMILY_RULE = re.compile(r"font-family\s*:\s*[^;]+;", re.IGNORECASE)


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
        family = bundled_family
    else:
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


def apply_font_to_window(window: QWidget, app: QApplication | None = None) -> str:
    """Apply the selected Arabic font after a window stylesheet has been created.

    Qt widget stylesheets can override QApplication.setFont().  The previous
    release used a stylesheet-level font-family rule, which caused Arabic to
    fall back to a font without the required glyphs on the documentation and
    packaged builds.  Remove only those font-family declarations and then set
    the selected font explicitly on the window and its existing children.
    """
    family = setup_application_font(app)
    if not family:
        return ""

    sheet = window.styleSheet()
    if sheet:
        cleaned = _FONT_FAMILY_RULE.sub("", sheet)
        if cleaned != sheet:
            window.setStyleSheet(cleaned)

    font = QFont(family)
    font.setStyleStrategy(QFont.PreferAntialias | QFont.PreferQuality)
    window.setFont(font)
    for child in window.findChildren(QWidget):
        child.setFont(font)
    return family
