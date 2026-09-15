from __future__ import annotations

from time import monotonic

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtMultimedia import QCamera, QMediaCaptureSession, QMediaDevices, QVideoFrame, QVideoSink
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

try:
    import numpy as np
    from pyzbar.pyzbar import decode as decode_barcodes
except Exception:
    np = None
    decode_barcodes = None


class BarcodeScannerWidget(QFrame):
    """Persistent camera scanner: it stays visible and the camera remains running."""

    barcode_detected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("barcodeScanner")
        self.setFixedSize(270, 205)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self._camera: QCamera | None = None
        self._session = QMediaCaptureSession()
        self._sink = QVideoSink(self)
        self._session.setVideoSink(self._sink)
        self._last_code = ""
        self._last_code_at = 0.0
        self._build()
        self._sink.videoFrameChanged.connect(self._on_frame)
        QTimer.singleShot(0, self.start_camera)

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(7, 7, 7, 7)
        root.setSpacing(4)
        header = QHBoxLayout()
        title = QLabel("📷 قارئ الباركود — مستمر")
        title.setObjectName("scannerTitle")
        self.status = QLabel("جاري تشغيل الكاميرا...")
        self.status.setObjectName("scannerStatus")
        header.addWidget(title)
        header.addStretch()
        root.addLayout(header)
        self.preview = QLabel("جاري تجهيز الكاميرا...")
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setMinimumHeight(130)
        self.preview.setObjectName("scannerPreview")
        root.addWidget(self.preview, 1)
        self.code_label = QLabel("الباركود: —")
        self.code_label.setObjectName("scannerCode")
        root.addWidget(self.code_label)

    def start_camera(self):
        if self._camera is not None:
            return
        devices = QMediaDevices.videoInputs()
        if not devices:
            self.status.setText("لا توجد كاميرا")
            return
        self._camera = QCamera(devices[0], self)
        self._session.setCamera(self._camera)
        self._camera.errorOccurred.connect(self._camera_error)
        self._camera.start()
        self.status.setText("الكاميرا تعمل — جاهز للمسح المستمر")

    def _camera_error(self, _error, message):
        self.status.setText(message or "خطأ في الكاميرا")

    def _on_frame(self, frame: QVideoFrame):
        if not frame.isValid():
            return
        image = frame.toImage()
        if image.isNull():
            return
        image = image.convertToFormat(QImage.Format_RGB888)
        self.preview.setPixmap(QPixmap.fromImage(image).scaled(self.preview.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        if np is None or decode_barcodes is None:
            self.status.setText("قارئ الباركود غير مثبت")
            return
        try:
            array = np.frombuffer(image.bits(), dtype=np.uint8)
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
        now = monotonic()
        if code == self._last_code and now - self._last_code_at < 0.45:
            return
        self._last_code = code
        self._last_code_at = now
        self.code_label.setText(f"الباركود: {code}")
        self.status.setText("تمت القراءة — مستمر")
        self.barcode_detected.emit(code)

    def toggle(self):
        """Keep the camera open; clicking the toolbar button only brings it to the front."""
        self.show()
        self.raise_()
        self.start_camera()

    def close_camera(self):
        if self._camera is not None:
            self._camera.stop()
            self._camera.deleteLater()
            self._camera = None

    def closeEvent(self, event):
        self.close_camera()
        super().closeEvent(event)
