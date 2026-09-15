from __future__ import annotations

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QFont, QFontDatabase, QRawFont
from PySide6.QtWidgets import QApplication, QLabel

from frontend.app.ui.font_setup import setup_application_font


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    family = setup_application_font(app)
    if not family:
        raise RuntimeError("No Arabic-capable Qt font was selected")

    font = QFont(family, 18)
    raw = QRawFont.fromFont(font)
    if not raw.isValid():
        raise RuntimeError(f"Selected font is not valid: {family}")

    sample = "نظام إدارة البقالات"
    glyphs = raw.glyphIndexesForString(sample)
    if not glyphs or all(glyph == 0 for glyph in glyphs):
        raise RuntimeError(f"Selected font cannot map Arabic glyphs: {family}")

    label = QLabel(sample)
    label.setFont(font)
    label.resize(640, 80)
    label.show()
    app.processEvents()
    label.grab().save("build_docs/arabic-font-smoke.png")
    print(f"Arabic font verified: family={family!r}, glyphs={glyphs}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
