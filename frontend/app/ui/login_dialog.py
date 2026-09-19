from __future__ import annotations

import hashlib
import json
from uuid import uuid4

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QDialog, QFormLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout

from backend.app.core.database import DATA_DIR
from backend.app.core.audit_service import AuditService
from backend.app.core.database import get_session


USERS_FILE = DATA_DIR / "users.json"


class LoginDialog(QDialog):
    authenticated = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("تسجيل الدخول — نظام الماركت المحاسبي")
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
            self._audit_login(username, False, "بيانات الدخول غير صحيحة أو الحساب موقوف.")
            self.status.setText("اسم المستخدم أو كلمة المرور غير صحيحة، أو أن الحساب موقوف.")
            self.password.selectAll()
            self.password.setFocus()
            return
        if not self._audit_login(username, True, "تم تسجيل الدخول."):
            self.status.setText("تعذر تسجيل عملية الدخول في سجل التدقيق.")
            return
        self.authenticated.emit(user)
        self.accept()

    def _audit_login(self, username: str, successful: bool, reason: str) -> bool:
        session = get_session()
        try:
            AuditService(session).record(
                operation_id=f"LOGIN:{uuid4()}",
                event_type="AUTHENTICATION",
                action="LOGIN_SUCCESS" if successful else "LOGIN_REJECTED",
                user_id=None,
                description=reason,
                details={"username": username, "result": "SUCCESS" if successful else "REJECTED"},
            )
            session.commit()
            return True
        except Exception:
            session.rollback()
            return False
        finally:
            session.close()
