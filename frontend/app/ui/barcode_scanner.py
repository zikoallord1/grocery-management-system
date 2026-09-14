from __future__ import annotations

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtMultimedia import QCamera, QCameraDevice, QMediaCaptureSession, QVideoFrame, QVideoSink
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

try:
    import numpy as np
    from pyzbar.pyzbar import decode as decode_barcodes
except Exception:  # Optional at import time so the desktop app can still open without scanner deps.
    np = None
    decode_barcodes = None


class BarcodeScannerWidget(QFrame):
    """Compact always-ready camera barcode scanner for the desktop/tablet UI."""

    barcode_detected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("barcodeScanner")
        self.setFixedSize(270, 205)
        self.setWindowFlags(Qt.Widget | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self._camera: QCamera | None = None
        self._session = QMediaCaptureSession()
        self._sink = QVideoSink(self)
        self._session.setVideoSink(self._sink)
        self._last_code = ""
        self._last_emit_ms = 0
        self._build()
        self._sink.videoFrameChanged.connect(self._on_frame)
        QTimer.singleShot(0, self.start_camera)

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(7, 7, 7, 7)
        root.setSpacing(4)
        header = QHBoxLayout()
        title = QLabel("📷 قارئ الباركود")
        title.setObjectName("scannerTitle")
        self.status = QLabel("جاري تشغيل الكاميرا...")
        self.status.setObjectName("scannerStatus")
        header.addWidget(title)
        header.addStretch()
        close = QPushButton("×")
        close.setFixedSize(28, 28)
        close.clicked.connect(self.hide)
        header.addWidget(close)
        root.addLayout(header)
        self.preview = QLabel("الكاميرا غير متاحة")
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setMinimumHeight(130)
        self.preview.setObjectName("scannerPreview")
        root.addWidget(self.preview, 1)
        self.code_label = QLabel("الباركود: —")
        self.code_label.setObjectName("scannerCode")
        root.addWidget(self.code_label)

    def start_camera(self):
        devices = QCameraDevice.videoInputs()
        if not devices:
            self.status.setText("لا توجد كاميرا")
            return
        device = devices[0]
        self._camera = QCamera(device, self)
        self._session.setCamera(self._camera)
        self._camera.errorOccurred.connect(lambda _error, message: self.status.setText(message or "خطأ في الكاميرا"))
        self._camera.start()
        self.status.setText("جاهز للمسح")

    def _on_frame(self, frame: QVideoFrame):
        if not frame.isValid():
            return
        image = frame.toImage()
        if image.isNull():
            return
        image = image.convertToFormat(QImage.Format_RGB888)
        self.preview.setPixmap(QPixmap.fromImage(image).scaled(
            self.preview.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        ))
        if np is None or decode_barcodes is None:
            self.status.setText("قارئ الباركود غير مثبت")
            return
        try:
            bits = image.bits()
            array = np.frombuffer(bits, dtype=np.uint8)
            array = array.reshape((image.height(), image.bytesPerLine()))[:, : image.width() * 3]
            array = array.reshape((image.height(), image.width(), 3))
            results = decode_barcodes(array)
        except Exception:
            return
        if not results:
            return
        code = results[0].data.decode("utf-8", errors="ignore").strip()
        if not code:
            return
        now = QTimer().remainingTime()  # placeholder-free monotonic gate below
        del now
        if code == self._last_code:
            return
        self._last_code = code
        self.code_label.setText(f"الباركود: {code}")
        self.status.setText("تمت القراءة")
        self.barcode_detected.emit(code)
        QTimer.singleShot(1200, self._clear_last_code)

    def _clear_last_code(self):
        self._last_code = ""

    def toggle(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.raise_()
            if self._camera is None:
                self.start_camera()

    def close_camera(self):
        if self._camera is not None:
            self._camera.stop()
            self._camera.deleteLater()
            self._camera = None

    def closeEvent(self, event):
        self.close_camera()
        super().closeEvent(event)
