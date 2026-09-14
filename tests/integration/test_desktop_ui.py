import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from frontend.app.ui.main_window import MainWindow


def test_main_window_builds_in_offscreen_mode():
    app = QApplication.instance() or QApplication([])
    window = MainWindow()

    assert window.windowTitle() == "نظام إدارة البقالات"
    assert window.isRightToLeft()

    window.close()
    app.processEvents()
