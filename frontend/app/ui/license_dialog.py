from __future__ import annotations

import shutil
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFileDialog, QFormLayout, QHBoxLayout, QLabel, QMessageBox, QPushButton, QVBoxLayout, QWidget

from backend.app.core.licensing import LICENSE_DIR, LICENSE_FILE, installation_id, verify_license


class LicenseDialog(QWidget):
    """Customer-side license information and activation dialog."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ترخيص نظام إدارة البقالات")
        self.resize(620, 420)
        self.setLayoutDirection(Qt.RightToLeft)
        self._build()
        self.refresh_status()

    def _build(self):
        root = QVBoxLayout(self)
        title = QLabel("ترخيص البرنامج")
        title.setStyleSheet("font-size:22px;font-weight:700;")
        root.addWidget(title)
        form = QFormLayout()
        self.installation = QLabel(installation_id())
        self.installation.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.status = QLabel()
        self.status.setWordWrap(True)
        self.customer = QLabel("—")
        self.store = QLabel("—")
        self.expiry = QLabel("—")
        form.addRow("معرّف التثبيت", self.installation)
        form.addRow("الحالة", self.status)
        form.addRow("العميل", self.customer)
        form.addRow("المنشأة", self.store)
        form.addRow("الانتهاء", self.expiry)
        root.addLayout(form)
        note = QLabel("أرسل معرّف التثبيت إلى مسؤول التراخيص. بعد استلام ملف license.json اختره من زر التفعيل.")
        note.setWordWrap(True)
        root.addWidget(note)
        buttons = QHBoxLayout()
        activate = QPushButton("تفعيل من ملف ترخيص")
        activate.clicked.connect(self.activate)
        refresh = QPushButton("تحديث الحالة")
        refresh.clicked.connect(self.refresh_status)
        buttons.addWidget(activate)
        buttons.addWidget(refresh)
        root.addLayout(buttons)
        root.addStretch()

    def refresh_status(self):
        status = verify_license()
        self.status.setText(status.message)
        self.customer.setText(status.customer_name or "—")
        self.store.setText(status.store_name or "—")
        self.expiry.setText(status.expires_at.isoformat() if status.expires_at else "—")
        self.status.setStyleSheet("color: #137333;" if status.usable else "color: #b3261e;")

    def activate(self):
        source, _ = QFileDialog.getOpenFileName(self, "اختيار ملف الترخيص", "", "License (*.json)")
        if not source:
            return
        try:
            LICENSE_DIR.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, LICENSE_FILE)
            status = verify_license()
            if not status.usable:
                QMessageBox.critical(self, "فشل التفعيل", status.message)
                return
            QMessageBox.information(self, "تم التفعيل", "تم تفعيل الترخيص بنجاح.")
            self.refresh_status()
        except Exception as exc:
            QMessageBox.critical(self, "خطأ", f"تعذر تثبيت ملف الترخيص: {exc}")
