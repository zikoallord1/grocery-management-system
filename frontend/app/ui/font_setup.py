from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication


PREFERRED_FONTS = (
    "Noto Sans Arabic",
    "Noto Sans Arabic UI",
    "Segoe UI",
    "Tahoma",
    "Arial",
    "DejaVu Sans",
)


def setup_application_font(app: QApplication | None = None) -> str:
    """Select a clear Arabic-capable font for the whole Qt application."""
    app = app or QApplication.instance()
    if app is None:
        return ""

    families = set(QFontDatabase.families())
    family = next((name for name in PREFERRED_FONTS if name in families), "")

    if not family:
        # Keep a deterministic fallback even on minimal/offscreen Linux images.
        family = "Sans Serif"

    font = QFont(family)
    font.setStyleStrategy(QFont.PreferAntialias | QFont.PreferQuality)
    app.setFont(font)
    return family
