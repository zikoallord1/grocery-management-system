from __future__ import annotations

from time import monotonic

from PySide6.QtCore import QTimer, Qt, Signal, QPoint
from PySide6.QtGui import QImage, QPixmap, QCursor
from PySide6.QtMultimedia import QCamera, QMediaCaptureSession, QMediaDevices, QVideoFrame, QVideoSink
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout

try:
    import numpy as np
    from pyzbar.pyzbar import decode as decode_barcodes
except Exception:
    np = None
    decode_barcodes = None


class BarcodeScannerWidget(QFrame):
    """Persistent camera scanner that can be freely moved with the mouse."""

    barcode_detected = Signal(str)
    moved_by_user = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("barcodeScanner")
        self.setFixedSize(270, 205)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setCursor(QCursor(Qt.OpenHandCursor))
        self._drag_start = QPoint()
        self._dragging = False
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

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._drag_start = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self.setCursor(QCursor(Qt.ClosedHandCursor))
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._dragging and event.buttons() & Qt.LeftButton:
            parent = self.parentWidget()
            if parent is not None:
                pos = event.globalPosition().toPoint() - self._drag_start
                local = parent.mapFromGlobal(pos)
                max_x = max(0, parent.width() - self.width())
                max_y = max(0, parent.height() - self.height())
                self.move(max(0, min(local.x(), max_x)), max(0, min(local.y(), max_y)))
                self.moved_by_user.emit()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._dragging:
            self._dragging = False
            self.setCursor(QCursor(Qt.OpenHandCursor))
            event.accept()
            return
        super().mouseReleaseEvent(event)

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
        """Show the scanner without resetting a position chosen by the user."""
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
