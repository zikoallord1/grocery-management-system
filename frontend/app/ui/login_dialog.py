from __future__ import annotations

import hashlib
import json

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QDialog, QFormLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout

from backend.app.core.database import DATA_DIR


USERS_FILE = DATA_DIR / "users.json"


class LoginDialog(QDialog):
    authenticated = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("تسجيل الدخول — نظام إدارة البقالات")
        self.setMinimumSize(430, 300)
        self.setLayoutDirection(Qt.RightToLeft)
        self.setModal(True)
        root = QVBoxLayout(self)
        title = QLabel("تسجيل الدخول")
        title.setObjectName("pageTitle")
        root.addWidget(title)
        root.addWidget(QLabel("أدخل اسم المستخدم وكلمة المرور للمتابعة إلى النظام."))
        form = QFormLayout()
        self.username = QLineEdit()
        self.username.setPlaceholderText("اسم المستخدم")
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setPlaceholderText("كلمة المرور")
        form.addRow("اسم المستخدم", self.username)
        form.addRow("كلمة المرور", self.password)
        root.addLayout(form)
        self.status = QLabel("بيانات الدخول الافتراضية: admin / admin")
        self.status.setWordWrap(True)
        root.addWidget(self.status)
        login = QPushButton("دخول")
        login.setObjectName("primaryButton")
        login.clicked.connect(self._login)
        root.addWidget(login)
        self.password.returnPressed.connect(self._login)
        self.username.setFocus()

    @staticmethod
    def _hash_password(password: str) -> str:
        return hashlib.sha256(password.encode("utf-8")).hexdigest()

    def _users(self):
        try:
            if USERS_FILE.exists():
                data = json.loads(USERS_FILE.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    return data
        except (OSError, ValueError):
            pass
        return []

    def _login(self):
        username = self.username.text().strip()
        password = self.password.text()
        if not username or not password:
            self.status.setText("أدخل اسم المستخدم وكلمة المرور.")
            return
        expected = self._hash_password(password)
        user = next((u for u in self._users() if str(u.get("username", "")).casefold() == username.casefold()), None)
        if user is None or not user.get("active", True) or user.get("password_hash") != expected:
            self.status.setText("اسم المستخدم أو كلمة المرور غير صحيحة، أو أن الحساب موقوف.")
            self.password.selectAll()
            self.password.setFocus()
            return
        self.authenticated.emit(user)
        self.accept()
