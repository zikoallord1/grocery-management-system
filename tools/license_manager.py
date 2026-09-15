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
        root = QVBoxLayout(self)
        title = QLabel("مدير تراخيص نظام إدارة البقالات")
        title.setStyleSheet("font-size:22px;font-weight:700;")
        root.addWidget(title)
        note = QLabel("هذه الأداة مخصصة لمالك البرنامج لإصدار تراخيص موقعة وربطها بتثبيت العميل. مفتاح الإصدار الخاص يبقى محليًا ولا يُرسل للعميل.")
        note.setWordWrap(True)
        root.addWidget(note)

        form = QFormLayout()
        self.installation_id = QLineEdit()
        self.installation_id.setPlaceholderText("الصق رقم التثبيت الذي يظهر في جهاز العميل")
        self.customer_name = QLineEdit()
        self.store_name = QLineEdit()
        self.edition = QComboBox()
        self.edition.addItems(["Standard", "Professional", "Enterprise"])
        self.expires_at = QDateEdit()
        self.expires_at.setCalendarPopup(True)
        self.expires_at.setDate(date.today().replace(year=date.today().year + 1))
        form.addRow("معرّف تثبيت العميل", self.installation_id)
        form.addRow("اسم العميل", self.customer_name)
        form.addRow("اسم المنشأة / البقالة", self.store_name)
        form.addRow("نوع الترخيص", self.edition)
        form.addRow("تاريخ الانتهاء", self.expires_at)
        root.addLayout(form)

        buttons = QHBoxLayout()
        generate = QPushButton("إنشاء الترخيص")
        generate.clicked.connect(self.create_license)
        show_public = QPushButton("عرض مفتاح التحقق العام")
        show_public.clicked.connect(self.show_public_key)
        export_public = QPushButton("تصدير مفتاح التحقق للنسخة")
        export_public.clicked.connect(self.export_public_key)
        buttons.addWidget(generate)
        buttons.addWidget(show_public)
        buttons.addWidget(export_public)
        root.addLayout(buttons)

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setPlaceholderText("ستظهر هنا نتيجة إنشاء الترخيص ومعلومات المفتاح العام...")
        root.addWidget(self.output, 1)

    def create_license(self):
        iid = self.installation_id.text().strip().upper()
        customer = self.customer_name.text().strip()
        store = self.store_name.text().strip()
        if not iid or not customer or not store:
            QMessageBox.warning(self, "بيانات ناقصة", "أدخل معرّف التثبيت واسم العميل واسم المنشأة.")
            return
        expires = self.expires_at.date().toPython()
        if expires < date.today():
            QMessageBox.warning(self, "تاريخ غير صحيح", "تاريخ انتهاء الترخيص يجب أن يكون اليوم أو بعده.")
            return
        envelope = create_signed_license(private_key_path=self.private_key_path, customer_name=customer, store_name=store, installation_id_value=iid, expires_at=expires, edition=self.edition.currentText())
        target, _ = QFileDialog.getSaveFileName(self, "حفظ ملف الترخيص", "license.json", "License (*.json)")
        if not target:
            return
        Path(target).write_text(json.dumps(envelope, ensure_ascii=False, indent=2), encoding="utf-8")
        self.output.setPlainText("تم إنشاء الترخيص بنجاح.\n\n" f"رقم الترخيص: {envelope['payload']['license_id']}\n" f"العميل: {customer}\n" f"المنشأة: {store}\n" f"الانتهاء: {expires.isoformat()}\n" f"الملف: {target}\n\n" "مهم: يجب أن تحتوي نسخة العميل على مفتاح التحقق العام المطابق، بينما يبقى مفتاح الإصدار الخاص على جهاز مالك البرنامج فقط.")

    def show_public_key(self):
        self.output.setPlainText(self.public_key_path.read_text(encoding="utf-8"))

    def export_public_key(self):
        target, _ = QFileDialog.getSaveFileName(self, "تصدير مفتاح التحقق العام", "public_key.pem", "PEM (*.pem)")
        if not target:
            return
        Path(target).write_bytes(self.public_key_path.read_bytes())
        self.output.setPlainText(f"تم تصدير مفتاح التحقق العام إلى:\n{target}\n\nهذا المفتاح آمن للتوزيع مع نسخة البرنامج، ولا يمكنه إنشاء تراخيص.")


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
