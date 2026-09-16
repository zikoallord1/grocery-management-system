from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QDialog, QLabel, QPushButton, QVBoxLayout

from backend.app.core.database import DATA_DIR


SETUP_FILE = DATA_DIR / "first_run_setup.json"


class FirstRunWizard(QDialog):
    """Small first-launch checklist shown once after a fresh installation."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("تهيئة بدء الاستخدام")
        self.setMinimumSize(560, 390)
        self.setLayoutDirection(Qt.RightToLeft)
        self.setModal(True)

        root = QVBoxLayout(self)
        title = QLabel("تهيئة بدء الاستخدام")
        title.setObjectName("pageTitle")
        root.addWidget(title)

        intro = QLabel(
            "مرحبًا بك في نظام إدارة البقالات.\n"
            "هذه الشاشة تظهر مرة واحدة بعد التثبيت لتأكيد الإعداد الأولي قبل تسجيل الدخول."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        root.addSpacing(8)
        root.addWidget(QLabel("سيتم تجهيز بيئة البرنامج بالبيانات الأساسية التالية:"))
        for text in (
            "قاعدة البيانات ومجلد بيانات البرنامج.",
            "المستخدم الافتراضي: admin — كلمة المرور: admin.",
            "الصندوق ووسائل الدفع الأساسية والمخزن الرئيسي.",
            "إمكانية بدء إدخال الأصناف والمشتريات والمبيعات بعد تسجيل الدخول.",
        ):
            check = QCheckBox(text)
            check.setChecked(True)
            check.setEnabled(False)
            root.addWidget(check)

        root.addSpacing(10)
        note = QLabel("يمكن تعديل بيانات المستخدمين والإعدادات لاحقًا من داخل النظام.")
        note.setWordWrap(True)
        root.addWidget(note)

        start = QPushButton("تهيئة وبدء الاستخدام")
        start.setObjectName("primaryButton")
        start.clicked.connect(self._complete)
        root.addWidget(start)

    @staticmethod
    def already_completed() -> bool:
        try:
            data = json.loads(SETUP_FILE.read_text(encoding="utf-8"))
            return bool(data.get("completed"))
        except (OSError, ValueError, AttributeError):
            return False

    def _complete(self):
        SETUP_FILE.parent.mkdir(parents=True, exist_ok=True)
        SETUP_FILE.write_text(
            json.dumps({"completed": True, "version": 1}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self.accept()
