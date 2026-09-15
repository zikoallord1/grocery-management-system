from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QComboBox, QDateEdit, QFileDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QTextEdit, QVBoxLayout, QWidget

from backend.app.core.licensing import create_signed_license, generate_authority_keys
from frontend.app.ui.font_setup import setup_application_font

AUTHORITY_DIR = Path.home() / ".grocery_management_license_authority"


class LicenseManager(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("مدير تراخيص نظام إدارة البقالات")
        self.resize(760, 650)
        self.setLayoutDirection(Qt.RightToLeft)
        self.private_key_path, self.public_key_path = generate_authority_keys(AUTHORITY_DIR)
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        title = QLabel("مدير تراخيص نظام إدارة البقالات")
        title.setStyleSheet("font-size: 22px; font-weight: 700;")
        layout.addWidget(title)

        form = QFormLayout()
        self.installation_id = QLineEdit()
        self.customer_name = QLineEdit()
        self.store_name = QLineEdit()
        self.edition = QComboBox()
        self.edition.addItems(["Standard", "Professional", "Enterprise"])
        self.expiry = QDateEdit()
        self.expiry.setCalendarPopup(True)
        self.expiry.setDate(date.today())
        form.addRow("معرّف التثبيت", self.installation_id)
        form.addRow("اسم العميل", self.customer_name)
        form.addRow("اسم المتجر", self.store_name)
        form.addRow("الإصدار", self.edition)
        form.addRow("تاريخ الانتهاء", self.expiry)
        layout.addLayout(form)

        buttons = QHBoxLayout()
        create = QPushButton("إنشاء الترخيص")
        create.clicked.connect(self.create_license)
        show_public = QPushButton("عرض مفتاح التحقق العام")
        show_public.clicked.connect(self.show_public_key)
        export_public = QPushButton("تصدير مفتاح التحقق للنسخة")
        export_public.clicked.connect(self.export_public_key)
        buttons.addWidget(create)
        buttons.addWidget(show_public)
        buttons.addWidget(export_public)
        layout.addLayout(buttons)

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        layout.addWidget(self.output)
        self.output.setPlainText(
            "ملاحظة أمنية: مفتاح الإصدار الخاص يبقى على جهاز مدير التراخيص ولا يُرسل إلى العميل."
        )

    def create_license(self):
        if not self.installation_id.text().strip():
            QMessageBox.warning(self, "بيانات ناقصة", "أدخل معرّف التثبيت أولاً.")
            return
        payload, signature = create_signed_license(
            self.installation_id.text().strip(),
            self.customer_name.text().strip(),
            self.store_name.text().strip(),
            self.expiry.date().toPython().isoformat(),
            self.edition.currentText(),
            self.private_key_path,
        )
        license_data = dict(payload)
        license_data["signature"] = signature
        target, _ = QFileDialog.getSaveFileName(
            self, "حفظ ملف الترخيص", "license.json", "JSON (*.json)"
        )
        if not target:
            return
        Path(target).write_text(json.dumps(license_data, ensure_ascii=False, indent=2), encoding="utf-8")
        self.output.setPlainText(f"تم إنشاء الترخيص بنجاح:\n{target}")

    def show_public_key(self):
        self.output.setPlainText(self.public_key_path.read_text(encoding="utf-8"))

    def export_public_key(self):
        target, _ = QFileDialog.getSaveFileName(
            self, "تصدير مفتاح التحقق", "public_key.pem", "PEM (*.pem)"
        )
        if target:
            Path(target).write_bytes(self.public_key_path.read_bytes())
            self.output.setPlainText(f"تم تصدير مفتاح التحقق إلى:\n{target}")


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("مدير تراخيص نظام إدارة البقالات")
    app.setLayoutDirection(Qt.RightToLeft)
    setup_application_font(app)
    window = LicenseManager()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
