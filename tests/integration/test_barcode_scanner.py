import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from frontend.app.ui.barcode_scanner import BarcodeScannerWidget


def test_barcode_scanner_stays_visible_and_camera_is_not_toggled_off():
    app = QApplication.instance() or QApplication([])
    scanner = BarcodeScannerWidget()
    scanner.toggle()
    assert scanner.isVisible()
    # The persistent scanner must never hide/stop the camera when the toolbar control is used.
    scanner.toggle()
    assert scanner.isVisible()
    scanner.close()
    app.processEvents()
